# CyberVPN systemd units

## DE Reality ingress relay

`cybervpn-de-relay-reality.*` and `cybervpn-de-relay-xhttp.*` expose bounded
TCP listeners on the NL node and transparently proxy them to the DE node:

- `0.0.0.0:2053` -> `138.124.115.206:443`;
- `0.0.0.0:2083` -> `138.124.115.206:8443`.

The relay is used by `de-relay.cyber-vpn.org` when a client network truncates
large REALITY ClientHello records on the direct path to the DE provider. TLS,
REALITY, and VLESS terminate only on the DE node, so the VPN exit remains DE.

Install on the NL node and allow only the two relay ports:

```bash
install -m 0644 infra/systemd/cybervpn-de-relay-{reality,xhttp}.{socket,service} \
  /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now cybervpn-de-relay-reality.socket cybervpn-de-relay-xhttp.socket
ufw allow 2053/tcp comment 'CyberVPN DE Reality relay'
ufw allow 2083/tcp comment 'CyberVPN DE XHTTP relay'
```

Rollback by restoring the DE Remnawave hosts to `de-3.cyber-vpn.org` on ports
`443` and `8443`, then disabling both sockets and removing the relay DNS record.

## `cybervpn-remnawave-ru-msk-node-proxy.service`

Production-only compatibility unit for the RU Moscow Remnawave node API.

During the Premium Smart RU rollout on 2026-06-28, the control plane host could
complete a TCP handshake to `178.159.94.225:22230`, but application payloads did
not pass over that IPv4 path. The same node API was reachable over the server
IPv6 address. Remnawave currently runs inside an IPv4-only Docker network on the
control plane, so the control plane exposes a local IPv4 listener:

- bind: `172.30.3.1:32230`
- upstream: `[2a12:5940:e38b::2]:22230`

The unit is intentionally narrow:

- no provider credentials or Remnawave secrets are stored in the unit;
- access must stay firewalled to the backend Docker subnet;
- Remnawave API authentication still uses the per-node `SECRET_KEY`;
- remove the proxy when the provider IPv4 path or Remnawave container IPv6 is
  fixed and the node can be addressed directly again.

Install/update on the control plane:

```bash
install -m 0644 infra/systemd/cybervpn-remnawave-ru-msk-node-proxy.service \
  /etc/systemd/system/cybervpn-remnawave-ru-msk-node-proxy.service
systemctl daemon-reload
systemctl enable --now cybervpn-remnawave-ru-msk-node-proxy.service
ufw allow from 172.30.3.0/24 to 172.30.3.1 port 32230 proto tcp
```
