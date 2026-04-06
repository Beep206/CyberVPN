# Helix Lab Live Results — 2026-04-01

## Scope

This note captures the first live desktop-to-Helix lab bench after:

- lab history reset
- desktop sidecar startup diagnostics hardening
- Helix runtime transfer-buffer tuning
- lab node restart/apply correctness fixes
- synthetic lab target wiring for transport-isolation benchmarking

## Artifacts

- External baseline before tuning:
  [C:\project\CyberVPN\apps\desktop-client\.artifacts\helix-lab\20260401-092648\helix-lab-benchmark-report.json](/C:/project/CyberVPN/apps/desktop-client/.artifacts/helix-lab/20260401-092648/helix-lab-benchmark-report.json)
- Synthetic lab benchmark after tuning:
  [C:\project\CyberVPN\apps\desktop-client\.artifacts\helix-lab\20260401-100512\helix-lab-benchmark-report.json](/C:/project/CyberVPN/apps/desktop-client/.artifacts/helix-lab/20260401-100512/helix-lab-benchmark-report.json)
- Stable external benchmark after tuning:
  [C:\project\CyberVPN\apps\desktop-client\.artifacts\helix-lab\20260401-095845\helix-lab-benchmark-report.json](/C:/project/CyberVPN/apps/desktop-client/.artifacts/helix-lab/20260401-095845/helix-lab-benchmark-report.json)
- Additional external sanity run:
  [C:\project\CyberVPN\apps\desktop-client\.artifacts\helix-lab\20260401-100525\helix-lab-benchmark-report.json](/C:/project/CyberVPN/apps/desktop-client/.artifacts/helix-lab/20260401-100525/helix-lab-benchmark-report.json)

## Key Numbers

### External baseline before tuning

- median connect latency: `1.41 ms`
- median first-byte latency: `526.22 ms`
- average throughput: `7497.9 kbps`

### External after tuning

Preferred stable comparison run:

- median connect latency: `2.16 ms`
- median first-byte latency: `493.88 ms`
- average throughput: `7703.74 kbps`

Observed delta versus baseline:

- first-byte latency improved by `32.34 ms` (`~6.1%`)
- average throughput improved by `205.84 kbps` (`~2.7%`)

Additional sanity run showed materially noisier wide-area behavior:

- median connect latency: `1.16 ms`
- median first-byte latency: `560.74 ms`
- average throughput: `6944.2 kbps`

Interpretation:

- wide-area Cloudflare runs remain noisy enough that external benches alone are not sufficient for tuning acceptance
- controlled synthetic lab runs should be treated as the primary signal for protocol/runtime tuning

### Synthetic lab after tuning

- median connect latency: `0.79 ms`
- median first-byte latency: `4.3 ms`
- average throughput: `78644.91 kbps`

Interpretation:

- Helix transport overhead inside the controlled lab path is low
- the tuned runtime comfortably saturates the synthetic target well above the external internet target rate
- future tuning should now focus on stream scheduling, session reuse, and route policy quality rather than basic transfer buffering

## Important Fixes Landed During This Run

- Helix node no longer treats a restored snapshot as proof that the runtime server is already active after process restart.
- Helix node idempotency now keys off a semantic runtime fingerprint instead of the adapter `assignment_hash`, which was too unstable for poll-by-poll re-fetches.
- Helix synthetic lab target is now reachable and benchmarkable without depending on Docker DNS resolution inside the node container.
- Desktop sidecar timeout errors now include client snapshot details, making live failure diagnosis much faster.

## Next Tuning Focus

- add per-stream queue/RTT telemetry into the desktop perf bundle
- benchmark route-quality scoring under deliberate route degradation
- measure reconnect and failover recovery time under synthetic packet loss / route drop
- compare Helix against `sing-box` and `xray` from the same desktop comparison runner using the same target matrix
