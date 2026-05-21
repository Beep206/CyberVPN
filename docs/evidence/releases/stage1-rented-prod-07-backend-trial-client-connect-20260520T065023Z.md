# STAGE1-RENT-07 Backend Trial Flow And Client Connect Proof

Date: `2026-05-20T06:50:23Z`

Stage: `S1 - Controlled Public Beta`

Scope: prove the rented production app/control-plane can create S1 trial VPN access, deliver a subscription URL through the CyberVPN backend/Mini App contract, generate real Remnawave client links and connect through the rented production VPN node.

Owner: `@Sasha_Beep`

## Summary

`STAGE1-RENT-07` is closed for the current rented production beta stack.

Result:

- the temporary Stalwart mail side-track was rolled back before this proof;
- CyberVPN backend was hotfixed so Remnawave usernames stay within the upstream 36-character limit;
- Remnawave default S1 internal squad was set to `S1_DEFAULT_DE`;
- Remnawave Hosts were created for `de-1.cyber-vpn.org`;
- CyberVPN edge now proxies Remnawave subscription fetches on `/api/sub*`;
- a disposable authenticated user activated trial through the backend API;
- the user was provisioned into Remnawave;
- Mini App config returned a subscription delivery response;
- the subscription endpoint returned real VLESS Reality links, not placeholder `0.0.0.0:1` links;
- an Xray client container connected through the generated TCP Reality link;
- proxied egress matched the production VPN node IP;
- disposable Remnawave and mobile users were deleted after proof;
- trial provisioning was restored to disabled state after proof.

No raw subscription URL, VLESS UUID, Reality public key, short ID, JWT, Remnawave token or generated client config is stored in this document.

## Stalwart Rollback

The Stalwart mail runtime was removed before continuing this stage.

Evidence file:

```text
docs/evidence/releases/stage1-rented-prod-mail-rollback-20260520T060600Z.md
```

Decision:

```text
Do not self-host mail during the immediate Stage 1 runtime path.
Use Resend later after core app/VPN/payment runtime is stable.
```

## Production Runtime Changes

### Backend Username Hotfix

Remnawave rejected trial user creation because the previous generated username exceeded the upstream maximum:

```text
Username must be less than 36 characters
```

CyberVPN username generation was shortened while keeping deterministic non-PII names:

| Flow | Runtime username format |
|---|---|
| Trial | `cvpn_t_<first_28_customer_uuid_hex>` |
| Paid provisioning | `cvpn_p_<first_28_customer_uuid_hex>` |
| Manual admin grant | `cvpn_m_<first_28_customer_uuid_hex>` |

Targeted tests:

```text
32 passed in 0.24s
```

The run without coverage was used because the targeted suite passed and the full repository coverage threshold is unrelated to this hotfix.

Production hotfix image:

```text
cybervpn/cybervpn-backend:stage1-rent07-usernamefix-20260520t062659z
```

Compose tag retained for runtime compatibility:

```text
cybervpn/cybervpn-backend:stage1-rent04-90f5b4b5
```

### Remnawave Hosts

Official Remnawave host model reference used:

```text
https://docs.rs/remnawave/latest/remnawave/api/types/hosts/struct.CreateHostRequestDto.html
https://docs.rs/remnawave/latest/src/remnawave/api/types/hosts.rs.html
```

Created visible Remnawave Hosts:

| Host tag | Address | Port | Network | Security | Node binding |
|---|---|---:|---|---|---|
| `S1_DE_REALITY_443` | `de-1.cyber-vpn.org` | `443` | `tcp` | `reality` | `s1-de-1` |
| `S1_DE_XHTTP_REALITY_8443` | `de-1.cyber-vpn.org` | `8443` | `xhttp` | `reality` | `s1-de-1` |

Why this was required:

```text
Before Hosts existed, Remnawave subscription output contained placeholder links:
host=0.0.0.0
port=1
security=none
```

After Hosts were created, subscription output contained real `de-1.cyber-vpn.org` links.

### Subscription Edge Route

The API edge was updated so Remnawave subscription fetches can pass through `api.cyber-vpn.net`:

```text
api.cyber-vpn.net /api/sub* -> internal Remnawave control-plane
```

This route is intentionally narrow and only covers the subscription fetch path. The Remnawave management API remains private/internal.

Edge compose was also updated to attach Caddy to the app backend network persistently, so the route survives Caddy container recreation.

## Trial Flow Proof

Server evidence directory:

```text
/srv/cybervpn/evidence/rent07-trial-client-connect-20260520T065023Z
```

Redacted proof:

```json
{
  "trial_activate": {
    "http_code": 200,
    "activated": true,
    "trial_end_present": true,
    "duration_ms": 322
  },
  "miniapp_config": {
    "http_code": 200,
    "is_found": true,
    "client_type": "subscription",
    "source": "legacy_subscription_url",
    "link_count": 1,
    "duration_ms": 17
  },
  "db": {
    "trial_activated_at_present": true,
    "trial_expires_at_present": true,
    "remnawave_uuid_present": true,
    "subscription_url_present": true,
    "subscription_url_host": "api.cyber-vpn.net"
  },
  "remnawave_user": {
    "found": true,
    "status": "active",
    "expires_at_present": true,
    "subscription_url_present": true
  },
  "subscription_fetch": {
    "http_code": 200,
    "size": 744,
    "decoded_payload_present": true,
    "contains_vless": true,
    "vless_link_count": 2
  }
}
```

Generated link metadata, redacted:

| Host | Port | Network | Security | Required client fields present |
|---|---:|---|---|---|
| `de-1.cyber-vpn.org` | `443` | `tcp` | `reality` | flow, SNI, public key, short ID, fingerprint |
| `de-1.cyber-vpn.org` | `8443` | `xhttp` | `reality` | SNI, public key, short ID, path, fingerprint |

## Client Connect Proof

An ephemeral Xray client container was started on `prod-app-1` using the generated TCP Reality link.

The raw client config was stored only as a temporary `.secret.json` file on the server and was deleted after the proof.

Redacted result:

```json
{
  "xray_client_container_running": true,
  "direct_ip_present": true,
  "proxy_ip_present": true,
  "proxy_egress_matches_node": true,
  "direct_and_proxy_differ": true,
  "node_ip_expected": "77.90.13.29",
  "result": "success"
}
```

Interpretation:

```text
Direct egress from prod-app-1 differed from proxied egress.
Proxied egress matched the production VPN node IPv4.
Therefore the generated subscription link produced a working VPN client connection.
```

## Cleanup And Restored State

Disposable proof data was removed:

```json
{
  "remnawave_user_deleted": true,
  "mobile_user_deleted": true
}
```

Runtime gate restored:

```text
STAGE1_TRIAL_PROVISIONING_ENABLED=false
```

Backend health after restore:

```json
{"status":"ok"}
```

No `.secret.json` files remain in the server evidence directory.

## Acceptance Result

`STAGE1-RENT-07` acceptance is met:

- backend trial API works against the rented production runtime;
- Remnawave provisioning works;
- subscription URL delivery works;
- subscription endpoint returns real usable VLESS links;
- the generated TCP Reality link connects through the production VPN node;
- cleanup and disabled-state restore are complete.

## Residual Notes

This proof does not enable public trial provisioning permanently. Public beta enablement still requires the controlled launch gate and owner go/no-go.

Recommended next stage:

```text
STAGE1-RENT-08: Controlled Runtime Enablement And Beta Cohort Start
```
