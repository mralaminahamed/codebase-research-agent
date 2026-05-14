#!/bin/bash
set -e
tailwindcss -i assets/tailwind.input.css -o research/static/css/tailwind.css --minify
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
