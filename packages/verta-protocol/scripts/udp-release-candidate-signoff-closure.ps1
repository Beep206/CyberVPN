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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-signoff-closure-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-signoff-closure-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseCandidateEvidenceFreezePath = Get-VertaOutputPath $repoRoot "udp-release-candidate-evidence-freeze-summary.json"
$legacyReleaseCandidateEvidenceFreezePath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-evidence-freeze-summary.json"
$releaseCandidateEvidenceFreezePath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_RELEASE_CANDIDATE_EVIDENCE_FREEZE_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_RELEASE_CANDIDATE_EVIDENCE_FREEZE_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseCandidateEvidenceFreezePath $legacyReleaseCandidateEvidenceFreezePath }
$canonicalLinuxReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$legacyLinuxReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$linuxReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_LINUX_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_LINUX_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxReadinessPath $legacyLinuxReadinessPath }
$canonicalMacosReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$legacyMacosReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$macosReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_MACOS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_MACOS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalMacosReadinessPath $legacyMacosReadinessPath }
$canonicalWindowsReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$legacyWindowsReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$windowsReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_WINDOWS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_WINDOWS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsReadinessPath $legacyWindowsReadinessPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate signoff closure wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-signoff-closure.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-candidate-evidence-freeze", $releaseCandidateEvidenceFreezePath,
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

Write-Host "==> Running machine-readable UDP release candidate signoff closure"
& cargo run -p ns-testkit --example udp_release_candidate_signoff_closure -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
