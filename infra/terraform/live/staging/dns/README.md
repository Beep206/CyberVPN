# staging/dns

This stack manages staging DNS records in Cloudflare.

Keep it intentionally thin:

- one zone per stack;
- one record map in variables;
- no large module abstraction for basic DNS records.

For the Cloudflare v5 provider, prefer full record names (FQDN) or `@` for the zone apex.
This stack reads the staging edge node IPs from the `staging/edge` remote state.
