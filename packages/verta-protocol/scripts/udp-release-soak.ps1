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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-soak-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-soak-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_SOAK_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_SOAK_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseBurnInPath = Get-VertaOutputPath $repoRoot "udp-release-burn-in-summary.json"
$legacyReleaseBurnInPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-burn-in-summary.json"
$releaseBurnInPath = if ($env:VERTA_UDP_RELEASE_SOAK_RELEASE_BURN_IN_PATH) { $env:VERTA_UDP_RELEASE_SOAK_RELEASE_BURN_IN_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseBurnInPath $legacyReleaseBurnInPath }
$canonicalLinuxInteropPath = Get-VertaOutputPath $repoRoot "udp-interop-lab-summary-linux.json"
$legacyLinuxInteropPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-lab-summary-linux.json"
$linuxInteropPath = if ($env:VERTA_UDP_RELEASE_SOAK_LINUX_INTEROP_PATH) { $env:VERTA_UDP_RELEASE_SOAK_LINUX_INTEROP_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxInteropPath $legacyLinuxInteropPath }
$canonicalMacosInteropPath = Get-VertaOutputPath $repoRoot "udp-interop-lab-summary-macos.json"
$legacyMacosInteropPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-lab-summary-macos.json"
$macosInteropPath = if ($env:VERTA_UDP_RELEASE_SOAK_MACOS_INTEROP_PATH) { $env:VERTA_UDP_RELEASE_SOAK_MACOS_INTEROP_PATH } else { Resolve-VertaPreferredPath $canonicalMacosInteropPath $legacyMacosInteropPath }
$canonicalWindowsInteropPath = Get-VertaOutputPath $repoRoot "udp-interop-lab-summary-windows.json"
$legacyWindowsInteropPath = Get-VertaLegacyOutputPath $repoRoot "udp-interop-lab-summary-windows.json"
$windowsInteropPath = if ($env:VERTA_UDP_RELEASE_SOAK_WINDOWS_INTEROP_PATH) { $env:VERTA_UDP_RELEASE_SOAK_WINDOWS_INTEROP_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsInteropPath $legacyWindowsInteropPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release soak wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-soak.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-burn-in", $releaseBurnInPath,
        "--linux-interop", $linuxInteropPath,
        "--macos-interop", $macosInteropPath,
        "--windows-interop", $windowsInteropPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release soak"
& cargo run -p ns-testkit --example udp_release_soak -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
