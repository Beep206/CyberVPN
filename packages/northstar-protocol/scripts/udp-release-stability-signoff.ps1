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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_SUMMARY_PATH) { $env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-stability-signoff-summary.json" }
$releaseReadinessBurndownPath = if ($env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_RELEASE_READINESS_BURNDOWN_PATH) { $env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_RELEASE_READINESS_BURNDOWN_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-readiness-burndown-summary.json" }
$linuxInteropPath = if ($env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_LINUX_INTEROP_PATH) { $env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_LINUX_INTEROP_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary-linux.json" }
$macosInteropPath = if ($env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_MACOS_INTEROP_PATH) { $env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_MACOS_INTEROP_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary-macos.json" }
$windowsInteropPath = if ($env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_WINDOWS_INTEROP_PATH) { $env:NORTHSTAR_UDP_RELEASE_STABILITY_SIGNOFF_WINDOWS_INTEROP_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-interop-lab-summary-windows.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release stability signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-stability-signoff.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-readiness-burndown", $releaseReadinessBurndownPath,
        "--linux-interop", $linuxInteropPath,
        "--macos-interop", $macosInteropPath,
        "--windows-interop", $windowsInteropPath
    )
}

Write-Host "==> Running machine-readable UDP release stability signoff"
& cargo run -p ns-testkit --example udp_release_stability_signoff -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
