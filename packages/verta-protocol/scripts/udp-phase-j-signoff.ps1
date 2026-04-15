[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "VertaCompat.ps1")

Sync-VertaPhaseJEnv

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-phase-j-signoff-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-phase-j-signoff-summary.json"
$summaryPath = if ($env:VERTA_UDP_PHASE_J_SIGNOFF_SUMMARY_PATH) { $env:VERTA_UDP_PHASE_J_SIGNOFF_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalWanStagingPath = Get-VertaOutputPath $repoRoot "udp-wan-staging-interop-summary.json"
$legacyWanStagingPath = Get-VertaLegacyOutputPath $repoRoot "udp-wan-staging-interop-summary.json"
$wanStagingPath = if ($env:VERTA_UDP_PHASE_J_SIGNOFF_WAN_STAGING_PATH) { $env:VERTA_UDP_PHASE_J_SIGNOFF_WAN_STAGING_PATH } else { Resolve-VertaPreferredPath $canonicalWanStagingPath $legacyWanStagingPath }
$canonicalNetChaosPath = Get-VertaOutputPath $repoRoot "udp-net-chaos-campaign-summary.json"
$legacyNetChaosPath = Get-VertaLegacyOutputPath $repoRoot "udp-net-chaos-campaign-summary.json"
$netChaosPath = if ($env:VERTA_UDP_PHASE_J_SIGNOFF_NET_CHAOS_PATH) { $env:VERTA_UDP_PHASE_J_SIGNOFF_NET_CHAOS_PATH } else { Resolve-VertaPreferredPath $canonicalNetChaosPath $legacyNetChaosPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP Phase J signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-phase-j-signoff.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--wan-staging", $wanStagingPath,
        "--net-chaos", $netChaosPath
    )
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP Phase J signoff"
& cargo run -p ns-testkit --example udp_phase_j_signoff -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
