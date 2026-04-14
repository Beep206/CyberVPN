[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$summaryPath = if ($env:NORTHSTAR_UDP_PHASE_J_SIGNOFF_SUMMARY_PATH) { $env:NORTHSTAR_UDP_PHASE_J_SIGNOFF_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-phase-j-signoff-summary.json" }
$wanStagingPath = if ($env:NORTHSTAR_UDP_PHASE_J_SIGNOFF_WAN_STAGING_PATH) { $env:NORTHSTAR_UDP_PHASE_J_SIGNOFF_WAN_STAGING_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-wan-staging-interop-summary.json" }
$netChaosPath = if ($env:NORTHSTAR_UDP_PHASE_J_SIGNOFF_NET_CHAOS_PATH) { $env:NORTHSTAR_UDP_PHASE_J_SIGNOFF_NET_CHAOS_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-net-chaos-campaign-summary.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP Phase J signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-phase-j-signoff.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--wan-staging", $wanStagingPath,
        "--net-chaos", $netChaosPath
    )
}

Write-Host "==> Running machine-readable UDP Phase J signoff"
& cargo run -p ns-testkit --example udp_phase_j_signoff -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
