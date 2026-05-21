# Stage 1 Stabilization Snapshot - 2026-05-20

Detailed evidence:

- `docs/evidence/releases/stage1-rented-prod-11-observability-stabilization-20260520T162926Z.md`
- `docs/evidence/releases/stage1-rented-prod-11a-external-probe-relay-20260520T164632Z.md`
- `docs/evidence/releases/stage1-rented-prod-11b-node-only-and-direct-home-prod-app-20260520T170051Z.md`
- `docs/evidence/releases/stage1-rented-prod-11c-direct-home-prod-app-network-path-20260520T172432Z.md`
- `docs/evidence/releases/stage1-rented-prod-11d-cloudflare-user-path-probes-20260520T175619Z.md`
- `docs/evidence/releases/stage1-rented-prod-12-catalog-support-beta-gate-20260520T180458Z.md`
- `docs/evidence/releases/stage1-rented-prod-13-first-controlled-cohort-trial-watch-20260520T184156Z.md`
- `docs/evidence/releases/stage1-home-observability-swap-tuning-20260520T191045Z.md`
- `docs/evidence/releases/stage1-rented-prod-14-owner-device-cohort2-preflight-20260520T191226Z.md`
- `docs/evidence/releases/stage1-rented-prod-14a-owner-device-confirmation-cohort2-list-20260521T061114Z.md`
- `docs/evidence/releases/stage1-rented-prod-14b-owner-real-device-retest-cohort2-invite-20260521T062040Z.md`
- `docs/evidence/releases/stage1-rented-prod-14c-miniapp-session-restore-20260521T065247Z.md`
- `docs/evidence/releases/stage1-rented-prod-15-cohort2-invite-execution-20260521T115722Z.md`

Result: `CONTINUE_CONTROLLED_INTERNAL_BETA_TRIAL_ONLY_COHORT2_LIST_PENDING`

## Summary

The rented Stage 1 runtime is up, the production VPN node is reachable on required TCP ports, Alertmanager delivery to Telegram/email is proven, and Sentry/Loki/Grafana/Prometheus are running on the home observability host.

`STAGE1-RENT-11B` restored the node-only policy: the temporary external probe relay was removed from `prod-vpn-node-1`, and the VPN node must not run public app/API/admin monitoring workloads.

The direct home-server public HTTP/TLS probing path to `prod-app-1` remains blocked at the network path level: TCP handshake and ICMP work, but TCP payload after handshake does not reach `prod-app-1`. This is now tracked as a direct-path infrastructure blocker instead of being hidden by a node relay.

`STAGE1-RENT-11C` now has RouterOS SSH evidence. MikroTik routes `45.87.41.146` directly through WAN, FastTrack/FastPath are inactive for the test, and WAN sniffer shows the post-handshake TLS payload being transmitted from `95.82.233.131` to `45.87.41.146:443`. `prod-app-1` tcpdump sees only SYN/SYN-ACK/ACK and does not receive the payload. The current blocker is upstream/provider-path handling after MikroTik TX, most likely the home ISP path or JustHost/provider anti-DDoS/TCP validation for the home public IP on `80/443`.

`STAGE1-RENT-11D` closes the active public endpoint monitoring authority by switching the S1 `.net` public hostnames to Cloudflare-proxied DNS and proving home Prometheus blackbox probes through the user-facing Cloudflare path. All `blackbox-stage1-public-web` targets now report `probe_success=1` and HTTP `200`, and no active `Stage1PublicEndpointProbeFailed` alert was returned after the user-path probes went green.

`STAGE1-RENT-12` seeds the production S1 catalog and minimum support/storefront/merchant records. The public API now returns 16 active public plan entries for each active channel: `web`, `miniapp` and `telegram_bot`. Support, communication, invoice, merchant, billing descriptor and storefront records are present and active. Stage 1 firing alerts are `0`, public user-path probes remain green, and VPN node TCP probes for `de-1.cyber-vpn.org:443` and `:8443` remain green.

`STAGE1-RENT-13` ran the first owner/internal controlled beta trial proof. Two launch blockers were found and hotfixed before cohort expansion: Mini App/Telegram trial activation now passes the Remnawave provisioning gateway, and Telegram Bot/Mini App config delivery now prefers the local `mobile_users.remnawave_uuid` bridge before falling back to Telegram-ID lookup or stored subscription URL. The owner/internal Telegram-linked user has an active trial, Remnawave link and subscription URL, protected config delivery returns `200` with VLESS config present, and an ephemeral Xray client on `prod-app-1` successfully connected through `de-1.cyber-vpn.org`.

The home observability swap warnings were closed by tuning home GitLab for the ops role: Puma workers were reduced, Sidekiq concurrency was reduced, GitLab nginx worker count was reduced, bundled GitLab Prometheus was disabled, and stale swapped pages were cleared through controlled restarts of GitLab and selected non-critical Sentry services. Final swap used is below the alert threshold and firing alerts are empty after scrape.

`STAGE1-RENT-14` preflight is complete. Rented production containers are healthy, public probes are `200`, owner/internal trial is active, protected Telegram Bot config delivery returns `200` with VLESS config present, Stage 1-specific firing alert count is `0`, and all public endpoint/VPN-node probes are green. RENT-14 remains pending owner device validation before adding cohort-2 users.

`STAGE1-RENT-14A` found one remaining server-side Mini App blocker before cohort-2 expansion: bootstrap usage lookup still fell back to Remnawave Telegram-ID lookup for the owner user. The backend was hotfixed to prefer `mobile_users.remnawave_uuid`, deployed as `cybervpn/cybervpn-backend:stage1-rent14a-miniapp-bootstrap-uuid-20260521t060453z`, and retested with production Mini App auth/bootstrap/config smoke. The smoke returned auth `200`, bootstrap `200`, config `200`, `config_source=remnawave_generated`, subscription URL present and no repeated Remnawave response validation warning.

`STAGE1-RENT-14B` closed owner real-device validation. The owner confirmed receiving the config through the Telegram Bot/Mini App flow, importing it into a VPN client, connecting successfully and seeing public exit IP `77.90.13.29` in Germany. Runtime containers remain healthy, public endpoint probes are green, VPN-node TCP probes for `de-1.cyber-vpn.org:443` and `:8443` are green, and firing alerts are empty. Cohort-2 remains pending only on the approved 1-3 user list and support-watch execution.

`STAGE1-RENT-14C` fixed a Mini App stale-session restore issue found after the owner real-device connect proof. Production backend state still showed an active trial, Remnawave UUID and subscription URL, but the Mini App could render a misleading no-subscription state after protected Mini App API requests returned `401`. The frontend now dispatches a Mini App auth-restore event on unrecovered `401`, re-runs Telegram Mini App auth from Telegram `initData`, invalidates Mini App query keys and shows a session-restore state instead of the no-subscription fallback while auth is recovering. The hotfix was deployed only to `cybervpn-frontend:stage1-rent14c-miniapp-session-restore-20260521t063728z`; production build, targeted tests, lint and public Mini App HTTP 200 proof passed. Cohort-2 expansion remains blocked until owner confirms the real-device Mini App retest after this hotfix.

`STAGE1-RENT-15` has started. Three owner-held controlled beta invite codes were issued for the owner Telegram-linked account with 7 free days each and a 72-hour expiry window ending on 2026-05-24 11:54:13 UTC. Raw codes are not stored in evidence. Production containers are healthy, public endpoint probes are green, VPN-node TCP probes are green, home Prometheus reports firing alerts `0`, and no recent sampled backend/bot/worker/scheduler errors were found. Public referral/growth launch remains disabled. The next required evidence is the first invited user onboarding attempt and support-watch result.

## Daily Decision

```text
CONTINUE owner/internal controlled beta and begin cohort-2 support-watch with no more than 1-3 selected users.
GO for Stage 1 public endpoint user-path monitoring through Cloudflare-proxied hostnames.
GO for visible S1 public catalog, owner/internal trial config delivery and very small controlled trial-only cohort expansion.
NO-GO for expanding beyond the issued 3-code owner-held pack until first invited user evidence is recorded.
NO-GO for paid users until real payment -> provisioning evidence exists.
NO-GO for global public registration; use manual/invite-controlled onboarding.
```
