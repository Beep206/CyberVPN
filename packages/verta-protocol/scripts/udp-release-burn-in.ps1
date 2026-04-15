[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "VertaCompat.ps1")

Sync-VertaReleaseEvidenceEnv

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-burn-in-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-burn-in-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_BURN_IN_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_BURN_IN_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseCandidateSignoffPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-signoff-summary.json"
$legacyReleaseCandidateSignoffPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-signoff-summary.json"
$releaseCandidateSignoffPath = if ($env:VERTA_UDP_RELEASE_BURN_IN_RELEASE_CANDIDATE_SIGNOFF_PATH) { $env:VERTA_UDP_RELEASE_BURN_IN_RELEASE_CANDIDATE_SIGNOFF_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseCandidateSignoffPath $legacyReleaseCandidateSignoffPath }
$canonicalLinuxReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$legacyLinuxReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$linuxReadinessPath = if ($env:VERTA_UDP_RELEASE_BURN_IN_LINUX_READINESS_PATH) { $env:VERTA_UDP_RELEASE_BURN_IN_LINUX_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxReadinessPath $legacyLinuxReadinessPath }
$canonicalMacosReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$legacyMacosReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$macosReadinessPath = if ($env:VERTA_UDP_RELEASE_BURN_IN_MACOS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_BURN_IN_MACOS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalMacosReadinessPath $legacyMacosReadinessPath }
$canonicalWindowsReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$legacyWindowsReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$windowsReadinessPath = if ($env:VERTA_UDP_RELEASE_BURN_IN_WINDOWS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_BURN_IN_WINDOWS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsReadinessPath $legacyWindowsReadinessPath }
$canonicalStagedMatrixPath = Get-VertaOutputPath $repoRoot "udp-rollout-matrix-summary-staged.json"
$legacyStagedMatrixPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-matrix-summary-staged.json"
$stagedMatrixPath = if ($env:VERTA_UDP_RELEASE_BURN_IN_STAGED_MATRIX_PATH) { $env:VERTA_UDP_RELEASE_BURN_IN_STAGED_MATRIX_PATH } elseif ($env:VERTA_UDP_RELEASE_EVIDENCE_CHAIN_STAGED_MATRIX_PATH) { $env:VERTA_UDP_RELEASE_EVIDENCE_CHAIN_STAGED_MATRIX_PATH } else { Resolve-VertaPreferredPath $canonicalStagedMatrixPath $legacyStagedMatrixPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release burn-in wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-burn-in.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-candidate-signoff", $releaseCandidateSignoffPath,
        "--linux-readiness", $linuxReadinessPath,
        "--macos-readiness", $macosReadinessPath,
        "--windows-readiness", $windowsReadinessPath,
        "--staged-matrix", $stagedMatrixPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release burn-in"
& cargo run -p ns-testkit --example udp_release_burn_in -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
