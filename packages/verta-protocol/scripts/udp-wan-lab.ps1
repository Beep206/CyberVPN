[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$InteropArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "VertaCompat.ps1")

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
Sync-VertaRolloutReadinessEnv
$canonicalDefaultSummaryPath = Get-VertaOutputPath $repoRoot "udp-interop-lab-summary.json"
$legacyDefaultSummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-lab-summary.json"
$summaryPath = if ($env:VERTA_UDP_INTEROP_SUMMARY_PATH) {
    $env:VERTA_UDP_INTEROP_SUMMARY_PATH
}
else {
    $canonicalDefaultSummaryPath
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP WAN-lab verification path."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-wan-lab.ps1."
}

Write-Host "==> Running reusable UDP interoperability lab harness"
& cargo run -p ns-testkit --example udp_interop_lab -- @InteropArgs --summary-path $summaryPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path $summaryPath)) {
    Fail "UDP interoperability lab did not produce the expected machine-readable summary at $summaryPath."
}

Copy-VertaCanonicalOutputToLegacy $summaryPath $canonicalDefaultSummaryPath $legacyDefaultSummaryPath

Write-Host "Verta UDP WAN-lab verification path completed successfully."
Write-Host "machine_readable_summary=$summaryPath"
