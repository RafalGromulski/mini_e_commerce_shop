# ==== builder ====
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Jeśli masz pyproject/poetry, odkomentuj odpowiednie linie.
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj projekt
COPY . /app

# (opcjonalnie) build-time collectstatic – zwykle robimy to jobem ad-hoc:
# ARG DJANGO_SETTINGS_MODULE=config.settings.prod
# ENV DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
# RUN python manage.py collectstatic --noinput


# ==== runtime ====
FROM python:3.12-slim AS runtime

# User non-root
RUN addgroup --system app && adduser --system --ingroup app --home /app app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
  && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# venv z buildera
COPY --from=builder /opt/venv /opt/venv

# Kod aplikacji
COPY --chown=app:app . /app

# Katalogi na statyki/media (montowane jako volume)
RUN mkdir -p /app/staticfiles /app/media && chown -R app:app /app

USER app

# CMD ustawia docker-compose (gunicorn/celery)
