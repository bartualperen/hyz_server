"""Uçtan uca akış testi — gerçek istemciyi taklit eder (yalnızca stdlib).

Sunucu çalışırken:
    python scripts/smoke_test.py --url http://localhost:8000/ --team test_team --password test

İstemcinin yaptığı her adımı tekrarlar: auth -> frames -> translation -> image ->
prediction(201) -> aynı frame tekrar(406) -> classes.
"""
import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def request(url, method="GET", data=None, headers=None, is_json=False):
    headers = dict(headers or {})
    body = None
    if data is not None:
        if is_json:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        else:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000/")
    ap.add_argument("--team", default=None,
                    help="Belirtilmezse her çalıştırmada benzersiz bir takım üretilir (temiz 201 yolu).")
    ap.add_argument("--password", default="test")
    args = ap.parse_args()
    base = args.url if args.url.endswith("/") else args.url + "/"

    # --team verilmezse benzersiz takım üret: ilk prediction her zaman 201 olur (re-run güvenli).
    # Verilirse o takımla test edilir; ilk prediction 201 ya da (önceden gönderilmişse) 406 kabul edilir.
    if args.team:
        team = args.team
        strict_first = False
    else:
        team = f"smoke_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        strict_first = True

    failures = []

    def check(cond, msg):
        status = "OK " if cond else "FAIL"
        print(f"[{status}] {msg}")
        if not cond:
            failures.append(msg)

    # 1) auth
    status, body = request(base + "auth/", "POST", {"username": team, "password": args.password})
    token = json.loads(body).get("token") if status == 200 else None
    check(status == 200 and token, f"/auth/ -> {status}, token alındı (takım={team})")
    auth_headers = {"Authorization": f"Token {token}"}

    # 2) frames
    status, body = request(base + "frames/", "GET", headers=auth_headers)
    frames = json.loads(body) if status == 200 else []
    check(status == 200 and len(frames) > 0, f"/frames/ -> {status}, {len(frames)} kare")
    if frames:
        f0 = frames[0]
        check(all(k in f0 for k in ("url", "image_url", "video_name")),
              "frame alanları: url/image_url/video_name mevcut")
        check(f0["image_url"].startswith("/"), "image_url '/' ile başlıyor")

    # 3) translation
    status, body = request(base + "translation/", "GET", headers=auth_headers)
    translations = json.loads(body) if status == 200 else []
    check(status == 200 and len(translations) == len(frames),
          f"/translation/ -> {status}, {len(translations)} kayıt (frame ile eşit)")
    if translations:
        t0 = translations[0]
        check(all(k in t0 for k in ("translation_x", "translation_y", "translation_z", "health_status")),
              "translation alanları: x/y/z/health_status mevcut")

    # 4) media (görsel indirme: base + 'media' + image_url)
    if frames:
        img_url = base + "media" + frames[0]["image_url"]
        status, body = request(img_url, "GET")
        check(status == 200 and len(body) > 0, f"/media -> {status}, {len(body)} bayt indirildi")

    # 5) prediction (201)
    if frames:
        payload = {
            "frame": frames[0]["url"],
            "detected_objects": [{
                "cls": base + "classes/3/",  # UAP (index 2 + 1)
                "landing_status": "1",
                "top_left_x": "10", "top_left_y": "20",
                "bottom_right_x": "110", "bottom_right_y": "120",
            }],
            "detected_translations": [{"translation_x": "1.0", "translation_y": "2.0", "translation_z": "3.0"}],
        }
        status, body = request(base + "prediction/", "POST", payload, auth_headers, is_json=True)
        if strict_first:
            check(status == 201, f"/prediction/ ilk gönderim -> {status} (201 bekleniyor)")
        else:
            check(status in (201, 406), f"/prediction/ ilk gönderim -> {status} (201/406 kabul)")

        # 6) aynı frame tekrar -> 406
        status, body = request(base + "prediction/", "POST", payload, auth_headers, is_json=True)
        check(status == 406, f"/prediction/ aynı frame tekrar -> {status} (406 bekleniyor)")

    # 7) classes
    status, body = request(base + "classes/3/", "GET")
    cls = json.loads(body) if status == 200 else {}
    check(status == 200 and cls.get("name") == "UAP", f"/classes/3/ -> {status}, name={cls.get('name')}")

    print()
    if failures:
        print(f"{len(failures)} kontrol BAŞARISIZ.")
        sys.exit(1)
    print("Tum kontroller gecti.")


if __name__ == "__main__":
    main()
