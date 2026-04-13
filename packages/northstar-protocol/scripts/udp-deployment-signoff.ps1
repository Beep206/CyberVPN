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
$summaryPath = if ($env:NORTHSTAR_UDP_DEPLOYMENT_SIGNOFF_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_DEPLOYMENT_SIGNOFF_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-deployment-signoff-summary.json"
}
$releaseWorkflowPath = if ($env:NORTHSTAR_UDP_RELEASE_WORKFLOW_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_WORKFLOW_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-release-workflow-summary.json"
}
$validationPath = if ($env:NORTHSTAR_UDP_DEPLOYMENT_VALIDATION_PATH) {
    $env:NORTHSTAR_UDP_DEPLOYMENT_VALIDATION_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-validation-summary-windows.json"
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP deployment signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-deployment-signoff.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-workflow", $releaseWorkflowPath,
        "--validation", $validationPath
    )
}

Write-Host "==> Running machine-readable UDP deployment signoff"
& cargo run -p ns-testkit --example udp_deployment_signoff -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
