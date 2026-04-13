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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_GATE_SUMMARY_PATH) { $env:NORTHSTAR_UDP_RELEASE_GATE_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-gate-summary.json" }
$releaseSoakPath = if ($env:NORTHSTAR_UDP_RELEASE_GATE_RELEASE_SOAK_PATH) { $env:NORTHSTAR_UDP_RELEASE_GATE_RELEASE_SOAK_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-soak-summary.json" }
$linuxCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_GATE_LINUX_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_GATE_LINUX_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-linux.json" }
$macosCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_GATE_MACOS_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_GATE_MACOS_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-macos.json" }
$windowsCatalogPath = if ($env:NORTHSTAR_UDP_RELEASE_GATE_WINDOWS_INTEROP_CATALOG_PATH) { $env:NORTHSTAR_UDP_RELEASE_GATE_WINDOWS_INTEROP_CATALOG_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-profile-catalog-windows.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release gate wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-gate.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-soak", $releaseSoakPath,
        "--linux-interop-catalog", $linuxCatalogPath,
        "--macos-interop-catalog", $macosCatalogPath,
        "--windows-interop-catalog", $windowsCatalogPath
    )
}

Write-Host "==> Running machine-readable UDP release gate"
& cargo run -p ns-testkit --example udp_release_gate -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
