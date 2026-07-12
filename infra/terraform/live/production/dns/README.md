# production/dns

Runnable production DNS stack for Cloudflare A records backed by the production
edge state and explicit DNS-only A/AAAA records for VPN nodes outside that
state. Direct VPN transport records must remain DNS-only so clients reach the
node origin rather than Cloudflare's HTTP proxy.

Before first use:

1. Apply `../edge` and confirm the canary nodes are healthy.
2. Copy `backend.hcl.example` to `backend.hcl`.
3. Copy `terraform.tfvars.example` to `terraform.tfvars`.
4. Export `TF_VAR_cloudflare_api_token`.

Keep production DNS changes narrow while the canary window is still open.

When adopting an existing Cloudflare record, import it into this stack before
the first plan. A plan that proposes creating or replacing an already-live VPN
record is not safe to apply. The checked-in example includes the production
`de-3.cyber-vpn.org` A/AAAA pair; both records point to the same node and must
remain `proxied = false`.

For the existing DE3 pair, set `ZONE_ID` to the zone ID used by
`terraform.tfvars`, then import both live records before planning:

```bash
tofu -chdir=infra/terraform/live/production/dns import \
  -var-file=terraform.tfvars \
  'cloudflare_dns_record.this["de-3-vpn-ipv4"]' \
  "${ZONE_ID}/cd8f1c0984db4c3ce3171eca0c7396b1"
tofu -chdir=infra/terraform/live/production/dns import \
  -var-file=terraform.tfvars \
  'cloudflare_dns_record.this["de-3-vpn-ipv6"]' \
  "${ZONE_ID}/00a3ab1a6fd0de22b555d0a68ee48446"
```

Typical operator path:

```bash
tofu -chdir=infra/terraform/live/production/dns init -backend-config=backend.hcl
tofu -chdir=infra/terraform/live/production/dns plan \
  -var-file=terraform.tfvars \
  -out=dns.tfplan
tofu -chdir=infra/terraform/live/production/dns show -json dns.tfplan | jq -e '
  [
    .resource_changes[]
    | select(.mode == "managed")
    | {address, actions: .change.actions}
  ] as $managed
  | [
      $managed[]
      | select(
          .address == "cloudflare_dns_record.this[\"de-3-vpn-ipv4\"]"
          or .address == "cloudflare_dns_record.this[\"de-3-vpn-ipv6\"]"
        )
    ] as $vpn
  | ($vpn | length) == 2
    and all(
      $vpn[];
      (.actions | index("create") | not)
      and (.actions | index("delete") | not)
    )
    and all(
      $managed[];
      if (
        .address == "cloudflare_dns_record.this[\"de-3-vpn-ipv4\"]"
        or .address == "cloudflare_dns_record.this[\"de-3-vpn-ipv6\"]"
      )
      then true
      else .actions == ["no-op"]
      end
    )
'
tofu -chdir=infra/terraform/live/production/dns apply dns.tfplan
```

The `jq` gate must exit zero. It rejects missing state adoption, creation,
replacement, or deletion of either live DE3 record; an in-place DE3 metadata
update is permitted for review. Every other managed resource must be a no-op, so
the saved plan cannot carry an unrelated production DNS mutation.
