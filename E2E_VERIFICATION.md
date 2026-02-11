# E2E Backend Endpoint Verification

Comprehensive end-to-end verification script for all CyberVPN backend API endpoints.

## Overview

The `e2e_verify_endpoints.py` script tests **38 backend endpoints** across all modules:
- **Auth** (12 endpoints): register, login, verify, 2FA flows
- **VPN** (1 endpoint): usage stats
- **Wallet** (3 endpoints): balance, transactions, withdraw
- **Payments** (3 endpoints): create invoice, invoice status, history
- **Subscriptions** (3 endpoints): list, get, config
- **Codes** (1 endpoint): validate promo
- **Referral** (4 endpoints): status, code, stats, recent commissions
- **Profile** (2 endpoints): get, update
- **Security** (4 endpoints): change password, antiphishing CRUD
- **Trial** (2 endpoints): activate, status

## Features

✅ Tests all HTTP methods (GET, POST, PATCH, DELETE)
✅ Automatic authentication setup with test user
✅ Color-coded output (green = pass, red = fail)
✅ Response time measurement for each endpoint
✅ Summary statistics (pass/fail count, average response time)
✅ Exit code 0 on success, 1 on failure (CI/CD compatible)

## Prerequisites

```bash
pip install requests
```

## Usage

### Default (localhost:8000)

```bash
python e2e_verify_endpoints.py
```

### Custom backend URL

```bash
python e2e_verify_endpoints.py --base-url http://api.example.com
```

### Run with Python directly

```bash
./e2e_verify_endpoints.py
```

## Output Example

```
Setting up authentication...
✓ Test user ready (status 201)
✓ Authentication successful

================================================================================
E2E Endpoint Verification
================================================================================

✓ POST   /auth/register                                      [201]    45ms Register new user
✓ POST   /auth/login                                         [200]    38ms User login
✓ POST   /auth/verify-email                                  [400]    12ms Verify email (expected 400)
✓ GET    /vpn/usage                                          [200]    67ms VPN usage stats
✓ GET    /wallet/balance                                     [200]    54ms Wallet balance
...

================================================================================
Summary

  Total endpoints tested: 38
  Passed: 38
  Failed: 0
  Average response time: 42ms
================================================================================

✓ All endpoint tests passed!
```

## Test Categories

### Authentication Flow Tests
- User registration (expected 201)
- User login (expected 200)
- Email verification with invalid code (expected 400)
- Token refresh
- Logout
- 2FA complete cycle

### Authenticated Endpoint Tests
All other endpoints require authentication and test:
- GET requests (lists, status, stats)
- POST requests (create, activate, validate)
- PATCH requests (updates)
- DELETE requests (deletions)

### Error Handling Tests
Several tests expect specific error codes:
- `400` - Invalid input (bad OTP code, etc.)
- `401` - Unauthorized (wrong password)
- `404` - Not found (non-existent resources)

## CI/CD Integration

The script exits with code 0 on success, 1 on failure, making it suitable for CI pipelines:

```yaml
# .github/workflows/e2e-test.yml
- name: Run E2E verification
  run: python e2e_verify_endpoints.py --base-url ${{ secrets.API_URL }}
```

## Authentication

The script automatically:
1. Registers a test user `e2e_test@example.com` (or reuses if exists)
2. Logs in to obtain access/refresh tokens
3. Uses Bearer token authentication for protected endpoints
4. Continues with limited tests if authentication fails

## Response Time Monitoring

Each endpoint reports response time in milliseconds. Use this to:
- Identify slow endpoints
- Monitor performance regressions
- Set SLA thresholds

## Troubleshooting

### "requests library not installed"
```bash
pip install requests
```

### "Connection failed"
- Verify backend is running: `docker compose up` or `npm run dev`
- Check URL is correct: `--base-url http://localhost:8000`

### Authentication failures
- Backend may require database setup
- Check logs for specific errors

## Extending the Script

To add new endpoints, edit `e2e_verify_endpoints.py`:

```python
endpoints = [
    # ... existing endpoints ...
    EndpointTest('GET', '/new/endpoint', True, None,
                 "Description", 200),
]
```

Parameters:
- Method: 'GET', 'POST', 'PATCH', 'DELETE'
- Path: endpoint path (without base URL)
- Requires auth: `True` or `False`
- Body: JSON dict or `None`
- Description: human-readable description
- Expected status: HTTP status code (default 200)

## License

Part of CyberVPN backend test suite.
