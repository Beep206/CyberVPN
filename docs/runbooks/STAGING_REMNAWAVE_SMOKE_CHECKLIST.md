# Staging Remnawave 2.7.4 Smoke Checklist

Run this checklist immediately after a staging Remnawave edge rollout.

This checklist is intentionally narrower than the generic edge verification checklist. It confirms that a `2.7.4` edge node is not only running, but is also visible to Remnawave and still works through the backend facade.

Operator shortcut:

```bash
cd /home/beep/projects/VPNBussiness/infra
make remnawave-staging-smoke
```

## Preconditions

1. Complete the staging rollout first:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-phase3-staging
make ansible-remnawave-verify-staging
```

2. Prepare operator variables:

```bash
export REMNAWAVE_BASE_URL="https://<staging-remnawave-host>"
export REMNAWAVE_API_TOKEN="<staging-remnawave-api-token>"
export API_BASE_URL="https://<staging-backend-host>/api/v1"
export EXPECTED_NODE_NAME="<staging-node-name>"

export ADMIN_LOGIN="<staging-admin-login-or-email>"
export ADMIN_PASSWORD="<staging-admin-password>"

export SMOKE_USER_LOGIN="<disposable-staging-user-login-or-email>"
export SMOKE_USER_PASSWORD="<disposable-staging-user-password>"

# Optional and intentionally explicit because it changes smoke-user state.
# Set only for a disposable staging user.
# export SMOKE_ALLOW_CANCEL=true
```

3. Use a disposable or resettable staging user for subscription checks.
`POST /api/v1/subscriptions/cancel` is a state-changing operation and must not be run against a real long-lived test account.

## 1. Verify node registration in Remnawave

The upgraded edge node must still appear in the Remnawave node list and report as connected.

```bash
curl -fsS "$REMNAWAVE_BASE_URL/api/nodes" \
  -H "Authorization: Bearer $REMNAWAVE_API_TOKEN" | jq
```

Check:

- the expected node exists
- `isConnected` is `true` for the expected node
- the node does not flap between connected and disconnected

Focused query:

```bash
curl -fsS "$REMNAWAVE_BASE_URL/api/nodes" \
  -H "Authorization: Bearer $REMNAWAVE_API_TOKEN" \
  | jq --arg NODE "$EXPECTED_NODE_NAME" '.response[] | select(.name == $NODE) | {name, isConnected, isDisabled, isConnecting, xrayVersion}'
```

## 2. Issue backend admin token

Monitoring and node-plugin endpoints require an admin role.

```bash
ADMIN_TOKEN=$(
  curl -fsS -X POST "$API_BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"login_or_email\":\"$ADMIN_LOGIN\",\"password\":\"$ADMIN_PASSWORD\"}" \
  | jq -r '.access_token'
)

test -n "$ADMIN_TOKEN" && test "$ADMIN_TOKEN" != "null"
```

## 3. Check backend monitoring health

```bash
curl -fsS "$API_BASE_URL/monitoring/health" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

Check:

- response status is `healthy`
- database is healthy
- redis is healthy
- Remnawave is healthy

## 4. Check backend monitoring stats

```bash
curl -fsS "$API_BASE_URL/monitoring/stats" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

Check:

- response contains a fresh `timestamp`
- `total_servers` is greater than `0`
- `online_servers` is greater than `0`
- values are not all zeros unless staging is intentionally empty

## 5. Check node plugins facade

This confirms the backend can still talk to Remnawave `2.7.4` plugin endpoints after the node upgrade.

```bash
curl -fsS "$API_BASE_URL/node-plugins/" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

Check:

- request returns `200`
- response shape is valid JSON and not an upstream error page
- plugin list is returned even if it is empty

## 6. Issue disposable user token

```bash
SMOKE_USER_TOKEN=$(
  curl -fsS -X POST "$API_BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"login_or_email\":\"$SMOKE_USER_LOGIN\",\"password\":\"$SMOKE_USER_PASSWORD\"}" \
  | jq -r '.access_token'
)

test -n "$SMOKE_USER_TOKEN" && test "$SMOKE_USER_TOKEN" != "null"
```

## 7. Check subscription read path

```bash
curl -fsS "$API_BASE_URL/subscriptions/active" \
  -H "Authorization: Bearer $SMOKE_USER_TOKEN" | jq
```

Check:

- request returns `200`
- `status` is present
- subscription fields parse correctly
- traffic fields are present when expected for that smoke user

## 8. Check subscription cancel path

Run this only against the disposable smoke user prepared for this checklist.

```bash
curl -fsS -X POST "$API_BASE_URL/subscriptions/cancel" \
  -H "Authorization: Bearer $SMOKE_USER_TOKEN" | jq
```

Check:

- request returns `200`
- response contains `canceled_at`
- repeated calls eventually hit the documented rate limit behavior instead of a server error

If the smoke user should remain reusable, restore or recreate it after the test.

## 9. Record rollout evidence

Capture and store:

- deployed Remnawave edge image tag
- target inventory hostname
- node registration evidence from `/api/nodes`
- `monitoring/health` response
- `monitoring/stats` response
- `node-plugins` response
- `subscriptions/active` response
- `subscriptions/cancel` response

## Failure handling

If any step fails:

1. stop the rollout from widening
2. capture the failing response body and timestamp
3. inspect host logs and container status on the canary
4. roll back if the failure indicates a real compatibility regression:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-remnawave-rollback-staging
```
