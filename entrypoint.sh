#!/bin/sh
# Yerel geliştirme: veritabanını bekle, migrate et, komutu başlat.
# Üretimde migrate App Platform PRE_DEPLOY job'ında çalışır; bu betik kullanılmaz.
set -e
python - <<'PY'
import os, time
import dj_database_url
import psycopg

url = os.environ.get("DATABASE_URL", "")
if url.startswith("postgres"):
    for _ in range(30):
        try:
            psycopg.connect(url, connect_timeout=2).close()
            break
        except psycopg.OperationalError:
            time.sleep(1)
PY
python manage.py migrate --noinput
exec "$@"
