# CyberVPN scoped Node SSH broker contract

This overlay applies only to the Remnawave backend source pinned at commit
`f8ad8ad3410252215ca7b2e429d157bd275ec564` (release `3.4.3`). The patcher
fails before writing any file when one of the security-sensitive upstream
anchors has drifted.

The broker is disabled by default. It is a service-to-service capability for
the CyberVPN backend; it is not a Remnawave API token or panel admin JWT. In
this custom image it is the only browser-SSH authorization path: the native
Remnawave ticket controller and `/api/node-ssh/ws` route are disabled
server-side so a broad Remnawave ADMIN JWT cannot bypass CyberVPN's trusted
administrator allowlist, fresh MFA, one-time local ticket, and audit policy.

## Runtime configuration

```dotenv
CYBERVPN_NODE_SSH_BROKER_ENABLED=true
CYBERVPN_NODE_SSH_BROKER_SECRET=<64 random bytes as 128 lowercase hex characters>
CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES=<comma-separated exact IPs or narrow CIDRs>
```

Generate the secret through the deployment secret manager. The value must be
different from `APP_SECRET`, every Remnawave API token, every CyberVPN JWT
secret, and every other service credential. Remnawave refuses to start when
the broker is enabled without a correctly formatted secret or when it equals
`APP_SECRET`.

The reverse proxy must overwrite (not append or pass through) the
`x-remnawave-real-ip` header. The REST exchange and WebSocket connection must
resolve to the same canonical source IP. Network policy should permit the
broker REST and WebSocket paths only from the CyberVPN backend.

`CYBERVPN_NODE_SSH_BROKER_TRUSTED_PROXY_RANGES` is matched against the actual
TCP peer in `request.socket.remoteAddress` before Remnawave honors any
forwarded IP. Prefer the exact Caddy/reverse-proxy container IP; if a stable
address is unavailable, use the smallest dedicated proxy-network CIDR. CIDRs
must be at least IPv4 `/24` or IPv6 `/64`; exact `/32` and `/128` entries are
allowed. Unspecified, multicast/reserved, broad, empty, invalid, zero-prefix,
or more than 32 entries make the Remnawave API fail during startup. Loopback
is accepted only for an explicitly local proxy topology. A direct or lateral
caller cannot make a spoofed `x-remnawave-real-ip` authoritative by adding
`X-Forwarded-*` headers.

## REST ticket exchange

```http
POST /api/cybervpn/node-ssh/tickets/{node_uuid}
Content-Type: application/json
X-CyberVPN-Node-Ssh-Broker-Secret: <broker secret>

{"actorReference":"6ba7b810-9dad-41d1-80b4-00c04fd430c8"}
```

`node_uuid` and `actorReference` are UUIDs. `actorReference` is the trusted
CyberVPN administrator UUID already authorized by CyberVPN's MFA, session,
RBAC, object-grant, and audit boundary. Remnawave uses it only to bind and
identify the resulting SSH session; the reference does not become a
Remnawave administrator.

Successful response (`201`):

```json
{
  "response": {
    "ticket": "<43-character base64url opaque value>",
    "credential": "<different 43-character base64url opaque value>",
    "path": "/api/cybervpn/node-ssh/ws",
    "protocol": "rw-cybervpn",
    "expiresInSeconds": 10
  }
}
```

The ticket and credential are both required. They are bound to each other,
the selected node, the resolved source IP, and `actorReference`. Redis stores
neither opaque value: it stores a 10-second record under a domain-separated
HMAC index. Issuance is bounded to 60 authenticated requests per source IP per
60 seconds.

Expected failures:

| Status | Meaning |
| --- | --- |
| `400` | Invalid UUID or strict request body. |
| `401` | Missing or incorrect dedicated broker secret. |
| `404` | Broker disabled or authenticated request names an unknown node. |
| `429` | Authenticated source exceeded the bounded issue rate. |
| `503` | TCP peer is outside the trusted proxy allowlist, or a valid forwarded source IP could not be established. |

The response is sensitive server-side state. The CyberVPN backend must never
return `ticket`, `credential`, the broker secret, or the upstream WebSocket
subprotocol list to a browser. It should wrap them in its own encrypted,
one-time local ticket and proxy WebSocket frames server-side.

Reverse-proxy and telemetry configuration must redact both
`X-CyberVPN-Node-Ssh-Broker-Secret` and `Sec-WebSocket-Protocol`; neither header
may be written to access logs, traces, error reports, or support evidence.

## WebSocket redemption

Connect to:

```text
wss://<private-remnawave-host>/api/cybervpn/node-ssh/ws
```

Offer exactly these WebSocket subprotocol values in order:

```text
rw-cybervpn, <ticket>, <credential>
```

The server selects `rw-cybervpn`. Redemption uses an atomic Redis `GETDEL`.
The exact pair succeeds at most once. A valid pair presented from another
source IP is rejected and burned. Wrong credentials derive a different cache
key and cannot consume the valid pair. Missing, expired, replayed, corrupt, or
scope-mismatched material returns a generic WebSocket `401` without logging
the credential.

Before redemption, the WebSocket's TCP peer must also match the configured
trusted proxy ranges. Only then is the overwritten `x-remnawave-real-ip`
value compared with the source IP captured by the REST exchange.

The credential is accepted only by this custom WebSocket path. It is not a
JWT, has no signature or claims, and is not consulted by generic Remnawave
REST guards, native panel routes, tools endpoints, or the native Node SSH
path. It therefore grants no generic panel/API administrator access.

## Native denial and rollback

Native Remnawave browser SSH is intentionally unavailable in the custom
image. `NodeSshController` is not registered, `/api/node-ssh/ws` returns 404
before native credentials are parsed, and the WebSocket server never selects
the native `rw` subprotocol. The upstream verifier/parser remains in the
pinned source only as a fail-closed source-drift anchor; it is unreachable
from the registered controller and gateway paths. A native panel button, if
rendered by the pinned frontend, cannot obtain or redeem a native ticket.

The overlay does not add a scoped vault-OPRF endpoint. CyberVPN must own its
browser-key workflow and must not call the native ADMIN-only vault route with
an elevated JWT.

To disable browser SSH, set `CYBERVPN_NODE_SSH_BROKER_ENABLED=false` and stop
issuing CyberVPN-local SSH tickets. Existing upstream broker material expires
within 10 seconds. Restoring native Remnawave SSH requires an explicit image
rollback/rebuild and is not an operational broker toggle because that would
re-introduce the alternate ADMIN-JWT authorization path.
