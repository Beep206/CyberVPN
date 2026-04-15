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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-certification-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-certification-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseCandidateAcceptancePath = Get-VertaOutputPath $repoRoot "udp-release-candidate-acceptance-summary.json"
$legacyReleaseCandidateAcceptancePath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-acceptance-summary.json"
$releaseCandidateAcceptancePath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_RELEASE_CANDIDATE_ACCEPTANCE_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_RELEASE_CANDIDATE_ACCEPTANCE_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseCandidateAcceptancePath $legacyReleaseCandidateAcceptancePath }
$canonicalLinuxInteropCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-linux.json"
$legacyLinuxInteropCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-linux.json"
$linuxInteropCatalogPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_LINUX_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_LINUX_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxInteropCatalogPath $legacyLinuxInteropCatalogPath }
$canonicalMacosInteropCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-macos.json"
$legacyMacosInteropCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-macos.json"
$macosInteropCatalogPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_MACOS_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_MACOS_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalMacosInteropCatalogPath $legacyMacosInteropCatalogPath }
$canonicalWindowsInteropCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-windows.json"
$legacyWindowsInteropCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-windows.json"
$windowsInteropCatalogPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_WINDOWS_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_WINDOWS_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsInteropCatalogPath $legacyWindowsInteropCatalogPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate certification wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-certification.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-candidate-acceptance", $releaseCandidateAcceptancePath,
        "--linux-interop-catalog", $linuxInteropCatalogPath,
        "--macos-interop-catalog", $macosInteropCatalogPath,
        "--windows-interop-catalog", $windowsInteropCatalogPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release candidate certification"
& cargo run -p ns-testkit --example udp_release_candidate_certification -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
