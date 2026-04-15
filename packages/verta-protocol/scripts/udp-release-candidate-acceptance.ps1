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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-acceptance-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-acceptance-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseCandidateReadinessPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-readiness-summary.json"
$legacyReleaseCandidateReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-readiness-summary.json"
$releaseCandidateReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_RELEASE_CANDIDATE_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_RELEASE_CANDIDATE_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseCandidateReadinessPath $legacyReleaseCandidateReadinessPath }
$canonicalLinuxReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$legacyLinuxReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$linuxReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_LINUX_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_LINUX_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxReadinessPath $legacyLinuxReadinessPath }
$canonicalMacosReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$legacyMacosReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$macosReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_MACOS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_MACOS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalMacosReadinessPath $legacyMacosReadinessPath }
$canonicalWindowsReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$legacyWindowsReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$windowsReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_WINDOWS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_ACCEPTANCE_WINDOWS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsReadinessPath $legacyWindowsReadinessPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate acceptance wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-acceptance.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-candidate-readiness", $releaseCandidateReadinessPath,
        "--linux-readiness", $linuxReadinessPath,
        "--macos-readiness", $macosReadinessPath,
        "--windows-readiness", $windowsReadinessPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release candidate acceptance"
& cargo run -p ns-testkit --example udp_release_candidate_acceptance -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
