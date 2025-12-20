#!/usr/bin/env sh
set -e

export PGPASSWORD=$POSTGRES_PASSWORD

# wait for database to be ready
until psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  echo "Waiting for Postgres..."
  sleep 2
done

echo "Postgres is ready. Running migrations..."

if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "Running Django migrations..."
  python manage.py makemigrations
  python manage.py migrate --noinput
  python manage.py createcachetable
fi

# this command is for finishing the entrypointfile/NECCESSARY
exec "$@"