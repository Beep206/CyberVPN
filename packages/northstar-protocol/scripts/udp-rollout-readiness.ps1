[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$smokeSummaryPath = if ($env:NORTHSTAR_UDP_FUZZ_SMOKE_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_FUZZ_SMOKE_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-fuzz-smoke-summary.json"
}
$perfSummaryPath = if ($env:NORTHSTAR_UDP_PERF_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_PERF_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-perf-gate-summary.json"
}
$interopSummaryPath = if ($env:NORTHSTAR_UDP_INTEROP_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_INTEROP_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary.json"
}
$rolloutSummaryPath = if ($env:NORTHSTAR_UDP_ROLLOUT_VALIDATION_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_ROLLOUT_VALIDATION_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-validation-summary.json"
}
$comparisonSummaryPath = if ($env:NORTHSTAR_UDP_ROLLOUT_COMPARISON_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_ROLLOUT_COMPARISON_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary.json"
}
$activeFuzzSummaryPath = if ($env:NORTHSTAR_UDP_ACTIVE_FUZZ_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_ACTIVE_FUZZ_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-active-fuzz-summary.json"
}
$rolloutCompareProfile = if ($env:NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE) {
    $env:NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE
}
else {
    "readiness"
}

if ($rolloutCompareProfile -notin @("readiness", "staged_rollout")) {
    Fail "NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE must be either 'readiness' or 'staged_rollout'."
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP rollout-readiness path."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-rollout-readiness.ps1."
}

Write-Host "==> Synchronizing reviewed UDP fuzz corpus"
& cargo run -p ns-testkit --example sync_udp_fuzz_corpus
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> Replaying reviewed UDP fuzz smoke seeds"
& cargo run -p ns-testkit --example udp_fuzz_smoke
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> Running UDP performance threshold gate"
& cargo run -p ns-testkit --example udp_perf_gate
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> Running machine-readable UDP interoperability lab"
& cargo run -p ns-testkit --example udp_interop_lab -- --all --summary-path $interopSummaryPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> Running machine-readable UDP rollout validation lab"
& cargo run -p ns-testkit --example udp_rollout_validation_lab -- --summary-path $rolloutSummaryPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> Running machine-readable UDP rollout comparison surface"
& cargo run -p ns-testkit --example udp_rollout_compare -- --profile $rolloutCompareProfile --summary-path $comparisonSummaryPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path $smokeSummaryPath)) {
    Fail "UDP fuzz smoke summary was not produced at $smokeSummaryPath."
}
if (-not (Test-Path $perfSummaryPath)) {
    Fail "UDP perf summary was not produced at $perfSummaryPath."
}
if (-not (Test-Path $interopSummaryPath)) {
    Fail "UDP interop summary was not produced at $interopSummaryPath."
}
if (-not (Test-Path $rolloutSummaryPath)) {
    Fail "UDP rollout validation summary was not produced at $rolloutSummaryPath."
}
if (-not (Test-Path $comparisonSummaryPath)) {
    Fail "UDP rollout comparison summary was not produced at $comparisonSummaryPath."
}
if ($rolloutCompareProfile -eq "staged_rollout" -and -not (Test-Path $activeFuzzSummaryPath)) {
    Fail "UDP active fuzz summary was not produced at $activeFuzzSummaryPath for staged_rollout comparison."
}

Write-Host "Northstar UDP rollout-readiness path completed successfully."
Write-Host "smoke_summary=$smokeSummaryPath"
Write-Host "perf_summary=$perfSummaryPath"
Write-Host "interop_summary=$interopSummaryPath"
Write-Host "rollout_validation_summary=$rolloutSummaryPath"
if ($rolloutCompareProfile -eq "staged_rollout") {
    Write-Host "active_fuzz_summary=$activeFuzzSummaryPath"
}
Write-Host "rollout_comparison_summary=$comparisonSummaryPath"
