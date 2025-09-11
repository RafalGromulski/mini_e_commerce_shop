# E‑commerce API (Django 4 + DRF)

A minimal e‑commerce REST API built with **Django**, **Django REST Framework**, **SQLite**, and **Pillow**. It supports public product browsing with filtering/sorting/pagination, seller‑only product management, authenticated order placement with email confirmations, and a sales stats endpoint. Optional **Celery + Redis** sends payment reminders one day before the due date.

---

## Features
- **Products & Categories**  
  Public product list & detail, filtering, sorting, pagination; automatic image thumbnail (JPEG, max width 200px).
- **Orders**  
  Authenticated users can place orders and see their own; sellers can see all orders. Order confirmation email (console in dev).
- **Stats**  
  Top‑N most frequently ordered products within a date range.
- **Permissions**  
  Read for everyone. Writes require membership in the **seller** group (configurable via `SHOP_SELLER_GROUP`).
- **Docs**  
  OpenAPI schema + Swagger UI + ReDoc.

---

## Tech Stack
- Python 3.11+ (tested also on 3.13)
- Django 4.2+
- Django REST Framework 3.14+
- django‑filter, drf‑spectacular
- Pillow (thumbnail generation)
- django‑environ (env‑based config)
- Celery 5.x + Redis (optional, for reminders)
- SQLite (default in dev; pluggable via `DATABASE_URL`)

---

## Quickstart

### 1) Clone & install
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 2) Configure environment
Copy the example and edit values as needed:
```bash
cp .env.example .env
```
Mandatory:
- `SECRET_KEY` – set a non‑default value in non‑debug environments.

Optional highlights:
- `SHOP_SELLER_GROUP` (default: `seller`) — group used to authorize write actions.
- `EMAIL_*` — SMTP settings; default backend prints emails to console in dev.
- `DATABASE_URL` — switch from SQLite to Postgres/MySQL if needed.
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` — Redis URLs for Celery.

### 3) Migrate & create admin user
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4) Run the app
```bash
python manage.py runserver
```
Visit:
- Swagger UI: **`/api/docs/`**
- ReDoc: **`/api/redoc/`**
- OpenAPI schema (JSON/YAML): **`/api/schema/`** (`?format=yaml` available)
- Admin: **`/admin/`**

### 5) Create a seller group and add a user
```python
# python manage.py shell
from django.contrib.auth.models import Group, User

Group.objects.get_or_create(name="seller")
u = User.objects.get(username="<your_username>")
u.groups.add(Group.objects.get(name="seller"))
u.save()
```
> Note: Django admin access still requires `is_staff=True` (independent of API permissions).

---

## Configuration

Configuration lives in `config/settings.py` and is driven by environment variables (loaded from `.env` in development via **django‑environ**).

Key variables:
- `DEBUG` (`true|false`)
- `SECRET_KEY`
- `ALLOWED_HOSTS` (comma‑separated)
- `CSRF_TRUSTED_ORIGINS` (comma‑separated full origins)
- `DATABASE_URL` (e.g., `postgres://USER:PASSWORD@HOST:5432/DBNAME`)
- `EMAIL_BACKEND` / `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` / `EMAIL_USE_SSL`
- `SHOP_SELLER_GROUP` (default: `seller`)
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (default Redis on localhost)

Media files are served from `MEDIA_ROOT` in development; thumbnails are automatically generated to JPEG with max width 200px.

---

## API Overview

### Categories
`/api/categories/`
- **GET** list (public)
- **POST** create (seller)
- `/api/categories/{id}/` — **GET** retrieve (public), **PUT/PATCH/DELETE** (seller)

### Products
`/api/products/`
- **GET** list (public) with filtering, sorting, pagination
- **POST** create (seller; supports multipart for image upload)
- `/api/products/{id}/` — **GET** detail (public), **PUT/PATCH/DELETE** (seller)

**Filtering params**
- `name` — case‑insensitive contains on product name
- `description` — case‑insensitive contains
- `category` — category ID
- `category_name` — case‑insensitive contains on category name
- `price` — exact match
- `min_price`, `max_price` — inclusive range

**Ordering params**
- `ordering=name` | `-name` | `price` | `-price` | `category__name` | `-category__name`

**Pagination**
- PageNumberPagination (`PAGE_SIZE=10` by default). Use `?page=2` etc.

**Example — create product (multipart)**
```bash
curl -X POST http://127.0.0.1:8000/api/products/   -H "Cookie: sessionid=<your_session_cookie>"   -F "name=Coffee machine"   -F "description=Pressure machine"   -F "price=999.90"   -F "category=1"   -F "image=@/path/to/photo.jpg"
```

### Orders
`/api/orders/`
- **POST** create an order (authenticated user)
- **GET** list current user’s orders (authenticated). Sellers see all orders.
- `/api/orders/{id}/` — **GET** retrieve

**Create order — request body**
```json
{
  "full_name": "John Smith",
  "shipping_address": "Green St 1, 00-000 Warsaw",
  "items": [
    {"product": 1, "quantity": 2},
    {"product": 3, "quantity": 1}
  ]
}
```
**Create order — response (201)**
```json
{
  "id": 5,
  "total_price": "2199.70",
  "payment_due_date": "2025-01-15",
  "created_at": "2025-01-10T12:34:56Z"
}
```
> A plain‑text confirmation email is sent using the configured backend (console in dev).

### Stats: Top Products
`/api/stats/top-products/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&limit=N`
- **GET** sellers only — returns an array of `{ product_id, product_name, units_ordered }` ordered by `units_ordered` desc.

**Example**
```bash
curl "http://127.0.0.1:8000/api/stats/top-products/?date_from=2025-01-01&date_to=2025-01-31&limit=5"   -H "Cookie: sessionid=<your_session_cookie>"
```

---

## Celery (optional): Payment reminders

Start **Redis**, **Celery worker**, and **Celery beat**:
```bash
# 1) Redis
# docker run -p 6379:6379 --name redis -d redis:7

# 2) Worker (in one terminal)
celery -A config worker -l info

# 3) Beat scheduler (in another terminal)
celery -A config beat -l info
```
A daily beat task runs at 09:00 (project timezone) and sends reminders for orders due **tomorrow**. You can trigger manually:
```bash
python manage.py shell
>>> from shop.tasks import send_payment_reminders
>>> send_payment_reminders()          # synchronous test
# or
>>> send_payment_reminders.delay()    # async via Celery
```

> **Note:** In typical dev setups a single worker runs; if you run multiple workers, consider adding a claim/lock mechanism to avoid duplicate emails.

---

## Development

### Linting & typing (optional)
You can add these to a `requirements-dev.txt`:
```
ruff
mypy
django-stubs
djangorestframework-stubs
typing-extensions
```
Example `mypy.ini`:
```ini
[mypy]
plugins = mypy_django_plugin.main, mypy_drf_plugin.main
ignore_missing_imports = True
strict_optional = True
warn_unused_ignores = True
disallow_untyped_defs = True
disallow_incomplete_defs = True

[mypy.plugins.django-stubs]
django_settings_module = config.settings
```

### Project structure (key files)
```
config/
  settings.py
  urls.py
  celery.py
shop/
  models.py
  serializers.py
  views.py
  filters.py
  permissions.py
  tasks.py
  signals.py
```

---

## Notes & Guarantees
- Thumbnails are generated as JPEG (quality 85) with max width 200px; original aspect ratio preserved; no upscaling.
- Monetary fields use `Decimal` with non‑negative validation.
- Public read access; writes are enforced by DRF permissions (seller group).
- Orders are tied to `auth_user`; totals are recomputed on line changes.

---

## License
`MIT LICENSE`
