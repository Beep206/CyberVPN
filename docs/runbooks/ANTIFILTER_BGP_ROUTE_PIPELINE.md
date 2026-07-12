# Antifilter BGP route pipeline

## Scope

This runbook covers the Task 2 Phase 1 offline foundation only:

- import externally supplied canonical CIDR files;
- validate, normalize, deduplicate, and safely collapse routes;
- preserve category membership and build the IPv4/IPv6 union;
- create deterministic canonical, manifest, delta, and Xray-renderable artifacts;
- quarantine suspicious candidates for checksum-bound manual approval;
- publish immutable versions with atomic active and last-known-good pointers.

The tools do not connect to Antifilter, scrape HTML, configure BGP, call
Remnawave, reload Xray, mutate infrastructure, or deploy to production. BIRD2
or FRR collection, real Xray validation, staging route tests, profile updates,
metrics, alerts, and production rollout remain later-phase work.

## Required communities

| Category key | Antifilter BGP communities |
| --- | --- |
| `rkn` | `65444:100` |
| `meta` | `65444:700` |
| `twitter_x` | `65444:710` |
| `netflix` | `65444:720` |
| `amazon_cloudfront` | `65444:730` |
| `microsoft` | `65444:740` |
| `amazon` | `65444:750` |
| `openai` | `65444:760` |
| `youtube` | `65444:770` |
| `google` | `65444:780` |
| `telegram` | `65444:790` |
| `discord` | `65444:800` |
| `custom_networks` | `65444:65444` |

Production decision 2026-07-12: the registered collector feed is complete
without a separate `65444:110` export. `65444:100` is therefore the sole
required RKN community. The observed total route count is operational evidence,
not a hardcoded acceptance threshold; all 13 configured communities must still
be non-empty and pass freshness, checksum, category bounds, delta and LKG gates.

Unknown communities and a source missing any required community are rejected.
Prefix and address counts are always derived from the supplied files; no live
feed snapshot count is compiled into the tool.

## Canonical input

The approved offline importer accepts a local `source.json` and local CIDR
files beneath the same source directory. It accepts no URL or archive input.
`source.type` must be `external-canonical-cidr` or `bgp-canonical-cidr`.
An HTML page is not an authoritative route source.

```json
{
  "schemaVersion": 1,
  "source": {
    "type": "external-canonical-cidr",
    "provider": "antifilter.network",
    "collector": "external-exporter-name",
    "generatedAt": "2026-07-11T00:00:00Z",
    "sourceVersion": "export-identifier"
  },
  "files": [
    {
      "community": "65444:100",
      "family": 4,
      "path": "65444_100.ipv4.cidr",
      "sha256": "lowercase-sha256-of-file"
    }
  ],
  "ipv6Policy": {
    "mode": "disabled",
    "reason": "No equivalent IPv6 feed has been proven; the tariff profile must disable IPv6."
  }
}
```

Every required community needs at least one declared family file. A community
may have one IPv4 and one IPv6 file. Paths must be relative POSIX paths and may
not contain `..`, backslashes, absolute roots, or symlinks. Each file is ASCII,
one CIDR per non-empty line, with no comments, attributes, whitespace, or BOM.
Host bits are accepted and normalized with `ip_network(..., strict=False)`.
The declared family must match every line and the file SHA-256 must match.

The importer enforces reviewed limits for manifest bytes, per-file bytes,
aggregate bytes, file count, lines per file, bytes per line, and compiled prefix
count. It does not support compressed input, so archive and decompression-bomb
paths do not exist in this phase.

The checked example is under `data/antifilter/fixtures/communities/`. It is a
small deterministic test corpus, not a current or production route feed.

## Reviewed policy

For fixture verification, pass `data/antifilter/example-policy.json`. For a
rollout, start from `data/antifilter/production-policy.example.json` and review
every endpoint and threshold. Never infer final production thresholds from the
small fixture or one live snapshot.

The policy controls:

- management CIDRs and exact self endpoints;
- per-category minimum and maximum compiled prefixes;
- maximum added and removed address percentages against the previous artifact;
- maximum IPv4 and IPv6 union address-space percentages, including bootstrap;
- maximum exclusion-count delta;
- maximum source age and future clock skew;
- explicit IPv6 mode and reason;
- all importer/compiler resource ceilings.

`data/antifilter/example-policy.json` is fixture-only and must never be used for
staging or production. `data/antifilter/production-policy.example.json` is the
rollout bootstrap: it contains the reviewed application, node, Antifilter-peer,
and IPv6 management/self endpoints; keeps IPv6 in `fallback_block`; requires
feed freshness within two hours; and assumes hourly updates. Its per-category
ranges are deliberately broad around the official 2026-07-11 snapshot counts.
This repository does not claim that a live feed was collected. After at least
24 hours of actual collector history, operators must review and narrow those
ranges before wider rollout.

Built-in forbidden ranges cover unspecified, loopback, RFC1918, CGNAT,
link-local, benchmark/documentation, multicast, reserved IPv4, IPv6
unspecified/loopback, ULA, link-local, documentation, and multicast space.
Reviewed management ranges are subtracted after built-ins. If any configured
self endpoint occurs in the source union, compilation fails instead of silently
publishing a candidate that could route its own control path.

## IPv6 no-bypass state

The source and policy must contain exactly the same IPv6 state:

- `enabled`: IPv4 and IPv6 compile separately; every required community must
  supply an IPv6 file, every category must retain IPv6 routes after exclusions,
  the IPv6 union must be non-empty, and the Xray artifact carries both families.
- `disabled`: IPv6 must be disabled by the eventual tariff profile; supplying
  IPv6 routes is rejected.
- `fallback_block`: the eventual profile must block IPv6; supplying a partial
  IPv6 exception feed is rejected.

There is no `direct` fallback state. The offline Xray artifact records the
required unmatched IPv6 behavior so later profile integration cannot interpret
an absent feed as permission for silent IPv6 bypass.

## Compile

Run from the repository root with Python 3.13. Use an output location outside
Git. `--now` is optional in normal operation and useful for deterministic
offline verification.

```powershell
backend/.venv/Scripts/python.exe -m scripts.remnawave.antifilter compile `
  --source data/antifilter/fixtures/communities/source.json `
  --policy data/antifilter/example-policy.json `
  --output $env:TEMP/cybervpn-antifilter-candidate `
  --now 2026-07-11T00:00:00Z
```

For a delta-aware candidate, point `--previous` at an immutable prior version:

```powershell
backend/.venv/Scripts/python.exe -m scripts.remnawave.antifilter compile `
  --source C:/route-feed/source.json `
  --policy C:/route-policy/policy.json `
  --previous C:/route-state/versions/PREVIOUS_VERSION_SHA256 `
  --output C:/route-candidates/CANDIDATE_NAME
```

Exit codes:

| Code | Meaning |
| ---: | --- |
| `0` | Candidate passed hard validation and automatic safety gates. |
| `1` | Source, policy, path, resource, checksum, freshness, self-route, or publish validation failed. |
| `2` | Candidate is valid but suspicious and requires manual approval before publish. |

A candidate directory is immutable. Compilation refuses an existing output
path and builds in a sibling temporary directory, fsyncs content where the OS
supports it, then uses an atomic rename. A failed switch removes the temporary
directory and leaves no partial candidate.

## Artifacts

Each candidate contains:

```text
manifest.json
canonical.json
categories/<category>.ipv4.cidr
categories/<category>.ipv6.cidr
union/ipv4.cidr
union/ipv6.cidr
deltas/added.ipv4.cidr
deltas/added.ipv6.cidr
deltas/removed.ipv4.cidr
deltas/removed.ipv6.cidr
xray/de-exceptions.json
```

`canonical.json` preserves every category's communities and separate IPv4/IPv6
CIDRs. Category collapse is independent, so an overlap or adjacent union
collapse cannot erase attribution. `union` is safely collapsed across
categories. Collapse only removes contained networks or combines exactly
adjacent siblings; it cannot add addresses outside the mathematical union.

`manifest.json` contains the source version and SHA-256, policy SHA-256,
per-category raw/compiled counts, decimal-string address counts, family counts,
category and union checksums, exclusion counts, previous manifest SHA-256,
exact added/removed CIDR deltas and address percentages, artifact checksums,
per-category deltas, IPv6 state, and safety status. The stable Task 2 operator
contract is `xray.rulesPath=xray/de-exceptions.json` plus the matching
`xray.rulesSha256`; the complete `artifacts` path-to-SHA map remains available
for immutable publish verification. Identical source, policy, prior artifact, and
controlled timestamp produce byte-identical output.

The Xray JSON is renderable route data, not a production Config Profile. It
contains non-empty matchers, `DE_EXCEPTIONS_BRIDGE`, and `fail_closed` metadata.
It does not select inline-versus-DAT for production, add customer inbounds, or
reload a runtime. Those decisions require benchmark and real Xray evidence.

## Suspicious approval

A suspicious category size, growth, shrink, or exclusion delta produces a
complete quarantined candidate with `safety.status=approval_required`. It is
not publishable without a matching manual record.

```powershell
backend/.venv/Scripts/python.exe -m scripts.remnawave.antifilter approve `
  --candidate C:/route-candidates/CANDIDATE_NAME `
  --output C:/route-approvals/CANDIDATE_NAME.json `
  --approved-by operator-id `
  --ticket CHANGE-1234
```

The record binds the candidate version, complete manifest SHA-256, sorted
suspicion reasons, reviewer, UTC approval time, and change ticket. Editing the
candidate or replaying the record for another manifest invalidates approval.
Access control and retention for the approval directory are operator concerns;
do not store approvals containing secrets in Git.

## Atomic publish and LKG

Publish to an operator-controlled state root outside Git:

```powershell
backend/.venv/Scripts/python.exe -m scripts.remnawave.antifilter publish `
  --candidate C:/route-candidates/CANDIDATE_NAME `
  --policy C:/route-policy/policy.json `
  --store C:/route-state
```

For an approved suspicious candidate, add
`--approval C:/route-approvals/CANDIDATE_NAME.json`.

The publisher verifies every declared artifact and rejects missing, extra,
tampered, escaping, or symlinked files. The reviewed `--policy` is required at
publish time; its checksum, category thresholds, forbidden/self ranges, address
coverage, IPv6 state, canonical union, Xray rules, and candidate version are
revalidated before any state write. It copies into a temporary version,
fsyncs the copied tree, verifies again, and atomically renames it to:

```text
C:/route-state/
  versions/<64-character-version-sha256>/...
  active.json
  last-known-good.json
  failures/<failure-record-sha256>.json
```

Pointer files contain only `version` and `manifestSha256` and are themselves
written by fsync plus atomic replacement. On the first publish, active and LKG
point to the same version. Later publishes never advance LKG; only an explicit
post-check `promote` can mark an active version known-good. Re-publishing the exact immutable version is
idempotent; a same-version content collision is rejected. Publish, promote,
and rollback share an exclusive `.state.lock`, so overlapping jobs cannot
interleave pointer changes. A lock left by a terminated process must only be
removed after an operator confirms no state-changing command is still running.

After later-phase external runtime validation succeeds, promote active:

```powershell
backend/.venv/Scripts/python.exe -m scripts.remnawave.antifilter promote --store C:/route-state
```

If that external validation fails, atomically restore LKG:

```powershell
backend/.venv/Scripts/python.exe -m scripts.remnawave.antifilter rollback --store C:/route-state
```

The offline publisher only changes artifact pointers. It does not perform an
Xray reload, post-deploy smoke, or Remnawave profile update.

## Failure handling

Pass `--state` to `compile` to record a safe degraded attempt without changing
active or LKG:

```powershell
backend/.venv/Scripts/python.exe -m scripts.remnawave.antifilter compile `
  --source C:/route-feed/source.json `
  --policy C:/route-policy/policy.json `
  --output C:/route-candidates/CANDIDATE_NAME `
  --state C:/route-state
```

Invalid, empty, stale, corrupt, oversized, family-mismatched, self-routing, and
hard safety failures create no candidate and cannot publish. A failure record
contains a bounded safe reason, source manifest checksum when readable, UTC
failure time, and `degraded` status. It does not contain route feed content,
BGP session credentials, bridge secrets, Remnawave tokens, VLESS identifiers,
subscription URLs, customer data, or stack traces. Existing active/LKG pointer
bytes remain unchanged.

## Offline verification

```powershell
backend/.venv/Scripts/python.exe -m pytest `
  backend/tests/unit/scripts/test_antifilter_route_compiler.py `
  -q --no-cov -p no:cacheprovider

backend/.venv/Scripts/python.exe -m ruff check `
  scripts/remnawave/antifilter `
  backend/tests/unit/scripts/test_antifilter_route_compiler.py

backend/.venv/Scripts/python.exe -m ruff format --check `
  scripts/remnawave/antifilter `
  backend/tests/unit/scripts/test_antifilter_route_compiler.py
```

The tests use no internet or production service. They cover every community,
normalization, duplicate/contained/adjacent collapse, category attribution,
deterministic randomized inputs, exact coverage, invalid/empty/stale/suspicious
feeds, IPv4/IPv6 separation, private/management/self handling, checksums and
deltas, traversal/symlink/resource rejection, approval binding, immutable
publish, LKG retention, rollback, idempotency, and tamper rejection.

## Deferred release gates

Do not treat this offline foundation as proof that the Task 2 tariff is ready.
Later owners must still provide an authoritative BIRD2 or FRR collector with
the same source contract, history-derived production thresholds, real Xray
config validation and inline-versus-DAT benchmarks, staging SPB-to-DE bridge
tests, matched fail-closed behavior, unmatched SPB direct behavior, IPv6 leak
tests, Remnawave profile isolation, observability, canary evidence, and a
production rollback procedure.
