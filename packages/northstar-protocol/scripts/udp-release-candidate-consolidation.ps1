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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-candidate-consolidation-summary.json" }
$releaseStabilitySignoffPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_RELEASE_STABILITY_SIGNOFF_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_RELEASE_STABILITY_SIGNOFF_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-stability-signoff-summary.json" }
$linuxInteropCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_LINUX_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_LINUX_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-linux.json" }
$macosInteropCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_MACOS_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_MACOS_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-macos.json" }
$windowsInteropCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_WINDOWS_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_WINDOWS_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-windows.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate consolidation wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-consolidation.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-stability-signoff", $releaseStabilitySignoffPath,
        "--linux-interop-catalog", $linuxInteropCatalogPath,
        "--macos-interop-catalog", $macosInteropCatalogPath,
        "--windows-interop-catalog", $windowsInteropCatalogPath
    )
}

Write-Host "==> Running machine-readable UDP release candidate consolidation"
& cargo run -p ns-testkit --example udp_release_candidate_consolidation -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
