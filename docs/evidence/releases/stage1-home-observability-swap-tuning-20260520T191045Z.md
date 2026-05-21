# Stage 1 Home Observability Swap Tuning

Date: `2026-05-20T19:10:45Z`

Scope: close home observability swap warning alerts before continuing to `STAGE1-RENT-14`.

Host: `cybervpn-h-ops` / `10.10.10.34`

## Result

```text
PASS_SWAP_WARNINGS_CLOSED
```

## Initial State

Prometheus firing alerts:

```text
CyberVPNSwapInUse
CyberVPNSwapUsageAbove1GiB
```

Initial host memory:

```text
Mem: 46Gi total, 17Gi available
Swap: 31Gi total, 15.6Gi used
```

The main pressure source was `cybervpn-gitlab`, which was using almost the full `16 GiB` container memory limit. GitLab had auto-sized itself for the high CPU count and generated:

```text
Puma workers before tuning: 45
Nginx worker_processes before tuning: 72
Sidekiq concurrency before tuning: 20
```

## Changes

GitLab was tuned for the home operations role, not for high-traffic public runtime.

Config block added to `/etc/gitlab/gitlab.rb` inside `cybervpn-gitlab`:

```ruby
### CyberVPN home ops memory tuning start
puma['worker_processes'] = 4
puma['min_threads'] = 2
puma['max_threads'] = 4
puma['per_worker_max_memory_mb'] = 900
sidekiq['concurrency'] = 10
nginx['worker_processes'] = 2
prometheus_monitoring['enable'] = false
### CyberVPN home ops memory tuning end
```

Backup created inside the GitLab container:

```text
/etc/gitlab/gitlab.rb.bak-cybervpn-swap-tuning-20260520T190322Z
```

Applied with:

```text
gitlab-ctl reconfigure
docker restart cybervpn-gitlab
```

Additional non-critical Sentry/Snuba/Sentry edge containers were restarted to clear stale swapped pages after GitLab memory was reduced.

Customer-facing CyberVPN runtime on rented infrastructure was not changed.

## Final State

Final host memory:

```text
Mem: 46Gi total, 29Gi available
Swap: 31Gi total, 883Mi used
Prometheus swap-used metric: 933568512 bytes
```

GitLab container:

```text
cybervpn-gitlab: healthy
GitLab /users/sign_in: HTTP 200
Puma workers: 4
Puma threads: 2-4
```

Sentry edge:

```text
sentry-self-hosted-web-1: healthy
sentry-self-hosted-nginx-1: healthy
sentry-self-hosted-relay-1: running
```

Prometheus firing alerts after scrape:

```text
none
```

Repository/server evidence hygiene:

```text
git diff --check: pass
secret scan over new/updated evidence docs: no raw tokens/private keys/VLESS links found
npm audit --omit=dev --workspaces --audit-level=high: exits 0; remaining findings are moderate and pre-existing
```

## Decision

The two swap warning alerts are closed.

The home observability host can continue supporting Stage 1 monitoring and `STAGE1-RENT-14`.

## Follow-Up

Keep GitLab as a home non-critical service. If GitLab CI load increases, review:

- Puma workers;
- Sidekiq concurrency;
- GitLab container memory limit;
- runner concurrency;
- Sentry retention and consumer count.
