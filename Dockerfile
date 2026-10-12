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
# collectstatic için geçici anahtar; gerçek SECRET_KEY çalışma zamanında verilir.
RUN SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && useradd -m app && chown -R app /app
USER app
EXPOSE 8080
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 3 --timeout 30"]
