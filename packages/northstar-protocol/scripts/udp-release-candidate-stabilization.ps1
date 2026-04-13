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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-candidate-stabilization-summary.json" }
$signoffClosurePath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-candidate-signoff-closure-summary.json" }
$linuxCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-linux.json" }
$macosCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-macos.json" }
$windowsCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-windows.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate stabilization wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-stabilization.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-candidate-signoff-closure", $signoffClosurePath,
        "--linux-interop-catalog", $linuxCatalogPath,
        "--macos-interop-catalog", $macosCatalogPath,
        "--windows-interop-catalog", $windowsCatalogPath
    )
}

Write-Host "==> Running machine-readable UDP release candidate stabilization"
& cargo run -p ns-testkit --example udp_release_candidate_stabilization -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
