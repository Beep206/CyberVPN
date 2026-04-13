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
$summaryPath = if ($env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH) {
    $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH
} else {
    Join-Path $repoRoot "target\northstar\remnawave-supported-upstream-lifecycle-summary.json"
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the supported-upstream lifecycle verification wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-lifecycle-verify.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath
    )
}

Write-Host "==> Running Remnawave supported-upstream lifecycle verification"
& cargo run -p ns-testkit --example remnawave_supported_upstream_lifecycle_verification -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
