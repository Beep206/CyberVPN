# CyberVPN Partner Platform: Phase 5 Service-Access Replay Pack

**Date:** 2026-04-18  
**Status:** canonical validation pack for `Phase 5 / T5.7`  
**Purpose:** define the deterministic replay artifact for service identities, entitlement grants, provisioning profiles, device credentials, access delivery channels, and cross-channel parity expectations.

---

## 1. Document Role

This pack exists to prove that service access can be reconstructed from canonical `Phase 5` objects without falling back to:

- raw `mobile_users` fields as the primary source of truth;
- storefront session assumptions;
- channel-specific provisioning shortcuts;
- undocumented support heuristics.

The pack is a machine-generated report built from a service-access snapshot containing:

- `service_identities`
- `entitlement_grants`
- `provisioning_profiles`
- `device_credentials`
- `access_delivery_channels`
- `channel_expectations`

The pack is deterministic. identical input snapshots with fixed `replay_generated_at` produce identical packs.

---

## 2. Output Sections

The report contains these top-level sections:

- `metadata`
- `input_summary`
- `service_identity_views`
- `channel_parity_views`
- `reconciliation`

`service_identity_views` are scope-level explainability rows for canonical service access.

`channel_parity_views` are expectation-driven checks showing whether a specific channel can resolve the same entitlement and provisioning truth without relying on purchase-surface state.

`reconciliation` contains machine-readable mismatch output suitable for evidence storage, shadow reviews, and `Phase 5` gate sign-off.

---

## 3. Service Identity View Definitions

Each `service_identity_views[]` entry must include:

- `service_identity_id`
- `service_key`
- `customer_account_id`
- `auth_realm_id`
- `provider_name`
- `provider_subject_ref`
- `duplicate_scope_count`
- `active_entitlement_grant_id`
- `active_entitlement_status`
- `active_plan_code`
- `entitlement_counts`
- `provisioning_profile_keys`
- `device_credentials`
- `access_delivery_channels`
- `bridge_provenance`

Important bridge fields:

- `bridge_provenance.legacy_provider_subject_present`
- `bridge_provenance.legacy_subscription_url_present`

These fields do not make legacy data canonical. They only prove that legacy provider references survived the bridge as provenance.

---

## 4. Channel Parity View Definitions

Each `channel_parity_views[]` entry must include:

- `parity_key`
- `customer_account_id`
- `auth_realm_id`
- `provider_name`
- `channel_type`
- `credential_type`
- `credential_subject_key`
- `resolved_provisioning_profile_key`
- `resolved_channel_subject_ref`
- `service_identity_id`
- `active_entitlement_grant_id`
- `selected_provisioning_profile_id`
- `selected_device_credential_id`
- `selected_access_delivery_channel_id`
- `mismatch_codes`

The expectation must be evaluated using the same resolution semantics as runtime service access:

1. profile key defaults to `<channel_type>-default` when absent;
2. channel subject defaults to explicit channel subject, then credential subject, then service-identity-derived subject;
3. device credentials are optional unless the expectation requires them;
4. access delivery channels remain separate from entitlement state.

This means channel parity evidence is explainable in the same terms support and platform teams already use in runtime diagnostics.

---

## 5. Canonical Mismatch Vocabulary

Blocking mismatches for `Phase 5` include:

- `service_identity_duplicate_customer_realm_provider`
- `entitlement_grant_missing_service_identity`
- `provisioning_profile_missing_service_identity`
- `device_credential_missing_service_identity`
- `device_credential_missing_provisioning_profile`
- `access_delivery_channel_missing_service_identity`
- `access_delivery_channel_missing_provisioning_profile`
- `access_delivery_channel_missing_device_credential`
- `access_delivery_channel_realm_mismatch`
- `provider_name_mismatch`
- `multiple_active_entitlement_grants_for_scope`

Warning-level channel parity mismatches include:

- `parity_missing_service_identity`
- `parity_missing_active_entitlement_grant`
- `parity_entitlement_status_mismatch`
- `parity_missing_provisioning_profile`
- `parity_missing_device_credential`
- `parity_missing_access_delivery_channel`
- `parity_channel_status_mismatch`
- `parity_delivery_payload_key_missing`

These codes are canonical and machine-readable. They are the approved mismatch vocabulary for `Phase 5` replay and parity evidence.

---

## 6. Expected Replay Behavior

The replay builder must:

1. validate that all service-access children reference existing canonical parents;
2. detect duplicate service-identity scopes;
3. detect multiple active entitlement grants for the same customer/realm/provider scope;
4. surface bridge provenance without treating legacy fields as live truth;
5. evaluate channel parity using deterministic profile and channel-subject defaults;
6. separate structural mismatches from channel expectation mismatches.

This pack is not a provisioning engine. It is a deterministic reporting and reconciliation artifact.

---

## 7. CLI Usage

Build the replay pack:

```bash
backend/.venv/bin/python backend/scripts/build_phase5_service_access_replay_pack.py \
  --input /path/to/phase5-service-access-snapshot.json \
  --output backend/docs/evidence/partner-platform/phase5-service-access-replay-pack.json
```

Print a compact summary:

```bash
backend/.venv/bin/python backend/scripts/print_phase5_service_access_replay_summary.py \
  --input backend/docs/evidence/partner-platform/phase5-service-access-replay-pack.json
```

---

## 8. Gate Usage

This pack is required input for:

- `T5.8` Phase 5 exit evidence;
- channel-parity shadow review before non-web rollout;
- support sign-off that purchase context and service-consumption context remain separately explainable.

If the pack status is `red`, `Phase 5` is not ready for parity sign-off.
