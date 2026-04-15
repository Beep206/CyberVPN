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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-prep-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-prep-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_PREP_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_PREP_SUMMARY_PATH } elseif ($env:VERTA_UDP_RELEASE_PREP_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_PREP_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalDeploymentSignoffPath = Get-VertaOutputPath $repoRoot "udp-deployment-signoff-summary.json"
$legacyDeploymentSignoffPath = Get-VertaLegacyOutputPath $repoRoot "udp-deployment-signoff-summary.json"
$deploymentSignoffPath = if ($env:VERTA_UDP_RELEASE_PREP_DEPLOYMENT_SIGNOFF_PATH) { $env:VERTA_UDP_RELEASE_PREP_DEPLOYMENT_SIGNOFF_PATH } elseif ($env:VERTA_UDP_RELEASE_PREP_DEPLOYMENT_SIGNOFF_PATH) { $env:VERTA_UDP_RELEASE_PREP_DEPLOYMENT_SIGNOFF_PATH } else { Resolve-VertaPreferredPath $canonicalDeploymentSignoffPath $legacyDeploymentSignoffPath }
$canonicalLinuxValidationPath = Get-VertaOutputPath $repoRoot "udp-rollout-validation-summary-linux.json"
$legacyLinuxValidationPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-validation-summary-linux.json"
$linuxValidationPath = if ($env:VERTA_UDP_RELEASE_PREP_LINUX_VALIDATION_PATH) { $env:VERTA_UDP_RELEASE_PREP_LINUX_VALIDATION_PATH } elseif ($env:VERTA_UDP_RELEASE_PREP_LINUX_VALIDATION_PATH) { $env:VERTA_UDP_RELEASE_PREP_LINUX_VALIDATION_PATH } else { Resolve-VertaPreferredPath $canonicalLinuxValidationPath $legacyLinuxValidationPath }
$canonicalMacosValidationPath = Get-VertaOutputPath $repoRoot "udp-rollout-validation-summary-macos.json"
$legacyMacosValidationPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-validation-summary-macos.json"
$macosValidationPath = if ($env:VERTA_UDP_RELEASE_PREP_MACOS_VALIDATION_PATH) { $env:VERTA_UDP_RELEASE_PREP_MACOS_VALIDATION_PATH } elseif ($env:VERTA_UDP_RELEASE_PREP_MACOS_VALIDATION_PATH) { $env:VERTA_UDP_RELEASE_PREP_MACOS_VALIDATION_PATH } else { Resolve-VertaPreferredPath $canonicalMacosValidationPath $legacyMacosValidationPath }
$canonicalWindowsValidationPath = Get-VertaOutputPath $repoRoot "udp-rollout-validation-summary-windows.json"
$legacyWindowsValidationPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-validation-summary-windows.json"
$windowsValidationPath = if ($env:VERTA_UDP_RELEASE_PREP_WINDOWS_VALIDATION_PATH) { $env:VERTA_UDP_RELEASE_PREP_WINDOWS_VALIDATION_PATH } elseif ($env:VERTA_UDP_RELEASE_PREP_WINDOWS_VALIDATION_PATH) { $env:VERTA_UDP_RELEASE_PREP_WINDOWS_VALIDATION_PATH } else { Resolve-VertaPreferredPath $canonicalWindowsValidationPath $legacyWindowsValidationPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release prep wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-prep.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--deployment-signoff", $deploymentSignoffPath,
        "--validation", $linuxValidationPath,
        "--validation", $macosValidationPath,
        "--validation", $windowsValidationPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release prep"
& cargo run -p ns-testkit --example udp_release_prep -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
