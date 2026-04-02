# Incident Response Runbook

## Account Lockout Incidents

### 1. User Reports Locked Account

**Symptoms:**
- User cannot log in
- Error: "Account temporarily locked"
- Login returns 429 or 403

**Investigation:**

1. Check Redis for lockout state:
```bash
redis-cli
> KEYS login_protection:*
> GET login_protection:<user_id>
```

2. Check audit logs:
```sql
SELECT * FROM audit_logs
WHERE actor_id = '<user_id>'
AND event_type = 'login_attempt'
ORDER BY created_at DESC
LIMIT 20;
```

**Resolution:**

1. Manual unlock (if legitimate user):
```bash
redis-cli DEL login_protection:<user_id>
```

2. If brute force detected:
   - Do NOT unlock
   - Monitor for continued attempts
   - Consider IP-level blocking

### 2. Circuit Breaker Triggered

**Symptoms:**
- Many requests returning 503
- Logs show "Circuit breaker OPEN"

**Investigation:**

1. Check Redis connectivity:
```bash
redis-cli PING
```

2. Check Redis metrics:
```bash
redis-cli INFO
```

**Resolution:**

1. If Redis is down:
   - Restart Redis service
   - Circuit will auto-reset after 30 seconds

2. If Redis is overloaded:
   - Scale Redis
   - Review rate limit settings

### 3. Mass Account Lockouts

**Symptoms:**
- Multiple users locked simultaneously
- Spike in failed login attempts

**Investigation:**

1. Check for attack pattern:
```sql
SELECT ip_address, COUNT(*) as attempts
FROM audit_logs
WHERE event_type = 'login_failure'
AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY ip_address
ORDER BY attempts DESC
LIMIT 10;
```

2. Check if same IP targeting multiple accounts:
```sql
SELECT ip_address, COUNT(DISTINCT actor_id) as accounts
FROM audit_logs
WHERE event_type = 'login_failure'
AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY ip_address
HAVING COUNT(DISTINCT actor_id) > 5;
```

**Response:**

1. Block attacking IPs at firewall level
2. Review if any accounts were compromised
3. Force password reset for affected accounts

## JWT Token Incidents

### 4. Suspected Token Compromise

**Symptoms:**
- User reports unauthorized activity
- API requests from unknown locations

**Investigation:**

1. Check audit logs for the user:
```sql
SELECT * FROM audit_logs
WHERE actor_id = '<user_id>'
ORDER BY created_at DESC
LIMIT 50;
```

**Response:**

1. Revoke all user tokens:
```bash
POST /api/v1/auth/logout-all
Authorization: Bearer <admin_token>
```

2. Or via Redis:
```bash
redis-cli SADD jwt_user_tokens:<user_id> <jti>
```

3. Force password reset

### 5. JWT Secret Rotation

**When needed:**
- Secret may have been exposed
- Routine rotation (quarterly)

**Procedure:**

1. Generate new secret:
```bash
openssl rand -hex 32
```

2. Update environment variable
3. Restart services (all active tokens will be invalidated)
4. Notify users to re-login

## OAuth Incidents

### 6. OAuth State Token Mismatch

**Symptoms:**
- "Invalid state token" errors
- OAuth callbacks failing

**Investigation:**

1. Check Redis for state tokens:
```bash
redis-cli KEYS oauth_state:*
redis-cli TTL oauth_state:<token>
```

2. Common causes:
   - User waited too long (>10 minutes)
   - Multiple OAuth flows started
   - Browser blocking cookies

**Resolution:**
- Instruct user to retry OAuth flow
- Clear browser cache/cookies

### 7. Telegram Signature Validation Failures

**Symptoms:**
- All Telegram logins failing
- "Invalid signature" errors

**Investigation:**

1. Verify bot token is correct:
```bash
echo $TELEGRAM_BOT_TOKEN | head -c 20
```

2. Check if bot token was rotated in Telegram

**Resolution:**
- Update TELEGRAM_BOT_TOKEN environment variable
- Restart backend service

## Helix Transport Incidents

### 11. Helix Canary No-Go Or Applied Pause

**Symptoms:**
- Helix canary evidence returns `no-go`
- rollout shows `applied_automatic_reaction = pause-channel`
- worker emits Helix canary/control alerts

**Investigation:**

1. Fetch rollout state:
```bash
GET /api/v1/helix/admin/rollouts/<rollout_id>
Authorization: Bearer <operator_token>
```

2. Fetch formal canary evidence:
```bash
GET /api/v1/helix/admin/rollouts/<rollout_id>/canary-evidence
Authorization: Bearer <operator_token>
```

3. Check latest worker alerts for:
- `recommended_follow_up_action`
- `throughput ratio`
- `open->first-byte gap ratio`
- `continuity success`

**Response:**

1. Keep the channel paused for new Helix sessions
2. Approve a healthier replacement profile or keep the rollout in canary-only watch mode
3. Re-run canary evidence after the corrective action

### 12. Helix Desktop Fallback Spike

**Symptoms:**
- sudden rise in Helix desktop fallback events
- support bundles show sidecar recovery or readiness failures

**Investigation:**

1. Check Helix runtime events and canary evidence
2. Review the `CyberVPN Helix` Grafana dashboard
3. Collect recent desktop support bundles from affected internal users

**Response:**

1. Freeze rollout widening
2. If the fallback spike is sustained, pause the affected channel
3. Compare fallback reasons against the current active profile and route policy

### 13. Helix Node Rollback Storm

**Symptoms:**
- Helix node rollback counters increase
- rollout health shows rolled-back nodes

**Investigation:**

1. Check lab/ops stack:
```bash
bash infra/tests/test_helix_stack.sh
```

2. Verify rollback artifacts:
```bash
bash infra/tests/verify_helix_rollback.sh
```

3. Inspect node metrics:
- `helix_node_rollback_total`
- `helix_node_runtime_healthy`

**Response:**

1. Pause the affected rollout channel if rollbacks are not converging
2. Confirm last-known-good restore is being used on nodes
3. Re-bootstrap the lab stack before widening exposure again

### 14. Helix Manifest Signing Or Internal Auth Failure

**Symptoms:**
- manifest resolution fails suddenly
- adapter internal calls start returning auth errors
- new Helix manifests cannot be issued

**Investigation:**

1. Check recent Helix secret changes in `infra/.env`
2. Verify current key ID and internal token rollout state
3. Compare adapter/backend/worker configuration versions

**Response:**

1. Rotate or restore the affected Helix secret using [secret-rotation.md](/C:/project/CyberVPN/docs/secret-rotation.md)
2. Restart affected Helix services in dependency order
3. Keep stable cores available and pause Helix exposure if manifest issuance is degraded

## Rate Limiting Incidents

### 8. Legitimate Traffic Being Rate Limited

**Symptoms:**
- Users getting 429 errors
- Rate limit thresholds too low

**Investigation:**

1. Check current settings:
```bash
echo $RATE_LIMIT_REQUESTS  # Should be reasonable for your traffic
```

2. Check Redis for rate limit keys:
```bash
redis-cli KEYS cybervpn:rate_limit:*
```

**Resolution:**

1. Increase rate limits (temporarily or permanently):
```bash
RATE_LIMIT_REQUESTS=200  # Increase from default 100
```

2. Restart backend service

## 2FA Incidents

### 9. User Lost 2FA Device

**Investigation:**

1. Verify user identity through alternate means
2. Check if backup codes exist

**Resolution:**

1. Admin disables 2FA (requires reauth):
```
POST /api/v1/admin/users/<user_id>/2fa/disable
```

2. User can re-enable with new device

### 10. TOTP Time Sync Issues

**Symptoms:**
- Valid TOTP codes rejected
- "Invalid TOTP code" errors

**Investigation:**

1. Check server time:
```bash
date
timedatectl status
```

2. TOTP allows ±1 window (30 seconds)

## Helix Incidents

### 11. Helix Canary No-Go Or Applied Pause

**Symptoms:**
- worker sends `Helix Canary No-Go` or `Helix Automatic Actuation Applied`
- admin canary evidence endpoint returns `decision=no-go`
- rollout policy shows `pause-channel` or `rotate-profile-now`

**Investigation:**

1. Read current canary snapshot:
```bash
GET /api/v1/helix/admin/rollouts/<rollout_id>/canary-evidence
```

2. Check rollout status:
```bash
GET /api/v1/helix/admin/rollouts/<rollout_id>
```

3. Confirm current follow-up action from snapshot:
- `hold-channel-paused`
- `approve-profile-rotation`
- `collect-more-evidence`
- `review-canary-blockers`

**Response:**

1. If `pause-channel` is already applied:
   - keep new Helix sessions paused;
   - do not widen canary exposure;
   - validate replacement profile readiness.
2. If `rotate-profile-now` is applied:
   - confirm node and desktop assignments converge on the target profile;
   - watch continuity, fallback, and throughput evidence.
3. Export Desktop support bundles for affected clients.

### 12. Helix Runtime Rollback Or Fallback Storm

**Symptoms:**
- spike in Helix rollback counters
- Desktop fallback events increase rapidly
- node heartbeat health reports `rolled-back` or unhealthy runtime

**Investigation:**

1. Check Helix node heartbeat state and rollback totals.
2. Check Desktop runtime event evidence for fallback reason and active stable core.
3. Check the current rollout and profile posture.

**Response:**

1. Pause the rollout if fallback or rollback pressure remains elevated.
2. Verify node daemons restored last-known-good bundle.
3. Keep Desktop on stable cores until Helix evidence returns to `go` or safe `watch`.
4. Run the Helix rollback drill:
```bash
bash infra/tests/verify_helix_rollback.sh
```

### 13. Helix Evidence Surface Degraded Under Load

**Symptoms:**
- canary evidence endpoint slows or returns errors during runtime-event ingest
- worker alerts stop matching observed Desktop benchmark evidence

**Investigation:**

1. Run Helix load scenario:
```bash
locust -f backend/tests/load/test_helix_load.py --host=http://localhost:8000
```

2. Compare:
- event ingest success
- canary snapshot readability
- worker canary-control transitions

**Response:**

1. Reduce Helix canary exposure until the evidence surface remains stable under load.
2. Preserve Locust report, canary snapshot, and Desktop support bundles.
3. Re-run the load scenario after fixes before restoring rollout growth.

## Helix Incidents

### 11. Helix Canary No-Go

**Symptoms:**
- `Helix` canary evidence returns `no-go`
- worker sends `Helix Canary No-Go` or `Helix Canary Control` alerts

**Investigation:**

1. Check formal canary evidence:
```bash
GET /api/v1/helix/admin/rollouts/<rollout_id>/canary-evidence
```

2. Review:
- `decision`
- `reasons`
- `evidence_gaps`
- `recommended_follow_up_action`

**Response:**

1. Do not widen the rollout
2. Apply the follow-up action from formal canary evidence
3. If `pause-channel` is active, keep new sessions paused until the next green evidence window

### 12. Helix Automatic Actuation Applied

**Symptoms:**
- worker sends `Helix Automatic Actuation Applied`
- rollout shows `applied_automatic_reaction`

**Investigation:**

1. Check rollout state:
```bash
GET /api/v1/helix/admin/rollouts/<rollout_id>
```

2. Confirm:
- `applied_automatic_reaction`
- `applied_transport_profile_id`
- `automatic_reaction_trigger_reason`

**Response:**

1. For `pause-channel`: keep new Helix sessions paused
2. For `rotate-profile-now`: confirm node assignments and desktop manifests converge on the target profile
3. Re-run canary evidence before resuming exposure

### 13. Helix Node Rollback Failure

**Symptoms:**
- node remains unhealthy after config apply
- rollback counters keep increasing
- worker reports rollback spike

**Investigation:**

1. Run rollback verification:
```bash
bash infra/tests/verify_helix_rollback.sh
```

2. Check node health:
```bash
curl http://<helix-node-host>:8091/healthz
curl http://<helix-node-host>:8091/readyz
```

**Response:**

1. Pause the affected rollout channel
2. Restore last-known-good bundle
3. Keep the node out of widening waves until rollback verification passes again

### 14. Helix Desktop Fallback Spike

**Symptoms:**
- fallback rate rises above threshold
- desktop support bundles show repeated `fallback` runtime events

**Investigation:**

1. Inspect latest support bundle and diagnostics timeline
2. Check current canary evidence for throughput ratio and gap ratio regression

**Response:**

1. Hold the rollout in `canary`
2. Run Helix recovery drill and target-matrix benchmarks again
3. If fallback remains elevated, pause channel or rotate profile before resuming

**Resolution:**
- Sync server time with NTP
- Instruct user to sync device time

## Escalation Contacts

| Severity | Contact | Response Time |
|----------|---------|---------------|
| Critical | On-call engineer | 15 minutes |
| High | Security team | 1 hour |
| Medium | DevOps | 4 hours |
| Low | Support ticket | 24 hours |

## Post-Incident

1. Document the incident
2. Update runbook if new scenario
3. Review and improve monitoring
4. Conduct blameless post-mortem for critical incidents
