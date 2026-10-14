# Rapit Quiz — Backend (Claude notları)

Gençlere yönelik hızlı bilgi yarışması: kategori seç, 20 soru, soru başına 5 sn, puan sunucuda
hesaplanır, kategori başına ilk 10 skor tablosu. Kimlik doğrulama/kullanıcı hesabı **yok**.
Tam doküman: `docs/PROJE_DOKUMANI.md` (Türkçe). Kullanıcıyla Türkçe konuş.

## Repolar (kardeş klasörler)

| Repo | Yol | Not |
|---|---|---|
| Backend (bu repo) | `/home/memo/projects/rapit-quiz-backend` | Django 5 + DRF |
| Frontend | `/home/memo/projects/rapit-quiz-frontend` | Vue 3 + Vite + TS + Pinia. Frontend ihtiyacı olunca **oraya bak/orada geliştir**. |
| Mobil | henüz yok | Flutter önerildi (aşama 5) |

API sözleşmesini değiştirirsen frontend'i de güncelle: `../rapit-quiz-frontend/src/api/types.ts`
ve `client.ts` elle yazılmıştır (OpenAPI'den üretilmiyor).

## Durum

Aşama 1–3 (backend), 4 (Vue frontend) ve CI/Docker/`.do/app.yaml` dosyaları tamam. Bekleyen: mobil
uygulama (aşama 5), gerçek DigitalOcean deploy'u, Dockerfile'ın ve Postgres testlerinin ilk gerçek
çalıştırılması (bu makinede Docker/Postgres yok; CI'da koşacak).

## Komutlar (venv: `.venv`, Python 3.14 yerelde; Dockerfile 3.12 kullanır)

```bash
.venv/bin/python -m pytest                  # 40 test, bellek içi SQLite
TEST_DATABASE_URL=postgres://... .venv/bin/python -m pytest   # Postgres'e karşı
.venv/bin/ruff check . && .venv/bin/black --check .
.venv/bin/python manage.py migrate          # kategorileri de oluşturur (0002 data migration)
.venv/bin/python manage.py import_questions --seed   # 5×40 soru, idempotent
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Frontend: `cd ../rapit-quiz-frontend && npm run dev` (5173), `npx vitest run`, `npm run lint`,
`npm run type-check`, `npm run test:e2e` (Playwright, API mock'lu). Tarayıcıda **`localhost`**
kullan; `127.0.0.1` CORS'a takılır (`.env` içindeki `CORS_ALLOWED_ORIGINS`).

## Mimari ve kurallar

- `config/` (settings, urls), `apps/{core,categories,questions,quiz,leaderboard}`, testler `tests/`.
- İş mantığı `apps/quiz/services.py`'de; view'lar ince. Süre/puan kuralları orada:
  cevap `served_at + 5 sn + 700 ms tolerans` sonrası gelirse süresiz (0 puan); doğru = 100 +
  `round(50·kalan/5000)`; eşitlikte kısa süre, sonra önce kaydedilen. Ayarlar `settings.QUIZ_*`.
- Soru sırayla verilir; süresi dolmuş soru bir sonraki `question/` isteğinde otomatik "süresiz"
  kapanır. Hata biçimi her yerde `{"error": {"code", "message", "details"?}}`
  (`apps/core/exceptions.py`; `ApiError` fırlat).
- Servis hataları `transaction.atomic` içinde fırlatılırsa geri alınır; yan etki sonrası hata
  gerekiyorsa `None` döndürüp view'da fırlat (bkz. `serve_question`).
- Health check (`/api/v1/health/`) middleware'de (`HealthCheckMiddleware`) — Host/HTTPS
  kontrolünden önce; URL olarak tanımlama.
- Testler zamanı `clock` fixture'ıyla (`timezone.now` monkeypatch) kontrol eder; throttle ayarları
  `settings_test.py`'de gevşetilmiştir.
- `.env` yoksa DB SQLite'tır; `DEBUG` varsayılan **False** ve `SECRET_KEY` zorunludur (yerelde
  `.env.example` → `.env`). Settings basit bir `.env` okuyucu içerir.
- Soru formatı (JSON): `{"q","a","w":[3 yanlış]}` veya tam biçim; CSV desteklenir. Sorular
  `apps/questions/seed_data/<slug>.json`. İçerik doğruluğu kullanıcı tarafından gözden geçirilmeli.
- Frontend oyun durumunu yalnızca bellekte tutar; sayfa yenilenirse oyun biter (dokümandaki gibi).

## Dağıtım — DigitalOcean App Platform (KULLANICI MANUEL, TARAYICIDAN YAPAR)

- **`doctl`/DO CLI kullanma, önermeye çalışma.** Kullanıcı deploy'u DO web panelinden elle
  yapacak; benden istenen: panelde adım adım anlatım (Türkçe). Kullanıcı "DO'ya nasıl deploy
  ederim" diye sorunca anlat: iki **ayrı App** (backend Web Service + Dockerfile + attached
  Managed PostgreSQL + PRE_DEPLOY migrate job + scheduled cleanup job; frontend Static Site).
- Referans dosyalar: backend `.do/app.yaml`, frontend `../rapit-quiz-frontend/.do/app.yaml`
  (`<kullanici>` ve `rapitquiz.example` yer tutucu). Bunlar panel alanlarının karşılığını gösterir.
- Ortam değişkenleri (backend): `DATABASE_URL` (`${db.DATABASE_URL}`), `SECRET_KEY` (secret),
  `DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `API_NUM_PROXIES=1`.
  Frontend (build zamanı): `VITE_API_BASE_URL`. İlk deploy'dan sonra bir kez
  `python manage.py import_questions --seed` çalıştırılmalı (kategoriler migrasyonla gelir).
- Frontend: build `npm ci && npm run build-only`, çıktı `dist`, catchall document `index.html`.
  `.npmrc` içindeki `legacy-peer-deps=true` `npm ci` için gerekli.
- Tuzaklar: Dockerfile `collectstatic` için geçici `SECRET_KEY` kullanır; konteyner `$PORT`'a
  bağlanır (varsayılan 8080, App Platform `http_port` ile eşleşmeli); health check yolu
  `/api/v1/health/`; DB `sslmode=require` managed DB URL'inde gelir.

## Çalışma tercihleri

- Commit'i kullanıcı atar; ben sormadan commit/push yapmam (kullanıcı istediğinde yaparım).
- Geçici dosyalar scratchpad dizinine. Çalışan sunucuları işim bitince kapat (port 8000/5173);
  `pkill -f` kendi kabuğumu da öldürebiliyor, bunun yerine `kill $(lsof -ti :PORT)` kullan.
- Silme komutlarında glob/göreli yol kullanma (güvenlik kontrolü engelliyor).
