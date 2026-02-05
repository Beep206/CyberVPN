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
