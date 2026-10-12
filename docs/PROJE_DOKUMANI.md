# Rapit Quiz — Proje Dokümanı

Sürüm: 0.1 (taslak) · Tarih: 2026-10-12

## 1. Özet

Rapit Quiz, gençlere yönelik hızlı tempolu bir bilgi yarışması uygulamasıdır. Kullanıcı bir kategori seçer, 20 soruyu tek tek ve her soru için 5 saniye süreyle cevaplar. Quiz bitince puanı hesaplanır, kullanıcıdan ismi istenir ve ilgili kategorinin ilk 10 skor tablosu gösterilir.

**Kapsam dışı:** Kayıt olma, giriş yapma, kullanıcı hesabı, profil. Kimlik doğrulama yoktur.

## 2. Hedefler

- Hızlı, akıcı, sade bir quiz deneyimi (bir oyun ~2 dakika).
- Web (Vue.js) ve mobil uygulama aynı backend API'sini kullanır.
- Hile yapmayı zorlaştıran, süre ve puanı **sunucu tarafında** denetleyen tasarım.

## 3. Kategoriler

| Slug | Ad |
|---|---|
| `yazilim` | Yazılım |
| `yapay-zeka` | Yapay Zeka |
| `bilgisayar-muhendisligi` | Bilgisayar Mühendisliği |
| `ulkeler` | Ülkeler |
| `fizik` | Fizik |

Her kategori için havuzda en az 40 soru bulunur (yeterli çeşitlilik için); her oyunda havuzdan rastgele 20 soru seçilir. Her soru 4 şıklıdır, tek doğru cevap vardır.

## 4. Kullanıcı Akışı

1. **Ana ekran:** Logo + 5 kategori kartı + "Skor Tablosu" bağlantısı.
2. **Kategori seçimi** → oyun başlar.
3. **Soru ekranı (×20):** soru metni, 4 şık, geri sayım çubuğu (5 sn), ilerleme göstergesi (n/20).
   - Şık seçilince cevap kilitlenir, doğru/yanlış geri bildirimi kısa gösterilir, sonraki soruya geçilir.
   - 5 saniye dolarsa soru boş/yanlış sayılır ve otomatik sonraki soruya geçilir.
   - Geri dönüş ve soruları önceden görme yoktur.
4. **Sonuç ekranı:** Toplam puan, doğru sayısı. İsim giriş alanı (2–20 karakter).
5. **Skor tablosu:** İsim gönderilince kategorinin ilk 10'u gösterilir; kullanıcının satırı listede varsa vurgulanır.

Oyun yarıda bırakılırsa (uygulama kapanır) skor kaydedilmez.

## 5. Puanlama

- Doğru cevap: **100 puan**
- Hız bonusu: kalan süreye göre **0–50 puan** → `round(50 * kalan_ms / 5000)`
- Yanlış / süresiz: 0 puan
- Maksimum: 20 × 150 = **3000 puan**
- Eşitlikte: önce toplam süresi kısa olan, sonra önce kaydedilen üstte.

Puan yalnızca backend'de hesaplanır; istemci puan göndermez.

## 6. Mimari

İki ayrı repo (+ mobil için üçüncü bir repo):

| Repo | Teknoloji | Açıklama |
|---|---|---|
| `rapit-quiz-backend` | Python 3.12, Django 5, Django REST Framework | REST API, admin paneli |
| `rapit-quiz-frontend` | Vue 3 (Vite), Pinia, Vue Router, TypeScript | Web arayüzü |
| `rapit-quiz-mobile` | Flutter *(öneri; alternatif: React Native)* | iOS/Android uygulaması |

Veritabanı: **PostgreSQL 16**.

```
 Vue Web ─┐
          ├─ HTTPS / JSON ─► Django REST API ─► PostgreSQL
 Mobil  ──┘
```

Backend istemciden bağımsız tasarlanır: yalnızca JSON REST API, oturum çerezi yok, CSRF'ye bağlı akış yok. Web ve mobil birebir aynı uç noktaları kullanır. API `/api/v1/` altında sürümlenir; OpenAPI şeması (drf-spectacular) üretilir ve mobil/web istemci tipleri bundan türetilebilir.

## 7. Veri Modeli

**Category**
- `id`, `slug` (unique), `name`, `icon`, `color`, `is_active`

**Question**
- `id`, `category` (FK), `text`, `is_active`, `created_at`

**Choice**
- `id`, `question` (FK), `text`, `is_correct`, `order`
- Kısıt: her soruda tam 1 doğru şık, toplam 4 şık (admin'de doğrulama).

**QuizSession** (bir oyun)
- `id` (UUID), `category` (FK), `started_at`, `finished_at` (null), `status` (`active` / `finished` / `submitted`), `total_score`, `correct_count`, `total_time_ms`

**SessionQuestion** (oyuna atanan 20 soru)
- `id`, `session` (FK), `question` (FK), `position` (1–20), `served_at` (null), `answered_at` (null), `choice` (FK, null), `is_correct`, `score`
- Unique: (`session`, `position`)

**ScoreEntry** (skor tablosu kaydı)
- `id`, `session` (OneToOne), `category` (FK), `player_name`, `score`, `correct_count`, `total_time_ms`, `created_at`
- İndeks: (`category`, `-score`, `total_time_ms`, `created_at`)

## 8. API Tasarımı (`/api/v1`)

Kimlik doğrulama yok. Oyun, `session_id` (UUID, tahmin edilemez) ile yürütülür.

| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/categories/` | Kategori listesi |
| POST | `/sessions/` | `{category}` → yeni oyun; 20 soru atanır. Yanıt: `session_id` |
| GET | `/sessions/{id}/question/` | Sıradaki soruyu verir ve süreyi başlatır (`served_at`). Doğru cevap **dönmez**. Yanıt: `position`, `text`, `choices[{id,text}]`, `time_limit_ms: 5000` |
| POST | `/sessions/{id}/answer/` | `{question_position, choice_id \| null}` → sunucu süreyi kontrol eder, `{is_correct, correct_choice_id, score_gained}` döner |
| GET | `/sessions/{id}/result/` | Oyun bitince toplam puan, doğru sayısı |
| POST | `/sessions/{id}/submit-score/` | `{player_name}` → skor tablosuna yazar (oyun başına bir kez) |
| GET | `/leaderboard/?category={slug}&limit=10` | İlk 10 skor |

Hata biçimi: `{"error": {"code": "...", "message": "..."}}`.

### Süre ve hile önleme

- Sunucu süreyi tutar: cevap, `served_at + 5 sn + ağ toleransı (~700 ms)` sonrasında gelirse **süresiz** sayılır (0 puan).
- Hız bonusu, istemcinin bildirdiği süreye değil `answered_at - served_at` farkına göre hesaplanır.
- Soru sırayla verilir; sıradaki soru, önceki cevaplanmadan/süresi dolmadan istenemez. Aynı soru iki kez cevaplanamaz.
- Doğru cevap bilgisi yalnızca cevap sonrasında iletilir.
- Skor, sadece tamamlanmış oyun için ve bir kez gönderilebilir.
- İsim: 2–20 karakter, boşluklar kırpılır, küfür/uygunsuz kelime filtresi (basit kara liste).
- Rate limiting (DRF throttling): IP başına oyun başlatma ve skor gönderme sınırı.
- Terk edilmiş `active` oturumlar periyodik temizlenir (ör. 1 saat sonra).

## 9. Arayüz / Tasarım Yönergeleri

Hedef kitle gençler: enerjik, açık ve canlı; koyu tema **değil**.

- **Zemin:** açık tonlar (`#F7F8FF` benzeri hafif lavanta-beyaz), kartlar beyaz, yumuşak gölgeler.
- **Vurgu renkleri:** canlı mor/indigo (birincil), turkuaz, mercan/pembe, sarı; her kategoriye ayrı bir renk.
- **Doğru/yanlış:** yeşil / mercan-kırmızı geri bildirim (renk körlüğü için ikon da eklenir).
- Yuvarlak köşeler (16–24 px), büyük dokunma alanları (min 48 px), büyük okunaklı tipografi (ör. Poppins / Nunito).
- Geri sayım: üstte renk değiştiren ilerleme çubuğu (yeşil → sarı → kırmızı) ve son 2 saniyede hafif titreşim animasyonu.
- Kısa, akıcı geçiş animasyonları; `prefers-reduced-motion` desteklenir.
- Mobil öncelikli (mobile-first) responsive; web ve mobil uygulama aynı görsel dili paylaşır.
- Erişilebilirlik: yeterli renk kontrastı (WCAG AA), klavye ile şık seçimi (1–4 tuşları).
- Skor tablosu: ilk 3 için madalya (🥇🥈🥉) vurgusu.

## 10. Frontend (Vue.js)

- Vue 3 + Vite + TypeScript, Pinia (oyun durumu), Vue Router.
- Rotalar: `/` (kategoriler), `/play/:category`, `/result`, `/leaderboard/:category?`.
- Geri sayım istemcide görsel amaçlıdır; asıl doğrulama sunucudadır.
- API adresi `VITE_API_BASE_URL` ortam değişkeninden okunur.
- Test: Vitest + Vue Test Utils; uçtan uca: Playwright.

## 11. Backend (Django)

- Django 5 + DRF, `psycopg` ile PostgreSQL, `django-cors-headers`, `drf-spectacular`, `gunicorn`, `whitenoise`, `dj-database-url`.
- Uygulamalar: `categories`, `questions`, `quiz` (oturum + cevap), `leaderboard`.
- Django admin: kategori/soru/şık yönetimi. Soru içe aktarımı için `loaddata` fikstürü veya CSV/JSON import komutu (`manage.py import_questions`).
- Ayarlar ortam değişkenlerinden okunur (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`).
- Test: pytest + pytest-django; süre/puan mantığı için birim testleri.
- Kalite: ruff, black.

## 12. Mobil Uygulama

- Aynı REST API'yi kullanır; backend'de mobil için ayrı bir kod yolu yoktur.
- Öneri: Flutter (tek kod tabanı, iOS + Android, akıcı animasyon). Alternatif: React Native.
- Oturum `session_id` yalnızca bellekte tutulur; çevrimdışı mod yoktur (ilk sürümde).
- Mobil uygulama mağaza sürümlerinde eski istemciler olabileceğinden API sürümlemesi (`/v1`) korunur, kırıcı değişiklikler `/v2` ile yapılır.
- Ağ gecikmesi toleransı mobilde daha geniş olabilir; tolerans değeri sunucu ayarıdır.

## 13. Dağıtım ve Ortamlar (DigitalOcean)

Her iki bileşen de **DigitalOcean App Platform** üzerinde, GitHub reposundaki `main` dalından otomatik deploy edilir.

| Bileşen | DO kaynak tipi | Not |
|---|---|---|
| Frontend | **Static Site** | `npm run build` çıktısı (`dist/`) CDN üzerinden sunulur. Docker gerekmez. |
| Backend | **Web Service** (Dockerfile ile) | Gunicorn ile çalışan Django konteyneri |
| Veritabanı | **Managed PostgreSQL** | App'e "attached database" olarak bağlanır; `DATABASE_URL` otomatik gelir |

```
Kullanıcı ─► DO CDN (Static Site: Vue) ─► https://api.rapitquiz.example ─► DO Web Service (Django/Gunicorn) ─► DO Managed PostgreSQL
```

### 13.1 Backend: Docker

Backend reposunda şu dosyalar bulunur:

- `Dockerfile` (üretim, çok aşamalı, non-root kullanıcı)
- `docker-compose.yml` (yalnızca yerel geliştirme: `web` + `db`)
- `.dockerignore`
- `entrypoint.sh` (bekleme + migrate + başlatma)
- `.do/app.yaml` (App Platform tanımı, isteğe bağlı)

**Dockerfile (taslak):**

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --from=builder /install /usr/local
COPY . .
RUN python manage.py collectstatic --noinput \
    && useradd -m app && chown -R app /app
USER app
EXPOSE 8080
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "3", "--timeout", "30"]
```

**Önemli noktalar:**
- App Platform `PORT` ortam değişkenini verir; gunicorn bu porta bağlanır (`--bind 0.0.0.0:${PORT:-8080}`).
- Statik dosyalar (admin paneli) **WhiteNoise** ile Django'dan sunulur; ayrı nginx gerekmez.
- Veritabanı migrasyonları App Platform'da **PRE_DEPLOY job** olarak çalıştırılır (`python manage.py migrate`), konteyner başlangıcında değil; böylece birden fazla örnek yarışmaz.
- Sağlık kontrolü: `GET /api/v1/health/` (DB bağlantısını da kontrol eder), App Platform health check olarak tanımlanır.
- Loglar stdout'a yazılır; DO panelinden izlenir.
- Konteyner dosya sistemine kalıcı veri yazılmaz (App Platform geçicidir).

**Yerel geliştirme (docker-compose.yml):**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: rapitquiz
      POSTGRES_USER: rapitquiz
      POSTGRES_PASSWORD: rapitquiz
    volumes: [pgdata:/var/lib/postgresql/data]
    ports: ["5432:5432"]
  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    env_file: .env
    volumes: [".:/app"]
    ports: ["8000:8000"]
    depends_on: [db]
volumes:
  pgdata:
```

### 13.2 Frontend: Statik site

- Build komutu: `npm ci && npm run build`, çıktı dizini: `dist`.
- SPA yönlendirmesi için **catchall document** `index.html` olarak ayarlanır (Vue Router history modu).
- `VITE_API_BASE_URL` build zamanında verilir (production için API alan adı). Bu bir sır değildir; istemciye gömülür.
- Hash/içerik adlı dosyalar uzun süreli cache'lenir, `index.html` cache'lenmez.
- Yerel geliştirmede Docker gerekmez (`npm run dev`).

### 13.3 App Spec (`.do/app.yaml`, taslak)

```yaml
name: rapit-quiz
region: fra
services:
  - name: api
    github: { repo: <kullanici>/rapit-quiz-backend, branch: main, deploy_on_push: true }
    dockerfile_path: Dockerfile
    http_port: 8080
    instance_size_slug: basic-xxs
    instance_count: 1
    health_check: { http_path: /api/v1/health/ }
    envs:
      - { key: DATABASE_URL, scope: RUN_TIME, value: "${db.DATABASE_URL}" }
      - { key: SECRET_KEY, scope: RUN_TIME, type: SECRET }
      - { key: DJANGO_ALLOWED_HOSTS, scope: RUN_TIME, value: "api.rapitquiz.example" }
      - { key: CORS_ALLOWED_ORIGINS, scope: RUN_TIME, value: "https://rapitquiz.example" }
      - { key: DEBUG, scope: RUN_TIME, value: "False" }
jobs:
  - name: migrate
    kind: PRE_DEPLOY
    github: { repo: <kullanici>/rapit-quiz-backend, branch: main }
    dockerfile_path: Dockerfile
    run_command: python manage.py migrate --noinput
databases:
  - name: db
    engine: PG
    version: "16"
    production: false   # geliştirme; canlıda managed cluster'a geçilir
static_sites:
  - name: web
    github: { repo: <kullanici>/rapit-quiz-frontend, branch: main, deploy_on_push: true }
    build_command: npm ci && npm run build
    output_dir: dist
    catchall_document: index.html
    envs:
      - { key: VITE_API_BASE_URL, scope: BUILD_TIME, value: "https://api.rapitquiz.example" }
```

> Not: İki ayrı repo olduğu için bu spec tek bir App içinde iki GitHub reposunu birleştirir; alternatif olarak backend ve frontend için **iki ayrı App** oluşturulabilir. Karar bölüm 16'dadır.

### 13.4 Ortam değişkenleri

| Değişken | Bileşen | Açıklama |
|---|---|---|
| `DATABASE_URL` | backend | Managed PostgreSQL bağlantısı (SSL zorunlu: `sslmode=require`) |
| `SECRET_KEY` | backend | Django gizli anahtarı (DO secret) |
| `DEBUG` | backend | Üretimde `False` |
| `DJANGO_ALLOWED_HOSTS` | backend | API alan adı |
| `CORS_ALLOWED_ORIGINS` | backend | Frontend alan adı (mobil uygulama CORS'a tabi değildir) |
| `VITE_API_BASE_URL` | frontend | API kök adresi (build zamanı) |

Sırlar repoya konmaz; `.env.example` dosyası örnek değerlerle tutulur.

### 13.5 Alan adı, HTTPS ve güvenlik

- Alan adları: `rapitquiz.example` (frontend) ve `api.rapitquiz.example` (backend); DO üzerinden özel alan adı eklenir, Let's Encrypt sertifikası otomatik.
- Production ayarları: `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER` (App Platform proxy arkasında), `SESSION/CSRF_COOKIE_SECURE`, HSTS.
- Managed DB'ye erişim yalnızca App'ten (Trusted Sources).
- Veritabanı yedekleri DO tarafından günlük alınır.

### 13.6 CI/CD

- **GitHub Actions:** her PR'da lint + test (backend için PostgreSQL servis konteyneriyle pytest; frontend için lint + Vitest + build).
- **Deploy:** `main` dalına birleştirmede App Platform otomatik build ve deploy eder (deploy_on_push). Testler geçmeden birleştirmeyi engellemek için branch protection kullanılır.
- Ortamlar: `staging` (ayrı küçük App + ayrı DB) ve `production`. Başlangıçta yalnızca production ile de başlanabilir.

## 14. Soru İçeriği

- Başlangıç: kategori başına 40 soru (toplam 200). Zorluk karışık, Türkçe.
- Sorular admin panelinden ve import komutuyla eklenir. İçerik doğruluğu yayından önce gözden geçirilir.
- İleride: zorluk seviyesi alanı, soru raporlama.

## 15. Yol Haritası

| Aşama | İçerik |
|---|---|
| 1 | Backend iskeleti, modeller, admin, soru import, seed verisi |
| 2 | Oyun API'si (oturum, soru, cevap, süre doğrulama, puanlama) + testler |
| 3 | Skor tablosu API'si, rate limiting, OpenAPI şeması |
| 4 | Vue frontend: kategori, oyun, sonuç, skor tablosu, tasarım |
| 5 | Mobil uygulama |
| 6 | Dockerfile, DigitalOcean App Platform kurulumu, CI/CD, yük ve güvenlik kontrolleri |

## 16. Açık Kararlar

1. Mobil teknoloji: Flutter mı React Native mi?
2. Skor tablosu yalnızca kategori bazlı mı, genel (tüm kategoriler) tablo da olsun mu? *(Öneri: ilk sürümde kategori bazlı.)*
3. Aynı isim birden fazla kez skor tablosunda görünebilsin mi? *(Öneri: evet, kimlik doğrulama olmadığı için isim benzersiz değildir.)*
4. Süre tolerans değeri ve puan ağırlıkları (100 + 50) nihai mi?
5. Çok dilli destek (TR/EN) gerekli mi? İlk sürüm yalnızca Türkçe önerilir.
6. DigitalOcean'da iki repo tek App altında mı (bölüm 13.3) yoksa iki ayrı App olarak mı yayınlansın? *(Öneri: iki ayrı App; repolar bağımsız deploy edilir.)*
7. Başlangıçta staging ortamı kurulsun mu, yoksa yalnızca production mı?
