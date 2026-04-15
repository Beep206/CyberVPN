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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-gate-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-gate-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_GATE_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_GATE_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseSoakPath = Get-VertaOutputPath $repoRoot "udp-release-soak-summary.json"
$legacyReleaseSoakPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-soak-summary.json"
$releaseSoakPath = if ($env:VERTA_UDP_RELEASE_GATE_RELEASE_SOAK_PATH) { $env:VERTA_UDP_RELEASE_GATE_RELEASE_SOAK_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseSoakPath $legacyReleaseSoakPath }
$canonicalLinuxCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-linux.json"
$legacyLinuxCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-linux.json"
$linuxCatalogPath = if ($env:VERTA_UDP_RELEASE_GATE_LINUX_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_GATE_LINUX_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxCatalogPath $legacyLinuxCatalogPath }
$canonicalMacosCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-macos.json"
$legacyMacosCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-macos.json"
$macosCatalogPath = if ($env:VERTA_UDP_RELEASE_GATE_MACOS_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_GATE_MACOS_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalMacosCatalogPath $legacyMacosCatalogPath }
$canonicalWindowsCatalogPath = Get-VertaOutputPath $repoRoot "udp-interop-profile-catalog-windows.json"
$legacyWindowsCatalogPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-profile-catalog-windows.json"
$windowsCatalogPath = if ($env:VERTA_UDP_RELEASE_GATE_WINDOWS_INTEROP_CATALOG_PATH) { $env:VERTA_UDP_RELEASE_GATE_WINDOWS_INTEROP_CATALOG_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsCatalogPath $legacyWindowsCatalogPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release gate wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-gate.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-soak", $releaseSoakPath,
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

Write-Host "==> Running machine-readable UDP release gate"
& cargo run -p ns-testkit --example udp_release_gate -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
