"""Aşama 2 (yönetim paneli) uçtan uca testi — yalnızca stdlib.

Çalışan sunucuya karşı: dataset ekleme (yol tarama + translations.json), session
oluşturma, client oluşturma + aktif session atama, atanan oturumla protokol akışı
ve dataset silme (FK cascade) doğrulanır.

    python scripts/manage_test.py --url http://127.0.0.1:8000/ --dataset-path <mutlak yol>
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def http(url, method="GET", data=None, headers=None, is_json=False, follow=True):
    headers = dict(headers or {})
    body = None
    if data is not None:
        if is_json:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        else:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with opener.open(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000/")
    ap.add_argument("--dataset-path", required=True)
    args = ap.parse_args()
    base = args.url.rstrip("/") + "/"
    suffix = int(time.time() * 1000)
    slug = f"manual_{suffix}"
    sess_name = f"run_{suffix}"
    team = f"client_{suffix}"

    failures = []

    def check(cond, msg):
        print(f"[{'OK ' if cond else 'FAIL'}] {msg}")
        if not cond:
            failures.append(msg)

    # 1) Dataset ekle (yol tarama + translations.json)
    status, body = http(base + "manage/datasets/create", "POST",
                        {"path": args.dataset_path, "name": "Manual Set", "slug": slug})
    check(status == 200 and f"{slug}" in body and "3 kare" in body,
          f"dataset ekle -> 3 kare bulundu (slug={slug})")
    check("translations.json: var" in body, "translations.json algilandi (var)")

    # dataset_id'yi sessions sayfasindaki dropdown'dan al
    _, sess_page = http(base + "manage/sessions")
    m = re.search(rf'<option value="(\d+)">{slug} ', sess_page)
    check(bool(m), "yeni dataset session dropdown'da listeleniyor")
    dataset_id = m.group(1) if m else None

    # 2) Session olustur
    status, body = http(base + "manage/sessions/create", "POST",
                        {"name": sess_name, "dataset_id": dataset_id})
    check(status == 200 and sess_name in body, f"session olustur ({sess_name})")

    # session_id'yi clients sayfasindaki dropdown'dan al
    _, cli_page = http(base + "manage/clients")
    m = re.search(rf'<option value="(\d+)">{sess_name}</option>', cli_page)
    check(bool(m), "yeni session client dropdown'da listeleniyor")
    session_id = m.group(1) if m else None

    # 3) Client olustur + aktif session ata
    status, body = http(base + "manage/clients/create", "POST",
                        {"team_name": team, "password": "x", "active_session_id": session_id})
    check(status == 200 and team in body, f"client olustur ({team})")
    # client tablosunda aktif session olarak sess_name gorunuyor mu
    check(re.search(rf'{team}.*?{sess_name}', body, re.S) is not None,
          "client'in aktif session'i atandi")

    # 4) Atanan oturumla protokol akisi (frame sayisi=3, prediction 201)
    status, body = http(base + "auth/", "POST", {"username": team, "password": "x"})
    token = json.loads(body).get("token") if status == 200 else None
    auth_h = {"Authorization": f"Token {token}"}
    status, body = http(base + "frames/", headers=auth_h)
    frames = json.loads(body) if status == 200 else []
    check(len(frames) == 3, f"atanan dataset frame sayisi=3 (gelen={len(frames)})")
    status, body = http(base + "translation/", headers=auth_h)
    trs = json.loads(body) if status == 200 else []
    check(len(trs) == 3 and trs[1]["health_status"] == "0",
          "translations.json degerleri dondu (2. kare health_status=0)")
    if frames:
        payload = {"frame": frames[0]["url"],
                   "detected_objects": [{"cls": base + "classes/1/", "landing_status": "1",
                                         "top_left_x": "1", "top_left_y": "2",
                                         "bottom_right_x": "3", "bottom_right_y": "4"}],
                   "detected_translations": [{"translation_x": "1", "translation_y": "2", "translation_z": "3"}]}
        status, _ = http(base + "prediction/", "POST", payload, auth_h, is_json=True)
        check(status == 201, f"atanan oturuma prediction -> {status} (201)")

    # 5) Dataset sil -> session + prediction FK cascade
    status, body = http(base + f"manage/datasets/{dataset_id}/delete", "POST", {})
    check(status == 200 and "silindi" in body, "dataset sil (cascade)")
    _, sess_page = http(base + "manage/sessions")
    check(sess_name not in sess_page, "silme sonrasi session listede yok (cascade dogrulandi)")

    print()
    if failures:
        print(f"{len(failures)} kontrol BASARISIZ.")
        sys.exit(1)
    print("Tum yonetim kontrolleri gecti.")


if __name__ == "__main__":
    main()
