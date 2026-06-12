# TEKNOFEST Local Evaluation Server

Havacılıkta Yapay Zeka yarışması **istemcisinin** (`TAKIM_BAGLANTI_ARAYUZU`) bağlanabileceği,
gerçek değerlendirme sunucusunun protokolünü **birebir** taklit eden yerel test sunucusu.
Dataset / session / client yönetimi, prediction ve istek/yanıt loglaması içerir.

> İstemci kodunu değiştirmezsiniz; yalnızca `config/.env` içindeki `EVALUATION_SERVER_URL`'i
> bu sunucuya çevirirsiniz.

## Hızlı başlangıç (Docker)

```bash
cd server
docker compose up --build
```

Açılışta otomatik olarak (`AUTO_SEED=true`):
- `sample_set` adında 30 karelik sentetik bir dataset üretilir,
- `sample_session` oturumu oluşturulur,
- `test_team` / `test` client'ı oluşturulup oturuma bağlanır.

Panel: <http://localhost:8000/dashboard> · API Docs: <http://localhost:8000/docs>

## Docker olmadan (lokal)

```bash
cd server
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## İstemciyi bağlama

`TAKIM_BAGLANTI_ARAYUZU/config/.env`:

```env
TEAM_NAME=test_team
PASSWORD=test
EVALUATION_SERVER_URL=http://localhost:8000/
SESSION_NAME=sample_session
```

> `EVALUATION_SERVER_URL` **mutlaka `/` ile bitmeli** (istemci URL'leri string birleştirme
> ile kuruyor). Başka makineden bağlanacaksanız `http://<sunucu-ip>:8000/` kullanın.

Sonra istemciyi çalıştırın:

```bash
cd TAKIM_BAGLANTI_ARAYUZU
python main.py
```

Panelde `/auth/`, `/frames/`, `/translation/`, `/prediction/` isteklerinin canlı aktığını görürsünüz.

## Uçtan uca test (istemci olmadan)

```bash
python scripts/smoke_test.py --url http://localhost:8000/ --team test_team --password test
```

## Uygulanan protokol sözleşmesi (gerçek istemciden doğrulandı)

| Endpoint | Method | Not |
|---|---|---|
| `/auth/` | POST (form) | `{username,password}` → `200 {"token": ...}` |
| `/frames/` | GET (Token) | `[{url, image_url, video_name}]` |
| `/translation/` | GET (Token) | frame ile **aynı sıra/uzunluk**, `{x,y,z,health_status}` |
| `/prediction/` | POST (JSON, Token) | başarı **201**; aynı frame tekrar **406**; limit aşımı **403** |
| `/classes/{id}/` | GET | **1-indeksli** (istemci `cls = index+1`) |
| `/media/{path}` | GET | `base_url + 'media' + image_url` |
| `/session/` | GET (Token) | bilgi amaçlı |

Kritik detaylar:
- `image_url` **`/` ile başlar**; `base + 'media' + image_url` → `/media/<slug>/...`.
- prediction'daki `cls` bir **URL string**'tir (`.../classes/<index+1>/`); sunucu id'yi parse eder.
- prediction'daki `frame`, `/frames/` içinde verilen `url`'in aynısıdır; eşleştirme bununla yapılır.

## Yapılandırma (ortam değişkenleri)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | Postgres: `postgresql+psycopg://...` |
| `PUBLIC_URL` | `http://localhost:8000/` | frame `url` ön eki |
| `MEDIA_ROOT` | `./data/media` | görsel kök dizini |
| `AUTO_SEED` | `true` | açılışta örnek dataset/session/client |
| `RATE_LIMIT_ENABLED` | `false` | yarışma kısıtları (5/dk, 80/dk) |
| `DEFAULT_TEAM_NAME` / `DEFAULT_TEAM_PASSWORD` | `test_team` / `test` | varsayılan client |

## Kendi dataset'inizi kullanma (v1)

`MEDIA_ROOT` altında bir klasöre görselleri koyun (ör. `data/media/set_01/...`) ve harici
diskler için `docker-compose.yml`'deki volume satırını açın. Otomatik kayıt şu an `sample_set`
içindir; gerçek setleri kaydetmek için `app/services/datasets.register_dataset(...)` kullanılır
(panelden CRUD bir sonraki aşamada eklenecek — bkz. yol haritası).

## Yol haritası

- **Aşama 1 (bu sürüm):** protokol uyumlu sunucu + seed + loglama + minimal panel. ✅
- **Aşama 2:** panelden dataset tarama/kayıt, session & client CRUD, aktif session atama.
- **Aşama 3:** filtreli log/prediction ekranları, client/model karşılaştırma.
- **Aşama 4:** bbox overlay, skor hesabı (mAP / RMSE), CSV/JSON export.
