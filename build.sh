#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Convert static files (CSS/JS)
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate