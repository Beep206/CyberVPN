#!/bin/sh
set -e

# Set default webhook URL if not provided
ALERTMANAGER_WEBHOOK_URL="${ALERTMANAGER_WEBHOOK_URL:-https://your-telegram-relay.example.com/alert}"

# Preprocess alertmanager.yml.template to inject environment variables
sed "s|\${ALERTMANAGER_WEBHOOK_URL}|${ALERTMANAGER_WEBHOOK_URL}|g" \
  /etc/alertmanager/alertmanager.yml.template > /tmp/alertmanager.yml

# Start AlertManager with the processed config
exec /bin/alertmanager --config.file=/tmp/alertmanager.yml "$@"
