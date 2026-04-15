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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-release-workflow-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-release-workflow-summary.json"
$summaryPath = if ($env:VERTA_UDP_RELEASE_WORKFLOW_SUMMARY_PATH) { $env:VERTA_UDP_RELEASE_WORKFLOW_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalReadinessMatrixPath = Get-VertaOutputPath $repoRoot "udp-rollout-matrix-summary.json"
$legacyReadinessMatrixPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-matrix-summary.json"
$readinessMatrixPath = if ($env:VERTA_UDP_RELEASE_WORKFLOW_READINESS_MATRIX_PATH) { $env:VERTA_UDP_RELEASE_WORKFLOW_READINESS_MATRIX_PATH } else { Resolve-VertaPreferredPath $canonicalReadinessMatrixPath $legacyReadinessMatrixPath }
$canonicalStagedMatrixPath = Get-VertaOutputPath $repoRoot "udp-rollout-matrix-summary-staged.json"
$legacyStagedMatrixPath = Get-VertaLegacyOutputPath $repoRoot "udp-rollout-matrix-summary-staged.json"
$stagedMatrixPath = if ($env:VERTA_UDP_RELEASE_WORKFLOW_STAGED_MATRIX_PATH) { $env:VERTA_UDP_RELEASE_WORKFLOW_STAGED_MATRIX_PATH } else { Resolve-VertaPreferredPath $canonicalStagedMatrixPath $legacyStagedMatrixPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release workflow wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-workflow.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--input", $readinessMatrixPath,
        "--input", $stagedMatrixPath
    )
    $shouldMirrorDefault = $true
}
elseif (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs = @("--summary-path", $summaryPath) + $WorkflowArgs
    $shouldMirrorDefault = $true
}

Write-Host "==> Running machine-readable UDP release workflow"
& cargo run -p ns-testkit --example udp_release_workflow -- @WorkflowArgs
$exitCode = $LASTEXITCODE
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
if ($exitCode -ne 0) {
    exit $exitCode
}
