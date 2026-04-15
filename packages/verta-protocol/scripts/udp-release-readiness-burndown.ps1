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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-readiness-burndown-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-readiness-burndown-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseGatePath = Get-VertaOutputPath $repoRoot "udp-release-gate-summary.json"
$legacyReleaseGatePath = Get-VertaLegacyOutputPath $repoRoot "udp-release-gate-summary.json"
$releaseGatePath = if ($env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_RELEASE_GATE_PATH) { $env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_RELEASE_GATE_PATH } elseif ($env:VERTA_UDP_RELEASE_GATE_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_GATE_SUMMARY_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseGatePath $legacyReleaseGatePath }
$canonicalLinuxReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$legacyLinuxReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-linux.json"
$linuxReadinessPath = if ($env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_LINUX_READINESS_PATH) { $env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_LINUX_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxReadinessPath $legacyLinuxReadinessPath }
$canonicalMacosReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$legacyMacosReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-macos.json"
$macosReadinessPath = if ($env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_MACOS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_MACOS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalMacosReadinessPath $legacyMacosReadinessPath }
$canonicalWindowsReadinessPath = Get-VertaOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$legacyWindowsReadinessPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-comparison-summary-windows.json"
$windowsReadinessPath = if ($env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_WINDOWS_READINESS_PATH) { $env:VERTA_UDP_RELEASE_READINESS_BURNDOWN_WINDOWS_READINESS_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsReadinessPath $legacyWindowsReadinessPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release-readiness burn-down wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-readiness-burndown.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-gate", $releaseGatePath,
        "--linux-readiness", $linuxReadinessPath,
        "--macos-readiness", $macosReadinessPath,
        "--windows-readiness", $windowsReadinessPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release-readiness burn-down"
& cargo run -p ns-testkit --example udp_release_readiness_burndown -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
