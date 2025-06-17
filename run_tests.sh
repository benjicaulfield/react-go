#!/bin/sh

# Set required environment variables for Django
export SECRET_KEY=django-insecure-development-key-for-docker
export DEBUG=True
export DB_NAME=test_db
export DB_USER=test_user
export DB_PASSWORD=test_pass
export DB_HOST=localhost
export DB_PORT=5432

# Run Django tests (Django will create its own test database)
echo "Running Django tests..."
python manage.py test discogs --verbosity=2

echo "Tests completed!"