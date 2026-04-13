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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_SOAK_SUMMARY_PATH) { $env:NORTHSTAR_UDP_RELEASE_SOAK_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-soak-summary.json" }
$releaseBurnInPath = if ($env:NORTHSTAR_UDP_RELEASE_SOAK_RELEASE_BURN_IN_PATH) { $env:NORTHSTAR_UDP_RELEASE_SOAK_RELEASE_BURN_IN_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-burn-in-summary.json" }
$linuxInteropPath = if ($env:NORTHSTAR_UDP_RELEASE_SOAK_LINUX_INTEROP_PATH) { $env:NORTHSTAR_UDP_RELEASE_SOAK_LINUX_INTEROP_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary-linux.json" }
$macosInteropPath = if ($env:NORTHSTAR_UDP_RELEASE_SOAK_MACOS_INTEROP_PATH) { $env:NORTHSTAR_UDP_RELEASE_SOAK_MACOS_INTEROP_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary-macos.json" }
$windowsInteropPath = if ($env:NORTHSTAR_UDP_RELEASE_SOAK_WINDOWS_INTEROP_PATH) { $env:NORTHSTAR_UDP_RELEASE_SOAK_WINDOWS_INTEROP_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary-windows.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release soak wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-soak.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-burn-in", $releaseBurnInPath,
        "--linux-interop", $linuxInteropPath,
        "--macos-interop", $macosInteropPath,
        "--windows-interop", $windowsInteropPath
    )
}

Write-Host "==> Running machine-readable UDP release soak"
& cargo run -p ns-testkit --example udp_release_soak -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
