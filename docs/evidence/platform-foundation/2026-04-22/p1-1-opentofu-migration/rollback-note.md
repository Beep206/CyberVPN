# CyberVPN Platform Foundation P1.1 OpenTofu Rollback Note

**Date:** 2026-04-22  
**Status:** active during `P1.1`  
**Packet:** `P1.1`  
**Primary owners:** `infra-platform`  
**Supporting owners:** `sre-platform`  
**Purpose:** define the temporary break-glass path back to `Terraform` if a real remote-backend `tofu plan` produces unexpected divergence during the migration window.

---

## 1. When This Note Applies

Use this rollback note only if:

- a real remote-backend `tofu plan` diverges unexpectedly from the known-good baseline;
- the divergence cannot be explained immediately by an intended infrastructure change;
- `P1.1` has not yet been declared complete.

Do **not** use this note to bypass normal review for expected infrastructure changes.

---

## 2. Non-Negotiable Rules

1. Do not apply an unexplained `tofu plan`.
2. Do not change backend type, backend key, or stack split while troubleshooting.
3. Do not treat provider-registry namespace changes or lockfile differences as permission to accept resource drift.
4. Do not mix manual edits to state with engine rollback.
5. Preserve the exact same `backend.hcl`, `terraform.tfvars`, environment variables, and stack path when comparing engines.

---

## 3. First Response Steps

If a real `tofu plan` looks wrong:

1. stop before `apply`
2. record:
   - stack path
   - git commit SHA
   - `tofu version`
   - exact command used
   - plan timestamp
3. save the plan output or transcript in the evidence archive
4. classify whether the difference is:
   - lockfile-only / provider-install-only
   - backend/init-only
   - actual resource drift

Only actual unexplained resource drift triggers the rollback path below.

---

## 4. Break-Glass Rollback Path

The temporary rollback path is to run the same operator flow with `Terraform` explicitly supplied.

### 4.1 Make-Based Operator Rollback

Examples:

```bash
cd infra
TOFU=terraform make terraform-init-staging-foundation
TOFU=terraform make terraform-plan-staging-foundation
```

```bash
cd infra
TOFU=terraform make terraform-init-production-edge
TOFU=terraform make terraform-plan-production-edge
```

Reasoning:

- existing `terraform-*` targets remain in place during `P1.1`
- they now execute through `$(TOFU)`
- setting `TOFU=terraform` reuses the same command family without inventing a second operator surface

### 4.2 Inventory Bridge Rollback

If inventory generation must use Terraform temporarily:

```bash
cd infra/ansible
python scripts/generate_inventory.py \
  --terraform-bin terraform \
  --terraform-dir ../terraform/live/staging/edge \
  --output inventories/staging/generated.hosts.json \
  --environment staging
```

The canonical flags remain `--tofu-bin` and `--stack-dir`, but legacy aliases are intentionally preserved during the migration window.

---

## 5. Required Evidence On Rollback Use

Any use of this rollback note must capture:

- affected stack
- operator name
- approving reviewer
- reason for rollback
- `tofu` transcript
- `terraform` comparison transcript
- disposition:
  - revert to Terraform temporarily
  - fix OpenTofu-specific issue
  - prove drift is unrelated to engine and continue with OpenTofu

Rollback use without written evidence is not acceptable.

---

## 6. Owner Acknowledgement

Required acknowledgement before the first live remote-backend rollback use:

| Function | Required | Named owner | Status | Notes |
|---|---|---|---|---|
| infra-platform | yes | pending | pending | operational owner of stack cutover |
| sre-platform | yes | pending | pending | reviewer for plan divergence and rollback decision |

---

## 7. Expiry Rule

This rollback note is temporary.

It expires when:

- `P1.1` is declared complete, and
- live `tofu plan` evidence has been accepted for the in-scope stacks, and
- later `P1` packets begin relying on OpenTofu as the only approved default path.

At that point:

- legacy `--terraform-*` aliases may be retired in a later cleanup packet;
- Terraform stops being an approved routine comparison path.
