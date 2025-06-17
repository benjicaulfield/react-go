FROM python:3.12-slim

# Install PostgreSQL and system dependencies
RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    gcc \
    sudo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install psycopg2-binary==2.9.7

COPY . .

# Create entrypoint script
RUN echo '#!/bin/bash \n\
set -e \n\
\n\
# Start PostgreSQL \n\
service postgresql start \n\
\n\
# Wait for PostgreSQL to be ready \n\
until sudo -u postgres pg_isready; do \n\
  echo "Waiting for PostgreSQL..." \n\
  sleep 1 \n\
done \n\
\n\
# Create database and user with proper permissions \n\
sudo -u postgres createdb discogs_db || true \n\
sudo -u postgres createuser discogs_user || true \n\
sudo -u postgres psql -c "ALTER USER discogs_user WITH PASSWORD '"'"'discogs_pass'"'"';" \n\
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE discogs_db TO discogs_user;" \n\
sudo -u postgres psql -c "ALTER USER discogs_user CREATEDB;" \n\
sudo -u postgres psql discogs_db -c "GRANT ALL ON SCHEMA public TO discogs_user;" \n\
sudo -u postgres psql discogs_db -c "GRANT CREATE ON SCHEMA public TO discogs_user;" \n\
\n\
# Set environment variables for Django \n\
export SECRET_KEY=django-insecure-development-key-for-docker \n\
export DEBUG=True \n\
export DB_NAME=discogs_db \n\
export DB_USER=discogs_user \n\
export DB_PASSWORD=discogs_pass \n\
export DB_HOST=localhost \n\
\n\
# Run Django setup \n\
python manage.py makemigrations \n\
python manage.py migrate \n\
\n\
# Start Django \n\
python manage.py runserver 0.0.0.0:8000 \n\
' > /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 8000

CMD ["/entrypoint.sh"]