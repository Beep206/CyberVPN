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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-readiness-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-readiness-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_SUMMARY_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseCandidateStabilizationPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-stabilization-summary.json"
$legacyReleaseCandidateStabilizationPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-stabilization-summary.json"
$releaseCandidateStabilizationPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_RELEASE_CANDIDATE_STABILIZATION_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_RELEASE_CANDIDATE_STABILIZATION_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_RELEASE_CANDIDATE_STABILIZATION_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_RELEASE_CANDIDATE_STABILIZATION_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseCandidateStabilizationPath $legacyReleaseCandidateStabilizationPath }
$canonicalLinuxReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$legacyLinuxReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$linuxReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_LINUX_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_LINUX_READINESS_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_LINUX_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_LINUX_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxReadinessPath $legacyLinuxReadinessPath }
$canonicalMacosReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$legacyMacosReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$macosReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_MACOS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_MACOS_READINESS_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_MACOS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_MACOS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalMacosReadinessPath $legacyMacosReadinessPath }
$canonicalWindowsReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$legacyWindowsReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$windowsReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_WINDOWS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_WINDOWS_READINESS_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_WINDOWS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_READINESS_WINDOWS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsReadinessPath $legacyWindowsReadinessPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate readiness wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-readiness.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-candidate-stabilization", $releaseCandidateStabilizationPath,
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

Write-Host "==> Running machine-readable UDP release candidate readiness"
& cargo run -p ns-testkit --example udp_release_candidate_readiness -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
