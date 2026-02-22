#!/bin/sh
set -e

flask init-db

exec gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"
