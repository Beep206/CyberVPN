# CyberVPN Task2 SPB DE Exceptions systemd units

These units support the repository-side Task2 foundation for
`premium_spb_de_exceptions`. This systemd support does not implement the VPN bridge traffic path itself.
The bridge is an Xray/Remnawave Shadowsocks AEAD inbound on DE with tag
`DE_SPB_EXCEPTIONS_BRIDGE_9444`; SPB routes matched exception traffic to
outbound tag `DE_EXCEPTIONS_BRIDGE`.

## Units

- `cybervpn-spb-de-exceptions-port-preflight.service` is a deploy-only manual
  one-shot check before first bridge activation. It has no `[Install]` section,
  must not be enabled, and is not ordered into boot or Remnanode restart
  transactions. It fails if any TCP or UDP listener already owns port `9444`;
  after the intended Remnanode/Xray bridge listener is active, that failure is
  expected and must not block ordinary service restarts.
- `cybervpn-spb-de-exceptions-firewall.service` loads the nftables rules
  rendered by the `spb_de_exceptions_bridge` Ansible role. It runs before
  `remnanode.service` so the peer-only firewall is present before Xray starts
  accepting bridge traffic.

## Install

Install on the DE node only after a dry-run operator plan and a reviewed
Ansible check-mode run:

```bash
install -m 0644 infra/systemd/cybervpn-spb-de-exceptions-*.service /etc/systemd/system/
systemctl daemon-reload
systemctl start cybervpn-spb-de-exceptions-port-preflight.service
systemctl enable --now cybervpn-spb-de-exceptions-firewall.service
```

Do not run `systemctl enable cybervpn-spb-de-exceptions-port-preflight.service`.
The preflight unit is intentionally deploy-only rather than idempotent after
activation; once Xray legitimately owns `9444`, rerunning the preflight will
fail by design.

## Firewall Contract

The firewall file must be rendered at:

```text
/etc/nftables.d/cybervpn-spb-de-exceptions-bridge.nft
```

It must allow TCP and UDP `9444` only from the dedicated SPB peer address
`2a01:e5c0:1368::3/128`. The DE listener is pinned to
`2a0b:4140:ba84::2`; the broken SPB-to-DE IPv4 data path is not an allowed
fallback. The ruleset must drop every other TCP and UDP source and must not
contain `0.0.0.0/0` or `::/0` allow rules for the bridge port.

## Restart Ordering

Apply order:

1. Validate artifact manifest and rules.
2. Prove port `9444` is free.
3. Load peer-only firewall on DE.
4. Create/update the DE bridge profile, bridge squad, and bridge service user.
5. Restart/reload DE first.
6. Create/update the SPB customer profile with `DE_EXCEPTIONS_BRIDGE`.
7. Restart/reload SPB.

Rollback order:

1. Move SPB customer profile/node assignment back to the previous state.
2. Restart/reload SPB so matched traffic can no longer point at the Task2
   bridge.
3. Restore or remove the DE bridge profile/squad/user/firewall state recorded
   in the rollback manifest.
4. Restart/reload DE.

No credentials, Remnawave tokens, bridge passwords, VLESS UUIDs, subscription
URLs, or customer data belong in these unit files or their logs.
