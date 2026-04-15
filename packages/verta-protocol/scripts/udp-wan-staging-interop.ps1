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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-wan-staging-interop-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-wan-staging-interop-summary.json"
$summaryPath = if ($env:VERTA_UDP_WAN_STAGING_SUMMARY_PATH) { $env:VERTA_UDP_WAN_STAGING_SUMMARY_PATH } elseif ($env:VERTA_UDP_WAN_STAGING_SUMMARY_PATH) { $env:VERTA_UDP_WAN_STAGING_SUMMARY_PATH } else { $canonicalSummaryPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP WAN staging interop wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-wan-staging-interop.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @("--summary-path", $summaryPath)
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP WAN staging interop"
& cargo run -p ns-testkit --example udp_wan_staging_interop -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
