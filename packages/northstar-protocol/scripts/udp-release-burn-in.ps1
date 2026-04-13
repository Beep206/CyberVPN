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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_BURN_IN_SUMMARY_PATH) { $env:NORTHSTAR_UDP_RELEASE_BURN_IN_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-burn-in-summary.json" }
$releaseCandidateSignoffPath = if ($env:NORTHSTAR_UDP_RELEASE_BURN_IN_RELEASE_CANDIDATE_SIGNOFF_PATH) { $env:NORTHSTAR_UDP_RELEASE_BURN_IN_RELEASE_CANDIDATE_SIGNOFF_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-candidate-signoff-summary.json" }
$linuxReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_BURN_IN_LINUX_READINESS_PATH) { $env:NORTHSTAR_UDP_RELEASE_BURN_IN_LINUX_READINESS_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-linux.json" }
$macosReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_BURN_IN_MACOS_READINESS_PATH) { $env:NORTHSTAR_UDP_RELEASE_BURN_IN_MACOS_READINESS_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-macos.json" }
$windowsReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_BURN_IN_WINDOWS_READINESS_PATH) { $env:NORTHSTAR_UDP_RELEASE_BURN_IN_WINDOWS_READINESS_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-windows.json" }
$stagedMatrixPath = if ($env:NORTHSTAR_UDP_RELEASE_BURN_IN_STAGED_MATRIX_PATH) { $env:NORTHSTAR_UDP_RELEASE_BURN_IN_STAGED_MATRIX_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-rollout-matrix-summary-staged.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release burn-in wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-burn-in.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-candidate-signoff", $releaseCandidateSignoffPath,
        "--linux-readiness", $linuxReadinessPath,
        "--macos-readiness", $macosReadinessPath,
        "--windows-readiness", $windowsReadinessPath,
        "--staged-matrix", $stagedMatrixPath
    )
}

Write-Host "==> Running machine-readable UDP release burn-in"
& cargo run -p ns-testkit --example udp_release_burn_in -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
