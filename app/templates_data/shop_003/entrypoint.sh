#!/bin/bash

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# Make sure the line endings are set to LF, not CRLF.
# CRLF line endings may cause the error: 'exec ./entrypoint.sh: no such file or directory'
# This can happen if the script was edited or saved in a Windows environment.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --noinput

gunicorn core.config.wsgi:application --bind 0.0.0.0:8000 &

python3 manage.py bot
