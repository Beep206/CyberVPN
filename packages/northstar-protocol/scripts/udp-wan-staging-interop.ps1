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
$summaryPath = if ($env:NORTHSTAR_UDP_WAN_STAGING_SUMMARY_PATH) { $env:NORTHSTAR_UDP_WAN_STAGING_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-wan-staging-interop-summary.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP WAN staging interop wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-wan-staging-interop.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @("--summary-path", $summaryPath)
}

Write-Host "==> Running machine-readable UDP WAN staging interop"
& cargo run -p ns-testkit --example udp_wan_staging_interop -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
