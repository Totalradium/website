#!/bin/bash
export SECRET_KEY="django-insecure-$(openssl rand -base64 32)"
export DEBUG=False
export PORT=${PORT:-10000}
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn website.wsgi:application --bind 0.0.0.0:${PORT}