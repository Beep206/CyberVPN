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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-candidate-stabilization-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-stabilization-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalSignoffClosurePath = Get-VertaOutputPath $repoRoot "udp-release-candidate-signoff-closure-summary.json"
$legacySignoffClosurePath = Get-VertaLegacyOutputPath $repoRoot "udp-release-candidate-signoff-closure-summary.json"
$signoffClosurePath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH } else { Resolve-VertaPreferredPath $canonicalSignoffClosurePath $legacySignoffClosurePath }
$canonicalLinuxCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-linux.json"
$legacyLinuxCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-linux.json"
$linuxCatalogPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxCatalogPath $legacyLinuxCatalogPath }
$canonicalMacosCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-macos.json"
$legacyMacosCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-macos.json"
$macosCatalogPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalMacosCatalogPath $legacyMacosCatalogPath }
$canonicalWindowsCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-windows.json"
$legacyWindowsCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-windows.json"
$windowsCatalogPath = if ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH } elseif ($env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsCatalogPath $legacyWindowsCatalogPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate stabilization wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-stabilization.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-candidate-signoff-closure", $signoffClosurePath,
        "--linux-interop-catalog", $linuxCatalogPath,
        "--macos-interop-catalog", $macosCatalogPath,
        "--windows-interop-catalog", $windowsCatalogPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release candidate stabilization"
& cargo run -p ns-testkit --example udp_release_candidate_stabilization -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
