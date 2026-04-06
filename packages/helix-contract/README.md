# Helix Contract Package

Shared JSON Schemas, fixtures, and validation tooling for the CyberVPN Helix platform.

## Contracts

- `manifest`
- `node-assignment`
- `node-heartbeat`
- `client-capabilities`
- `transport-profile`
- `benchmark-report`
- `rollout-state`

## Validate

From the repository root:

```bash
node packages/helix-contract/scripts/validate-contracts.mjs
```

Or from this package:

```bash
npm run validate
```
