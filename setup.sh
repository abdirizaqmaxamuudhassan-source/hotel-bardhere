#!/usr/bin/env bash
# One-time development setup (Linux / macOS). Windows: run the same commands in PowerShell.
set -e
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations core rooms bookings dashboard
python manage.py migrate
python manage.py seed_demo --with-staff     # starter rooms/menu + sample staff logins (passwords printed once)
echo "Now create your own owner account:"
python manage.py createsuperuser
echo "Start the site with:  python manage.py runserver"
