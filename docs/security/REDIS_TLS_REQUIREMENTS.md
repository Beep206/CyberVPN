# Redis TLS Configuration Requirements

**SEC-016**: This document describes the Redis TLS requirements for production deployment.

## Overview

Redis connections MUST use TLS in production environments to encrypt data in transit. This protects:
- JWT tokens stored in the revocation blocklist
- Session data and user tokens
- OTP codes and verification data
- Rate limiting state

## Production Requirements

### 1. Enable TLS on Redis Server

For self-hosted Redis:

```conf
# redis.conf
port 0
tls-port 6379
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
tls-auth-clients yes
```

For managed Redis services (AWS ElastiCache, Redis Cloud, etc.):
- Enable "Encryption in transit" in the service configuration
- Use the provided TLS endpoint

### 2. Configure Backend Connection

Update the `REDIS_URL` environment variable to use `rediss://` (note the double 's'):

```env
# Production .env
REDIS_URL=rediss://user:password@redis-host:6379/0
```

For self-signed certificates, you may need to provide CA certificates:

```python
# In code, if using custom CA
import ssl
import redis.asyncio as redis

ssl_context = ssl.create_default_context(cafile="/path/to/ca.crt")
redis_client = redis.from_url(
    settings.redis_url,
    ssl=ssl_context,
)
```

### 3. Certificate Management

- Use certificates from a trusted CA or your organization's PKI
- Set certificate expiry monitoring alerts
- Rotate certificates before expiry (recommended: 90 days before)

## Development Environment

TLS is **not required** in development for ease of setup. The local Docker Compose stack uses unencrypted Redis:

```yaml
# infra/docker-compose.yml (development only)
redis:
  image: valkey/valkey:8.1
  ports:
    - "127.0.0.1:6379:6379"  # Bound to localhost only
```

**Security note**: Development Redis is bound to `127.0.0.1` and not exposed externally.

## Verification

### Check TLS is enabled

```bash
# Should fail without TLS (connection refused)
redis-cli -h redis-host ping

# Should succeed with TLS
redis-cli -h redis-host --tls --cacert ca.crt ping
```

### From application logs

Look for these log entries on startup:
- `"Connected to Redis (TLS enabled)"` - TLS working
- `"WARNING: Redis connection is not encrypted"` - TLS not enabled

## Checklist

- [ ] Redis server configured with TLS certificates
- [ ] `REDIS_URL` uses `rediss://` protocol
- [ ] Certificates are from a trusted CA
- [ ] Certificate expiry monitoring is set up
- [ ] Application logs confirm TLS connection
- [ ] Network policies restrict Redis access to backend services only

## Related Security Controls

- **SEC-003**: JWT token revocation stored in Redis
- **SEC-010**: Session limits enforced via Redis
- **SEC-012**: Rate limiting state in Redis

## References

- [Redis TLS Documentation](https://redis.io/docs/management/security/encryption/)
- [AWS ElastiCache Encryption](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/in-transit-encryption.html)
- [Redis Cloud TLS](https://docs.redis.com/latest/rc/security/database-security/tls-ssl/)
