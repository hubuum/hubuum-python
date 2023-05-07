#!/bin/sh

# Exit on error
set -e

MODE="${MODE:-production}"

# Run Django migrations
python manage.py migrate 

# pass signals on to the gunicorn process
function sigterm()
{
	echo "Received SIGTERM"
	kill -term $( cat /var/run/gunicorn.pid )
}
trap sigterm SIGTERM

export DJANGO_SETTINGS_MODULE=hubuumsite.settings

# Run tests if in testing mode
if [ "$MODE" = "testing" ]; then
    # Run Django test suite
    exec python manage.py test --noinput --failfast
else
    export HUBUUM_LOGGING_PRODUCTION=true
    # Start the application using Gunicorn, store its PID, set the worker temporary directory, and wait for it to terminate
    gunicorn hubuumsite.wsgi:application --workers=3 --bind 0.0.0.0:8099 --pid /var/run/gunicorn.pid --worker-tmp-dir /dev/shm --log-level error &
    wait $!
fi
