# Control-plane release promotion

This runbook prepares a digest-pinned release artifact for staging or production.
It does not authorize or perform a production rollout.

## Fixed trust policy

All seven release images must be built by the default-branch `Control Plane Images`
workflow in `Beep206/CyberVPN`:

- custom Remnawave panel/backend/frontend;
- CyberVPN backend;
- task-worker;
- Helix adapter;
- Remnawave node mirror;
- subscription-page mirror;
- CyberVPN-scoped node SSH proxy mirror.

Each component is bound to its exact repository under
`ghcr.io/beep206/cybervpn/`: `remnawave-backend`, `backend`, `task-worker`,
`helix-adapter`, `remnawave-node`, `remnawave-subscription-page`, and
`node-ssh-proxy`
respectively. Swapping two component refs, using another repository, or reusing
one digest for two components fails before any attestation or remote-state step.

For every digest, the repository requires GitHub-signed SLSA provenance, a
schema-valid SPDX-2.3 SBOM attestation, and a CyberVPN vulnerability-scan
attestation containing the exact Critical/High counts and SHA-256 of the raw
report. A clean scan uses `result=pass`. A nonzero scan uses `result=findings`
and is non-blocking only when a protected-branch decision under
`infra/ansible/policies/control-plane-accepted-risks/` matches every finding
component's image digest, scanner, counts and report hash. The decision is also
bound to the fixed signer workflow, source commit and
`cybervpn-control-plane-supply-chain/v2` policy. The trusted repository, signer
workflow, and `refs/heads/main` source ref are fixed in
`infra/ansible/scripts/verify_control_plane_attestations.py`; inventory variables
cannot override them.

There is no equivalent local signing pipeline. A local build may be used for
development, but it cannot be promoted by the reviewed release path.

## Build and promotion artifact

1. Run `.github/workflows/control-plane-images.yml` for the exact 40-character
   source commit on `main`.
2. Record all seven OCI refs in `registry/path@sha256:<64-hex>` form and the workflow
   run URL.
3. If any signed scan reports findings, add and review one decision conforming
   to `infra/ansible/policies/control-plane-accepted-risk.schema.json`, then pass
   its protected-branch path as `accepted_risk_decision_path`. Do not copy a
   decision across digests or changed reports. A clean release must not provide
   a stale decision.
4. Run `.github/workflows/control-plane-promote.yml`. For production, keep the
   GitHub Environment approval in place and obtain explicit production rollout
   authorization separately.
5. Download the generated `control-plane-release-<environment>` artifact. The
   workflow is read-only: it does not push a branch or modify an inventory.
6. Review the artifact's `release.yml`, `supply-chain-evidence.json`, saved
   verification outputs before copying the release manifest into the target
   inventory.

Raw Trivy reports and SPDX documents remain attached to the image-build run for
90 days. Promotion retains the signed verification outputs, exact counts,
report hashes and normalized decision for 90 days. The previously recorded
local Docker Scout findings remain owner-accepted diagnostics, but local output
cannot substitute for these registry-backed signed facts.

The evidence JSON is audit metadata, not the deployment trust boundary. Forging
its `verified` fields cannot authorize an image.

## Deployment-controller prerequisite

The Ansible controller must have:

- Python 3;
- GitHub CLI (`gh`) authenticated to read the private GHCR artifacts and their
  attestations;
- network access to GitHub and GHCR;
- registry credentials for the target hosts where private pulls are required.

Immediately before the role creates or changes remote state, Ansible runs the
fixed verifier against all 21 component/predicate combinations. Missing `gh`,
authentication failure, an untrusted signer/source, absent or malformed
provenance/SBOM/scan attestation, an unapproved or mismatched High/Critical
finding, a stale decision, or a digest mismatch stops the rollout before remote
mutation. Approved findings retain their exact counts and report hash in the
release manifest rather than being rewritten as a clean scan.

The local `make control-plane-release-{staging,production}` helpers perform the
same cryptographic verification before rendering a manifest; they are not an
offline bypass.

## Secrets and inventory

Start from `infra/ansible/examples/control-plane-vault-source.yml.example` and
render an encrypted environment vault. Never store plaintext production values
in the repository. If GHCR pulls are private, populate the registry username and
token in the vault.

The release manifest paths are:

- `infra/ansible/inventories/staging/group_vars/control_plane_staging/release.yml`;
- `infra/ansible/inventories/production/group_vars/control_plane_production/release.yml`.

Before staging rollout, confirm the read-only baseline guard, backup location,
pre-upgrade `APP_SECRET` fingerprint, numeric-ID reconciliation report, and exact
rollback digests. Production uses a separately reviewed copy of staging evidence;
it is never inferred from available credentials.

## Staging rollout

From `infra/`:

```bash
make ansible-control-plane-backup-staging
make ansible-control-plane-rollout-staging
make ansible-control-plane-verify-staging
```

Keep the native panel bound to loopback/private ingress. Browser SSH remains
disabled until its dedicated private proxy, trusted-admin/node allowlists,
passkey step-up, one-time ticket path, and audit tests all pass in staging.

## Production boundary

Do not run the production target without explicit authorization for the precise
release and window. When authorized, follow the panel-first, node-canary order in
the Remnawave production runbook and obey its stop conditions. Record:

- source commit, build and promotion run URLs;
- all seven digests and the immutable `release.yml` hash;
- attestation-verifier output;
- backup/restore evidence and rollback digests;
- rollout/health output and timestamps;
- the operator and approval record.
