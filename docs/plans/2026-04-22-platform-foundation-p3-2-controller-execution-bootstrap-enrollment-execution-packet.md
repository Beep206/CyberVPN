# CyberVPN Platform Foundation P3.2 Controller Executor, Bootstrap, And Enrollment Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live integration evidence pending  
**Packet:** `P3.2`  
**Primary owners:** `fleet-platform` / `infra-platform`  
**Supporting owners:** `backend-platform`, `security`, `transport-backend`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.2` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md](2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md)
- [../api/node-fleet-controller-domain-model.md](../api/node-fleet-controller-domain-model.md)
- [../runbooks/platform-foundation-node-lifecycle-state-machine.md](../runbooks/platform-foundation-node-lifecycle-state-machine.md)
- [../security/platform-foundation-openbao-and-pki-registry.md](../security/platform-foundation-openbao-and-pki-registry.md)

`P3.2` exists to turn the controller from a generic request API into a real fleet-control
service foundation that understands:

- OpenTofu execution safety
- OpenBao bootstrap issuance
- first enrollment handoff
- renewable node identity rotation

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because no live OpenTofu
  runners, no live OpenBao auth material, and no live external node enrollment target exist in
  the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is live executor wiring, live OpenBao issuance and unwrap proof,
  live enrollment proof, and certificate rotation evidence.

---

## 2. Canonical Decisions For P3.2

`P3.2` fixes the following decisions:

1. The controller now owns durable records for:
   - `Node`
   - `BootstrapToken`
   - `NodeCertificate`
   - `OperationStep`
2. OpenTofu executor behavior enters the service first as an auditable preview-safe adapter,
   not as uncontrolled shell execution from an HTTP handler.
3. State locking, workspace isolation, policy-check requirement, plan artifact recording, and
   variable redaction are mandatory executor invariants.
4. OpenBao bootstrap is represented through:
   - `auth/approle-bootstrap`
   - `bootstrap-fleet-node-enrollment`
   - response wrapping TTL
5. Enrollment completion consumes a bootstrap token and moves the node to certificate-backed
   identity.
6. Node identity rotation is an explicit controller flow, not an implicit side effect.

---

## 3. Scope

In scope for `P3.2`:

- extend `services/node-fleet-controller/` with:
  - durable node, bootstrap-token, certificate, and operation-step models
  - OpenTofu executor preview layer
  - OpenBao bootstrap manager
  - bootstrap issuance service
  - enrollment completion service
  - node identity rotation service
  - API routes for:
    - node creation and inspection
    - executor preview
    - bootstrap issuance
    - enrollment completion
    - identity rotation
- add unit and API tests for the new foundation slice;
- update packet evidence and program records.

Out of scope for this repository slice:

- live `tofu plan/apply/destroy`
- live OpenBao login or unwrap
- live cert-auth login from real nodes
- live runtime-adapter readiness
- live synthetic verification

---

## 4. Official Constraints

The execution of `P3.2` follows current primary-source guidance:

- OpenTofu state locking is mandatory for state-writing operations and failed locking must stop
  execution;
- OpenBao response wrapping is the required bootstrap delivery posture for short-lived machine
  handoff;
- OpenBao `AppRole` is the machine-oriented bootstrap auth path and should use wrapped
  `SecretID` delivery in pull mode where practical;
- OpenBao `cert` auth is the steady-state certificate-based identity posture for fleet nodes.

Primary sources:

- OpenTofu state locking: https://opentofu.org/docs/language/state/locking/
- OpenBao response wrapping: https://openbao.org/docs/2.3.x/concepts/response-wrapping/
- OpenBao AppRole auth: https://openbao.org/docs/auth/approle/
- OpenBao cert auth: https://openbao.org/docs/auth/cert/

---

## 5. Resulting Repository Touchpoints

- `services/node-fleet-controller/src/infra/execution/opentofu_executor.py`
- `services/node-fleet-controller/src/infra/secrets/openbao_manager.py`
- `services/node-fleet-controller/src/application/services/executor_service.py`
- `services/node-fleet-controller/src/application/services/bootstrap_service.py`
- `services/node-fleet-controller/src/application/services/enrollment_service.py`
- `services/node-fleet-controller/src/application/services/identity_service.py`
- `services/node-fleet-controller/src/api/router.py`
- `services/node-fleet-controller/tests/test_executor_preview.py`
- `services/node-fleet-controller/tests/test_p3_2_services.py`
- [../evidence/platform-foundation/2026-04-22/p3-2-controller-execution-bootstrap-enrollment/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p3-2-controller-execution-bootstrap-enrollment/evidence-pack.md)

