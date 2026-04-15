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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-deployment-signoff-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-deployment-signoff-summary.json"
$summaryPath = if ($env:VERTA_UDP_DEPLOYMENT_SIGNOFF_SUMMARY_PATH) { $env:VERTA_UDP_DEPLOYMENT_SIGNOFF_SUMMARY_PATH } elseif ($env:VERTA_UDP_DEPLOYMENT_SIGNOFF_SUMMARY_PATH) { $env:VERTA_UDP_DEPLOYMENT_SIGNOFF_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReleaseWorkflowPath = Get-VertaOutputPath $repoRoot "udp-release-workflow-summary.json"
$legacyReleaseWorkflowPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-workflow-summary.json"
$releaseWorkflowPath = if ($env:VERTA_UDP_DEPLOYMENT_SIGNOFF_RELEASE_WORKFLOW_PATH) { $env:VERTA_UDP_DEPLOYMENT_SIGNOFF_RELEASE_WORKFLOW_PATH } elseif ($env:VERTA_UDP_DEPLOYMENT_SIGNOFF_RELEASE_WORKFLOW_PATH) { $env:VERTA_UDP_DEPLOYMENT_SIGNOFF_RELEASE_WORKFLOW_PATH } elseif ($env:VERTA_UDP_RELEASE_WORKFLOW_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_WORKFLOW_SUMMARY_PATH } elseif ($env:VERTA_UDP_RELEASE_WORKFLOW_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_WORKFLOW_SUMMARY_PATH } else { Resolve-VertaPreferredPath $canonicalReleaseWorkflowPath $legacyReleaseWorkflowPath }
$canonicalValidationPath = Get-VertaOutputPath $repoRoot "udp-rollout-validation-summary-windows.json"
$legacyValidationPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-validation-summary-windows.json"
$validationPath = if ($env:VERTA_UDP_DEPLOYMENT_VALIDATION_PATH) { $env:VERTA_UDP_DEPLOYMENT_VALIDATION_PATH } elseif ($env:VERTA_UDP_DEPLOYMENT_VALIDATION_PATH) { $env:VERTA_UDP_DEPLOYMENT_VALIDATION_PATH } else { Resolve-VertaPreferredPath $canonicalValidationPath $legacyValidationPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP deployment signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-deployment-signoff.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-workflow", $releaseWorkflowPath,
        "--validation", $validationPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP deployment signoff"
& cargo run -p ns-testkit --example udp_deployment_signoff -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
