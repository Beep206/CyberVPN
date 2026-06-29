#!/usr/bin/env bash
set -Eeuo pipefail

HOST="${HOST:-https://my.cyber-vpn.net}"
if [[ -n "${LOCALES:-}" ]]; then
  read -r -a locales <<<"$LOCALES"
elif [[ -n "${LOCALE:-}" ]]; then
  locales=("$LOCALE")
else
  locales=("en-EN" "ru-RU")
fi

route_segments=(
  "/dashboard"
  "/subscriptions"
  "/payment-history"
  "/referral"
  "/rewards"
  "/rewards/referral"
  "/rewards/gifts"
  "/rewards/invites"
  "/rewards/codes"
  "/rewards/notifications"
  "/messages"
  "/wallet"
  "/settings"
  "/support"
  "/servers"
  "/onboarding"
  "/monitoring"
  "/analytics"
  "/users"
  "/partner"
)

base_host="${HOST%/}"
status=0

printf 'RSC route smoke host=%s locales=%s\n' "$base_host" "${locales[*]}"

check_response() {
  local label="$1"
  local url="$2"
  local http_code="$3"
  local location="$4"

  if [[ "$http_code" == "000" ]]; then
    printf 'FAIL %s %s curl-failed\n' "$label" "$url"
    status=1
    return
  fi

  if [[ "$http_code" == 30* ]]; then
    printf 'FAIL %s %s http=%s location=%s\n' "$label" "$url" "$http_code" "${location:-<empty>}"
    status=1
    return
  fi

  if [[ "$location" == https://cyber-vpn.net/* || "$location" == https://www.cyber-vpn.net/* ]]; then
    printf 'FAIL %s %s http=%s cross-origin-location=%s\n' "$label" "$url" "$http_code" "$location"
    status=1
    return
  fi

  printf 'PASS %s %s http=%s\n' "$label" "$url" "$http_code"
}

read_location_header() {
  local headers_file="$1"
  tr -d '\r' <"$headers_file" \
    | awk 'tolower($0) ~ /^location:/ {sub(/^[^:]+:[[:space:]]*/, ""); print}' \
    | tail -n 1
}

for locale in "${locales[@]}"; do
  for segment in "${route_segments[@]}"; do
    route="/${locale}${segment}"
    headers_file="$(mktemp)"
    url="${base_host}${route}?_rsc=customer-site-smoke"
    if ! http_code="$(
      curl -sS -o /dev/null -D "$headers_file" -w '%{http_code}' \
        -H 'RSC: 1' \
        -H 'Accept: text/x-component' \
        -H 'Next-Router-State-Tree: []' \
        -H 'Sec-Fetch-Mode: cors' \
        -H 'Sec-Fetch-Dest: empty' \
        "$url"
    )"; then
      http_code="000"
    fi
    location="$(read_location_header "$headers_file")"
    rm -f "$headers_file"

    check_response "RSC" "$url" "$http_code" "$location"

    headers_file="$(mktemp)"
    if ! http_code="$(
      curl -sS -o /dev/null -D "$headers_file" -w '%{http_code}' \
        -X OPTIONS \
        -H 'Origin: https://my.cyber-vpn.net' \
        -H 'Access-Control-Request-Method: GET' \
        -H 'Access-Control-Request-Headers: rsc,next-router-state-tree' \
        "$url"
    )"; then
      http_code="000"
    fi
    location="$(read_location_header "$headers_file")"
    rm -f "$headers_file"

    check_response "OPTIONS" "$url" "$http_code" "$location"
  done
done

exit "$status"
