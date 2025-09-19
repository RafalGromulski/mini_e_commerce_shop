# 🛍️ Mini E-Commerce Shop API

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Django](https://img.shields.io/badge/django-5.1%2B-green.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A minimalist REST API for an e-commerce shop built with **Django 5.1+** and **Django REST Framework**.  
It supports a public product catalog (with filtering/sorting/pagination), seller-only product management, authenticated order placement with confirmation e-mails, sales statistics, and optional **Celery + Redis** for payment reminders.

---

## ✨ Features

- **Products & Categories** – public browsing, filtering, sorting, pagination; automatic image thumbnails (JPEG, max width 200px).  
- **Orders** – authenticated users place orders; sellers see all. Confirmation e-mail after creation.  
- **Statistics** – top-N most ordered products by date range (seller-only).  
- **Permissions** – read for all, write restricted to the `seller` group.  
- **Docs** – OpenAPI schema + Swagger UI + ReDoc.  
- **Async** – Celery + Redis tasks for payment reminders.  

---

## 🛠️ Tech Stack

- Python **3.13**
- Django **5.1+**
- Django REST Framework **3.15+**
- django-filter, drf-spectacular
- Pillow (image handling)
- django-environ (environment config)
- Celery **5.5+** + Redis (optional)
- SQLite (default) / Postgres/MySQL via `DATABASE_URL`

---

## 🚀 Quickstart (Development)

### 1. Clone & install
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -U pip
pip install pip-tools
pip-compile requirements.in
pip-compile requirements-dev.in
pip install -r requirements-dev.txt
```

### 2. Configure environment
```bash
cp .env.example .env
```

> The `.env` file is not versioned (it is in `.gitignore`), and `.env.example` contains all the variables required to run the project.

Important variables:
- `SECRET_KEY` — required in production
- `DEBUG` — `1` or `0`
- `DATABASE_URL` — e.g. `postgres://user:pass@localhost:5432/shop`
- `SHOP_SELLER_GROUP` — default: `seller`
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` — Redis connections

> If you do not set `DATABASE_URL`, the project will use the default SQLite database (`db.sqlite3` in the project root).

### 3. Migrate & create superuser
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run the app
```bash
python manage.py runserver
```

Docs:
- Swagger UI → [/api/docs/](http://127.0.0.1:8000/api/docs/)
- ReDoc → [/api/redoc/](http://127.0.0.1:8000/api/redoc/)
- OpenAPI schema → [/api/schema/](http://127.0.0.1:8000/api/schema/)
- Admin → [/admin/](http://127.0.0.1:8000/admin/)

---

## 📦 API Overview

### Categories
- `GET /api/categories/` – list (public)  
- `POST /api/categories/` – create (seller)  
- `GET /api/categories/{id}/`, `PUT/PATCH/DELETE` – detail (seller for write)  

### Products
- `GET /api/products/` – list (filters: `name`, `description`, `category`, `category_name`, `min_price`, `max_price`; order: `name`, `price`, `category__name`)  
- `POST /api/products/` – create (seller; multipart image upload)  
- `GET /api/products/{id}/`, `PUT/PATCH/DELETE` – detail (seller for write)  

### Orders
- `POST /api/orders/` – place order (authenticated)  
- `GET /api/orders/` – user’s own orders; all for sellers  
- `GET /api/orders/{id}/` – detail  

### Statistics
- `GET /api/stats/top-products/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&limit=N` – top ordered products (seller only)  

---

## ⏱️ Celery (Optional)

Celery is used for asynchronous tasks (e.g. sending payment reminders).  
There are two ways to run it locally:

### Option A – Run manually

```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Start Celery worker
celery -A config worker -l info

# Start Celery beat scheduler
celery -A config beat -l info
```

> Daily beat runs at 09:00 (project timezone) to send payment reminders for orders due the next day.

---

### Option B – Use Docker Compose

This project ships with a `docker-compose.yaml` for local development.

```bash
# Start Redis, Celery worker, and Celery beat
docker compose up -d redis celery-worker celery-beat
```

Then in a separate terminal, run Django locally:

```bash
python manage.py runserver
```

Celery will now use the Redis service from Docker (`redis://redis:6379/0`).

---

## 🧪 Testing

Run the test suite:

```bash
pytest -q
```

Run with coverage:

```bash
pytest --cov=shop --cov-report=term-missing
```
Run with coverage:

```bash
pytest --cov=shop --cov-report=term-missing
```

> The test suite uses **pytest** and **pytest-django**.  
> Configuration is stored in `pyproject.toml` under `[tool.pytest.ini_options]`  
> (default settings module: `config.settings.dev`).

---

## 🔧 Contributing

1. Fork the repo and create your branch from `main`.
2. Install dev dependencies:  
   ```bash
   pip install pip-tools
   pip-compile requirements.in
   pip-compile requirements-dev.in
   pip install -r requirements-dev.txt
   ```
3. Run linting & typing checks:  
   ```bash
   pre-commit run --all-files
   ```
4. Ensure tests pass:  
   ```bash
   pytest -q
   ```
5. Submit a Pull Request 🚀

---

## 🌍 Deployment (Production)

- **Settings**: use `config/settings/prod.py`
- **Environment**: set `DJANGO_SETTINGS_MODULE=config.settings.prod`
- **Database**: configure `DATABASE_URL` (Postgres/MySQL recommended)
- **Static files**: run `python manage.py collectstatic`
- **Celery**: start both worker and beat with a process manager (systemd, supervisord, or Docker)
- **Gunicorn/Uvicorn**: recommended for WSGI/ASGI serving
- **Reverse proxy**: Nginx or Caddy for HTTPS termination

---

## 👨‍💻 Development

### Code quality
- **Black** – formatting  
- **isort** – import sorting  
- **flake8** (+bugbear, +comprehensions) – linting  
- **mypy** + django-stubs – typing  

### Pre-commit
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

> Install the pre-commit hooks with pre-commit install to automatically format and lint code on every commit.

### Tests
```bash
pytest -q
```

---

## 📂 Project Structure

```
.
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── celery.py
│   ├── urls.py
│   ├── views.py
│   ├── wsgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py
│       ├── dev.py
│       ├── prod.py
│       └── staging.py
├── shop/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── filters.py
│   ├── management/
│   │   └── commands/
│   │       └── ensure_seller_group.py
│   ├── migrations/
│   ├── static/
│   ├── tests/
│   ├── models.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── signals.py
│   ├── tasks.py
│   ├── urls.py
│   └── views.py
├── media/ # created locally, not versioned
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── docker-compose.yaml
├── LICENSE
├── manage.py
├── pyproject.toml
├── requirements.in
├── requirements-dev.in
└── README.md
```
> `media/` — folder for user uploads (e.g. product images).  
Must be created manually in development (`mkdir media`) but **should not be committed** (already in `.gitignore`).  
In production, serve it via Nginx or an external storage service (S3/GCS).

---
