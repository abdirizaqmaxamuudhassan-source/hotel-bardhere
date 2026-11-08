# HOTEL BARDHERE HB – website and management system

Django 4.2+/5 · Bootstrap 5 · Chart.js · Font Awesome · SQLite (dev) / PostgreSQL (production)

## 1. Quick start (development)

```bash
cd hotel_bardhere
./setup.sh            # Linux/macOS; does everything below
```

Or step by step:

```bash
python3 -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations core rooms bookings dashboard   # creates the migration files
python manage.py migrate
python manage.py seed_demo --with-staff     # optional starter rooms, services, menu + sample staff logins
python manage.py createsuperuser            # your owner account
python manage.py runserver
```

* Public website: http://127.0.0.1:8001/
* Staff dashboard: http://127.0.0.1:8001/manage/   (log in with the owner account)
* Technical Django admin (superusers only): http://127.0.0.1:8001/admin/
* Run the tests: `python manage.py test`

`seed_demo --with-staff` prints random passwords once for `manager`, `reception` and `accounts`.
Change or delete these accounts in Dashboard > Employees before going live.

## 2. Changing everything (hotel details)

Dashboard > **Site settings** controls: hotel name, taglines, story/mission/vision (English and Somali),
**address** (default: "Buundo, Baydhabo road, Bardhere, Gedo, Somalia"), phone, WhatsApp, email, Facebook/Instagram,
Google Maps link, currency symbol, check-in/out times, invoice note, hero and about photos.
**Replace the placeholder phone, WhatsApp and email** – they are not real.

Photos: upload hero/about images in Site settings, room photos in Room types & prices, gallery photos in Gallery,
dish photos in Restaurant menu. No stock photos are bundled; until you upload photos the site shows navy/gold placeholders.

## 3. Roles

| Role | Access |
|---|---|
| Owner (superuser) | everything, including Django admin |
| Manager | everything in the dashboard, can delete records |
| Receptionist | overview, reservations, customers, payments |
| Accountant | overview, reservations, payments, reports |

Create staff in Dashboard > Employees (this also creates their login). Passwords are hashed (PBKDF2) and must pass
Django's strength checks (10+ characters). Five failed logins lock that username/IP for 15 minutes.

## 4. How booking works

* Guests choose room type + dates. The server picks a free room of that type and creates a **Pending** booking.
* A room is blocked for any date range that overlaps a Pending or Confirmed booking (leaving and arriving on the same day is allowed).
  Cancelling frees the room. The check runs in the public form, in a database transaction (row locks on PostgreSQL),
  in the staff booking form, and when changing status.
* Guests can look a booking up with reference + phone number. Staff confirm or cancel from Reservations.

## 5. Payments

Methods: Cash, Mobile Money, EVC Plus, ZAAD, eDahab. Staff record amount, method, transaction reference, date and status.
**No payment API is integrated: mobile-money payments are NOT verified automatically.** Staff copy the reference from the
customer's confirmation message. Receipts and invoices say so. Real verification would require an agreement with the
operator and their API.

## 6. Language

EN / SO switcher on the public site. Interface strings live in `core/i18n.py`; content in Somali is entered in the
`(Somali)` fields in the dashboard (falls back to English when empty). Please have a Somali speaker review the translations.
The staff dashboard is English only.

## 7. Production (PostgreSQL)

```bash
export DJANGO_DEBUG=False DJANGO_SECRET_KEY='long-random-value' DJANGO_ALLOWED_HOSTS=yourdomain.com
export DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com
export DB_ENGINE=postgres DB_NAME=bardhere_hb DB_USER=bardhere_hb DB_PASSWORD=... DB_HOST=localhost
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

See `.env.example` for all variables (email too). Put Nginx/Caddy with HTTPS in front, serve `/media/` (uploaded photos)
from `media/` via the web server, back up the database, and consider renaming the `/admin/` URL in `config/urls.py`.
Bootstrap, Chart.js, Font Awesome and Google Fonts load from CDNs, so visitors need internet access.
