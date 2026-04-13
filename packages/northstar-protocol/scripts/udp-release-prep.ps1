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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_PREP_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_PREP_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-release-prep-summary.json"
}
$deploymentSignoffPath = if ($env:NORTHSTAR_UDP_RELEASE_PREP_DEPLOYMENT_SIGNOFF_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_PREP_DEPLOYMENT_SIGNOFF_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-deployment-signoff-summary.json"
}
$linuxValidationPath = if ($env:NORTHSTAR_UDP_RELEASE_PREP_LINUX_VALIDATION_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_PREP_LINUX_VALIDATION_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-validation-summary-linux.json"
}
$macosValidationPath = if ($env:NORTHSTAR_UDP_RELEASE_PREP_MACOS_VALIDATION_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_PREP_MACOS_VALIDATION_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-validation-summary-macos.json"
}
$windowsValidationPath = if ($env:NORTHSTAR_UDP_RELEASE_PREP_WINDOWS_VALIDATION_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_PREP_WINDOWS_VALIDATION_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-validation-summary-windows.json"
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release prep wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-prep.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--deployment-signoff", $deploymentSignoffPath,
        "--validation", $linuxValidationPath,
        "--validation", $macosValidationPath,
        "--validation", $windowsValidationPath
    )
}

Write-Host "==> Running machine-readable UDP release prep"
& cargo run -p ns-testkit --example udp_release_prep -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
