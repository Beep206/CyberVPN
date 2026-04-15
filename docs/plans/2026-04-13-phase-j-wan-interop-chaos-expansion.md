# Phase J WAN Interop And Chaos Expansion Implementation Plan

## Outcome

As of `2026-04-13`, this plan is complete:

- `udp_wan_staging_interop` is `ready`
- `udp_net_chaos_campaign` is `ready`
- `udp_phase_j_signoff` reports `phase_j_state = "honestly_complete"`
- `Phase J` is therefore closed and `Phase K` becomes the next main track

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add repeatable WAN-like datagram evidence and explicit net-chaos coverage, then project that evidence into release-facing operator summaries without widening protocol semantics.

**Architecture:** Keep the existing deterministic `udp_interop_lab` profile catalog and release-shaped verdict chain as the contract anchor. Add two new evidence surfaces in `ns-testkit`: one staging/WAN-backed datagram lane and one explicit net-chaos campaign lane. Feed their machine-readable summaries into the current release-candidate consumers so operators can distinguish deterministic lab evidence from broader deployment evidence and retain enough artifacts for diagnosis.

**Tech Stack:** Rust workspace (`ns-testkit`, `ns-carrier-h3`), Bash/PowerShell wrappers, existing staging/edge runbooks, Docker or namespace-based impairment tooling, machine-readable JSON summaries under `target/verta/`.

---

### Task 1: Freeze The Phase J Summary Contracts

**Files:**
- Modify: `packages/verta-protocol/crates/ns-testkit/src/lib.rs`
- Create: `packages/verta-protocol/crates/ns-testkit/examples/udp_wan_staging_interop.rs`
- Test: `packages/verta-protocol/crates/ns-testkit/examples/udp_wan_staging_interop.rs`
- Modify: `packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md`

**Step 1: Write the failing tests**

- Add example-local tests that assert:
  - missing required WAN env fails closed
  - summary schema records `evidence_lane = "wan_staging"`
  - summary distinguishes deterministic-lab source vs broader deployment source
  - fallback and degradation facts are present even when the run fails

**Step 2: Run test to verify it fails**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
cargo test -p ns-testkit --example udp_wan_staging_interop -- --nocapture
```

Expected: FAIL because the example and summary contract do not exist yet.

**Step 3: Write minimal implementation**

- Introduce a new example that:
  - validates required env/config for a staging-backed UDP run
  - records deployment label, role permutation, profile set, and artifact paths
  - emits a fail-closed JSON summary under `target/verta/udp-wan-staging-interop-summary.json`
- Extend shared `ns-testkit` helpers only where needed for stable schema constants and summary labels.

**Step 4: Run test to verify it passes**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
cargo test -p ns-testkit --example udp_wan_staging_interop -- --nocapture
```

Expected: PASS with a machine-readable summary contract and explicit fail-closed behavior.

**Step 5: Commit**

```bash
git add packages/verta-protocol/crates/ns-testkit/src/lib.rs \
  packages/verta-protocol/crates/ns-testkit/examples/udp_wan_staging_interop.rs \
  packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md
git commit -m "feat: add phase j wan staging interop lane"
```

### Task 2: Add Operator-Facing WAN Wrappers And Checklist

**Files:**
- Create: `packages/verta-protocol/scripts/udp-wan-staging-interop.sh`
- Create: `packages/verta-protocol/scripts/udp-wan-staging-interop.ps1`
- Create: `docs/runbooks/VERTA_PHASE_J_WAN_INTEROP_CHECKLIST.md`
- Modify: `packages/verta-protocol/docs/implementation/MILESTONE_51_IMPLEMENTATION_NOTES.md`

**Step 1: Write the failing test**

- Add wrapper smoke assertions in the example tests or script validation tests that verify default summary paths, required env names, and fail-closed exit behavior.

**Step 2: Run test to verify it fails**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
bash scripts/udp-wan-staging-interop.sh --help
```

Expected: FAIL because the wrapper does not exist yet.

**Step 3: Write minimal implementation**

- Bash and PowerShell wrappers should:
  - call the new example
  - keep summary, qlog, and packet-capture paths explicit
  - reject missing deployment label, host label, artifact root, and impairment selector
- The runbook should reuse the existing staging/canary operating model and specify:
  - required hosts
  - required secrets/tokens
  - where qlog/pcap artifacts are stored
  - how to abort and roll back if the run regresses

**Step 4: Run test to verify it passes**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
bash scripts/udp-wan-staging-interop.sh --help
```

Expected: PASS with usage text and clear required inputs.

**Step 5: Commit**

```bash
git add packages/verta-protocol/scripts/udp-wan-staging-interop.sh \
  packages/verta-protocol/scripts/udp-wan-staging-interop.ps1 \
  docs/runbooks/VERTA_PHASE_J_WAN_INTEROP_CHECKLIST.md \
  packages/verta-protocol/docs/implementation/MILESTONE_51_IMPLEMENTATION_NOTES.md
git commit -m "docs: add phase j wan interop wrapper and checklist"
```

### Task 3: Add Explicit Net-Chaos Campaign Coverage

**Files:**
- Create: `packages/verta-protocol/crates/ns-testkit/examples/udp_net_chaos_campaign.rs`
- Create: `packages/verta-protocol/scripts/udp-net-chaos-campaign.sh`
- Create: `packages/verta-protocol/scripts/udp-net-chaos-campaign.ps1`
- Modify: `packages/verta-protocol/crates/ns-testkit/src/lib.rs`
- Test: `packages/verta-protocol/crates/ns-testkit/examples/udp_net_chaos_campaign.rs`

**Step 1: Write the failing tests**

- Add tests that require named profiles for:
  - `loss-1`
  - `loss-5`
  - `jitter-low`
  - `jitter-high`
  - `reorder-2`
  - `reorder-10`
  - `mtu-1200`
  - `udp-blocked`
  - `udp-flaky`
  - `nat-rebind-midflow`
- Assert that each run records latency, reconnect, fallback, and artifact pointers.

**Step 2: Run test to verify it fails**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
cargo test -p ns-testkit --example udp_net_chaos_campaign -- --nocapture
```

Expected: FAIL because the campaign and named profile inventory do not exist yet.

**Step 3: Write minimal implementation**

- Add a net-chaos example that:
  - accepts a named impairment profile
  - shells out only to reviewed impairment tooling
  - records qlog/pcap paths, exit codes, and fallback counters
  - emits `target/verta/udp-net-chaos-campaign-summary.json`
- Keep it fail-closed when impairment tooling or artifact directories are missing.

**Step 4: Run test to verify it passes**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
cargo test -p ns-testkit --example udp_net_chaos_campaign -- --nocapture
```

Expected: PASS with stable named-profile coverage and artifact accounting.

**Step 5: Commit**

```bash
git add packages/verta-protocol/crates/ns-testkit/examples/udp_net_chaos_campaign.rs \
  packages/verta-protocol/scripts/udp-net-chaos-campaign.sh \
  packages/verta-protocol/scripts/udp-net-chaos-campaign.ps1 \
  packages/verta-protocol/crates/ns-testkit/src/lib.rs
git commit -m "feat: add phase j net chaos campaign lane"
```

### Task 4: Project WAN And Chaos Evidence Into Release-Candidate Consumers

**Files:**
- Modify: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_readiness.rs`
- Modify: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_acceptance.rs`
- Modify: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_certification.rs`
- Modify: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_signoff.rs`
- Modify: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_soak.rs`
- Test: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_readiness.rs`
- Test: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_acceptance.rs`
- Test: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_certification.rs`
- Test: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_signoff.rs`
- Test: `packages/verta-protocol/crates/ns-testkit/examples/udp_release_soak.rs`

**Step 1: Write the failing tests**

- Add summary-contract tests that require:
  - distinct accounting for `deterministic_lab`, `compatible_host`, `wan_staging`, and `net_chaos`
  - failure when only same-build compatible-host evidence exists
  - explicit artifact-presence checks for failed WAN/chaos runs

**Step 2: Run test to verify it fails**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
cargo test -p ns-testkit --example udp_release_candidate_readiness -- --nocapture
cargo test -p ns-testkit --example udp_release_candidate_acceptance -- --nocapture
cargo test -p ns-testkit --example udp_release_candidate_certification -- --nocapture
cargo test -p ns-testkit --example udp_release_candidate_signoff -- --nocapture
cargo test -p ns-testkit --example udp_release_soak -- --nocapture
```

Expected: FAIL until the new WAN/chaos required inputs and counters are wired through.

**Step 3: Write minimal implementation**

- Extend release-facing summaries with:
  - broader evidence-source counts
  - explicit WAN/chaos required-input presence and pass counts
  - artifact-root references for diagnosis
  - blocking reasons that distinguish lab-only readiness from broader deployment readiness

**Step 4: Run test to verify it passes**

Run the same commands as Step 2.

Expected: PASS with release-facing summaries that can reject lab-only evidence and explain why.

**Step 5: Commit**

```bash
git add packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_readiness.rs \
  packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_acceptance.rs \
  packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_certification.rs \
  packages/verta-protocol/crates/ns-testkit/examples/udp_release_candidate_signoff.rs \
  packages/verta-protocol/crates/ns-testkit/examples/udp_release_soak.rs
git commit -m "feat: require wan and chaos evidence in release gates"
```

### Task 5: Execute A First Phase J Campaign And Capture Evidence

**Files:**
- Modify: `packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md`
- Create: `packages/verta-protocol/docs/implementation/MILESTONE_52_IMPLEMENTATION_NOTES.md`
- Create: `docs/runbooks/VERTA_PHASE_J_ARTIFACT_RETENTION.md`

**Step 1: Run the WAN/staging lane**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
bash scripts/udp-wan-staging-interop.sh --json
```

Expected: PASS against the selected staging/WAN environment with retained summary + qlog/pcap paths.

**Step 2: Run the net-chaos lane**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
bash scripts/udp-net-chaos-campaign.sh --profile loss-5 --json
bash scripts/udp-net-chaos-campaign.sh --profile udp-blocked --json
bash scripts/udp-net-chaos-campaign.sh --profile nat-rebind-midflow --json
```

Expected: PASS or fail-closed with retained artifacts and operator-readable blocking reasons.

**Step 3: Run release-facing consumers**

Run:

```bash
cd /home/beep/projects/VPNBussiness/packages/verta-protocol
bash scripts/udp-release-candidate-readiness.sh
bash scripts/udp-release-soak.sh
```

Expected: PASS only when broader evidence is present; otherwise fail with explicit reasons.

**Step 4: Record evidence**

- Write milestone notes with:
  - environment labels
  - profile permutations run
  - failures seen
  - artifact roots
  - follow-up blockers

**Step 5: Commit**

```bash
git add packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md \
  packages/verta-protocol/docs/implementation/MILESTONE_52_IMPLEMENTATION_NOTES.md \
  docs/runbooks/VERTA_PHASE_J_ARTIFACT_RETENTION.md
git commit -m "docs: record first phase j wan and chaos campaign"
```

### Task 6: Promote Phase J Exit Criteria Into The Main Track

**Files:**
- Modify: `packages/verta-protocol/docs/implementation/PHASED_EXECUTION_PLAN.md`
- Modify: `packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md`
- Modify: `packages/verta-protocol/docs/implementation/MILESTONE_52_IMPLEMENTATION_NOTES.md`

**Step 1: Validate against exit criteria**

- Confirm:
  - release-candidate validation is broader than same-build compatible-host runs
  - critical fallback/degradation paths have WAN-like or staging-backed evidence
  - failed runs preserve artifacts
  - operator summaries separate lab evidence from broader deployment evidence

**Step 2: Update the phase documents**

- Mark `Phase J` complete only if every exit criterion is satisfied.
- If not, leave `Phase J` open and document the exact blocker without inventing `Phase O`.

**Step 3: Commit**

```bash
git add packages/verta-protocol/docs/implementation/PHASED_EXECUTION_PLAN.md \
  packages/verta-protocol/docs/implementation/IMPLEMENTATION_STATUS.md \
  packages/verta-protocol/docs/implementation/MILESTONE_52_IMPLEMENTATION_NOTES.md
git commit -m "docs: close phase j or record its exact blocker"
```

## Environment Inputs Needed To Start Phase J

- At least one staging or WAN-like environment reachable from this machine for end-to-end datagram traffic.
- A deployment label and host labels for every evidence lane.
- Artifact storage location for JSON summaries, qlog, pcap, and relevant logs.
- Reviewed impairment tooling for `tc netem`, namespaces, containers, or equivalent.
- At least one release-candidate cross-revision permutation to exercise, not only same-build compatible-host runs.
- Operator access to rollback-capable staging edge hosts if a chaos profile regresses the environment.

## Stop Rules

- Do not widen protocol semantics or add new transport personas just to satisfy coverage.
- Do not treat deterministic localhost interop as sufficient Phase J evidence.
- Do not promote `Phase J -> K` until WAN/chaos evidence is both real and operator-readable.
