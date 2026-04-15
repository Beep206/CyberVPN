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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-signoff-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-signoff-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleasePrepPath = Get-VertaOutputPath $repoRoot "udp-release-prep-summary.json"
$legacyReleasePrepPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-prep-summary.json"
$releasePrepPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_RELEASE_PREP_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_RELEASE_PREP_PATH } else { Resolve-VertaPreferredPath $canonicalReleasePrepPath $legacyReleasePrepPath }
$canonicalWindowsReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$legacyWindowsReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$windowsReadinessPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsReadinessPath $legacyWindowsReadinessPath }
$canonicalWindowsInteropPath = Get-VertaOutputPath $repoRoot "udp-interop-lab-summary-windows.json"
$legacyWindowsInteropPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-lab-summary-windows.json"
$windowsInteropPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_INTEROP_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_INTEROP_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsInteropPath $legacyWindowsInteropPath }
$canonicalMacosInteropPath = Get-VertaOutputPath $repoRoot "udp-interop-lab-summary-macos.json"
$legacyMacosInteropPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-lab-summary-macos.json"
$macosInteropPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_MACOS_INTEROP_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_MACOS_INTEROP_PATH } else { Resolve-VertaPreferredPath $canonicalMacosInteropPath $legacyMacosInteropPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-signoff.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-prep", $releasePrepPath,
        "--windows-readiness", $windowsReadinessPath,
        "--windows-interop", $windowsInteropPath,
        "--macos-interop", $macosInteropPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release candidate signoff"
& cargo run -p ns-testkit --example udp_release_candidate_signoff -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
