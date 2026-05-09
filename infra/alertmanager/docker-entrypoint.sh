#!/bin/sh
set -eu

SECRET_DIR="${ALERTMANAGER_SECRET_DIR:-/tmp/alertmanager-secrets}"
mkdir -p "${SECRET_DIR}"
chmod 700 "${SECRET_DIR}"

require_live="${ALERTMANAGER_REQUIRE_LIVE_RECEIVERS:-false}"
telegram_token="${ALERTMANAGER_TELEGRAM_BOT_TOKEN:-000000000:stage1-local-placeholder}"
telegram_chat_id="${ALERTMANAGER_TELEGRAM_CHAT_ID:--5173727789}"
smtp_password="${ALERTMANAGER_SMTP_PASSWORD:-}"

if [ "${require_live}" = "true" ]; then
  if [ "${telegram_token}" = "000000000:stage1-local-placeholder" ] || [ -z "${telegram_token}" ]; then
    echo "ALERTMANAGER_TELEGRAM_BOT_TOKEN must be set when ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=true" >&2
    exit 1
  fi
  if [ -z "${telegram_chat_id}" ]; then
    echo "ALERTMANAGER_TELEGRAM_CHAT_ID must be set when ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=true" >&2
    exit 1
  fi
  if [ -z "${ALERTMANAGER_BACKUP_EMAIL:-}" ]; then
    echo "ALERTMANAGER_BACKUP_EMAIL must be set when ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=true" >&2
    exit 1
  fi
  if [ -z "${ALERTMANAGER_SMTP_SMARTHOST:-}" ]; then
    echo "ALERTMANAGER_SMTP_SMARTHOST must be set when ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=true" >&2
    exit 1
  fi
fi

umask 077
smtp_password_file="${ALERTMANAGER_SMTP_PASSWORD_FILE:-${SECRET_DIR}/smtp_password}"

printf '%s' "${smtp_password}" > "${smtp_password_file}"

escape_sed() {
  printf '%s' "$1" | sed -e 's/[\/&|\\]/\\&/g'
}

smtp_from="${ALERTMANAGER_SMTP_FROM:-alerts@cyber-vpn.net}"
smtp_smarthost="${ALERTMANAGER_SMTP_SMARTHOST:-mailpit-1:1025}"
smtp_hello="${ALERTMANAGER_SMTP_HELLO:-cyber-vpn.net}"
smtp_auth_username="${ALERTMANAGER_SMTP_AUTH_USERNAME:-}"
smtp_require_tls="${ALERTMANAGER_SMTP_REQUIRE_TLS:-false}"
backup_email="${ALERTMANAGER_BACKUP_EMAIL:-backup@cyber-vpn.net}"

sed \
  -e "s|\${ALERTMANAGER_TELEGRAM_BOT_TOKEN}|$(escape_sed "${telegram_token}")|g" \
  -e "s|\${ALERTMANAGER_TELEGRAM_CHAT_ID}|$(escape_sed "${telegram_chat_id}")|g" \
  -e "s|\${ALERTMANAGER_SMTP_PASSWORD_FILE}|$(escape_sed "${smtp_password_file}")|g" \
  -e "s|\${ALERTMANAGER_SMTP_FROM}|$(escape_sed "${smtp_from}")|g" \
  -e "s|\${ALERTMANAGER_SMTP_SMARTHOST}|$(escape_sed "${smtp_smarthost}")|g" \
  -e "s|\${ALERTMANAGER_SMTP_HELLO}|$(escape_sed "${smtp_hello}")|g" \
  -e "s|\${ALERTMANAGER_SMTP_AUTH_USERNAME}|$(escape_sed "${smtp_auth_username}")|g" \
  -e "s|\${ALERTMANAGER_SMTP_REQUIRE_TLS}|$(escape_sed "${smtp_require_tls}")|g" \
  -e "s|\${ALERTMANAGER_BACKUP_EMAIL}|$(escape_sed "${backup_email}")|g" \
  /etc/alertmanager/alertmanager.yml.template > /tmp/alertmanager.yml

exec /bin/alertmanager --config.file=/tmp/alertmanager.yml "$@"
