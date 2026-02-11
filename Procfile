web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn mechatronics_hub.wsgi --bind 0.0.0.0:$PORT --log-file - --timeout 120
