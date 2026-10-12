# Rapit Quiz — Backend

Django 5 + DRF REST API. Proje dokümanı: [docs/PROJE_DOKUMANI.md](docs/PROJE_DOKUMANI.md).
Frontend (Vue) kardeş repoda: `../rapit-quiz-frontend`.

## Yerel çalıştırma (Docker'sız)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env                                 # DATABASE_URL boşsa SQLite kullanılır
.venv/bin/python manage.py migrate                   # kategorileri de oluşturur
.venv/bin/python manage.py import_questions --seed   # 5 × 40 başlangıç sorusu
.venv/bin/python manage.py createsuperuser           # admin paneli: /admin/
.venv/bin/python manage.py runserver
```

Docker ile: `docker compose up` (Postgres 16 + web, http://localhost:8000).

- OpenAPI şeması: `/api/v1/schema/`, Swagger UI: `/api/v1/docs/`
- Sağlık kontrolü: `/api/v1/health/` (DB'yi de kontrol eder; middleware seviyesinde çalışır,
  Host/HTTPS kontrollerine takılmaz)

## Test ve kalite

```bash
.venv/bin/python -m pytest                                    # varsayılan: bellek içi SQLite
TEST_DATABASE_URL=postgres://... .venv/bin/python -m pytest   # Postgres'e karşı (CI)
.venv/bin/ruff check . && .venv/bin/black --check .
```

## Soru yönetimi

- Admin panelinden: her soru tam 4 şık, tam 1 doğru şık (admin doğrular).
- Toplu: `manage.py import_questions dosya.json|dosya.csv [--category slug] [--dry-run]`
  - Aynı kategori + aynı metne sahip sorular atlanır (tekrar çalıştırmak güvenlidir).
  - JSON tam biçim: `{"category","text","choices":[4],"correct":0-3}`;
    kompakt biçim: `{"q","a":"doğru","w":["yanlış1","yanlış2","yanlış3"]}` (şıklar karıştırılır).
  - CSV: `category,text,choice1..choice4,correct(1-4)`.
- Başlangıç verisi: `apps/questions/seed_data/<slug>.json`.

## Bakım

`manage.py cleanup_sessions` — 1 saatten eski, skoru gönderilmemiş (`active`/`finished`)
oturumları siler. App Platform'da zamanlanmış job olarak çalıştırılmalıdır.

## Ortam değişkenleri

`SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
(bkz. `.env.example`). Ek: `QUIZ_NETWORK_TOLERANCE_MS` (700), `THROTTLE_SESSION_START`
(30/min), `THROTTLE_SCORE_SUBMIT` (20/min), `API_NUM_PROXIES` (1; throttle IP tespiti için
güvenilir proxy sayısı), `SECURE_SSL_REDIRECT`.

## API notları (dokümana göre eklenenler)

Hata biçimi: `{"error": {"code", "message", "details"?}}`.

| Uç nokta | Ek davranış |
|---|---|
| `POST /sessions/` | Yanıt: `session_id`, `category`, `question_count` (201) |
| `GET /sessions/{id}/question/` | Yanıta `total_questions` ve `remaining_ms` eklendi. Cevaplanmamış, süresi dolmamış soru tekrar istenirse **aynı soru** kalan süreyle döner (`served_at` sıfırlanmaz). Süresi dolan soru otomatik "süresiz" sayılır. Soru kalmadıysa `409 session_finished` |
| `POST /sessions/{id}/answer/` | `choice_id: null` süresiz sayılır. Yanıta `finished` eklendi; son cevaptan sonra oturum `finished` olur |
| `GET /sessions/{id}/result/` | `finished`/`submitted` durumunda açılır; aksi halde `409 session_not_finished` |
| `POST /sessions/{id}/submit-score/` | Yanıt: `entry_id`, `rank`, `player_name`, `score`. Hatalar: `invalid_name`, `inappropriate_name`, `already_submitted` |
| `GET /leaderboard/?category=&limit=` | `category` zorunlu; `limit` varsayılan 10, en fazla 50. Satırlarda `rank` ve `entry_id` var (kullanıcı satırını vurgulamak için `submit-score`'dan dönen `entry_id` ile eşleştirin) |

Süre kuralı: cevap `served_at + 5 sn + tolerans` sonrasında gelirse süresiz sayılır; tolerans
içinde gelen doğru cevap 100 puan alır, hız bonusu 0 olur.
