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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-release-candidate-signoff-summary.json"
}
$releasePrepPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_RELEASE_PREP_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_RELEASE_PREP_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-release-prep-summary.json"
}
$windowsReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_READINESS_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_READINESS_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-windows.json"
}
$windowsInteropPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_INTEROP_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_INTEROP_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary-windows.json"
}
$macosInteropPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_MACOS_INTEROP_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_MACOS_INTEROP_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary-macos.json"
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-signoff.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-prep", $releasePrepPath,
        "--windows-readiness", $windowsReadinessPath,
        "--windows-interop", $windowsInteropPath,
        "--macos-interop", $macosInteropPath
    )
}

Write-Host "==> Running machine-readable UDP release candidate signoff"
& cargo run -p ns-testkit --example udp_release_candidate_signoff -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
