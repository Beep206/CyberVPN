[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "VertaCompat.ps1")

Sync-VertaPhaseLEnv

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "phase-l-operator-readiness-signoff-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "phase-l-operator-readiness-signoff-summary.json"
$summaryPath = if ($env:VERTA_PHASE_L_OPERATOR_READINESS_SUMMARY_PATH) { $env:VERTA_PHASE_L_OPERATOR_READINESS_SUMMARY_PATH } else { $canonicalSummaryPath }
$runbookMatrixPath = if ($env:VERTA_PHASE_L_OPERATOR_READINESS_RUNBOOK_MATRIX_PATH) { $env:VERTA_PHASE_L_OPERATOR_READINESS_RUNBOOK_MATRIX_PATH } else { Join-Path $repoRoot "docs\\runbooks\\operator-recovery-matrix.json" }
$canonicalProfileDisableDrillPath = Get-VertaOutputPath $repoRoot "remnawave-supported-upstream-lifecycle-summary.json"
$legacyProfileDisableDrillPath = Get-VertaLegacyOutputPath $repoRoot "remnawave-supported-upstream-lifecycle-summary.json"
$profileDisableDrillPath = if ($env:VERTA_PHASE_L_OPERATOR_READINESS_PROFILE_DISABLE_DRILL_PATH) { $env:VERTA_PHASE_L_OPERATOR_READINESS_PROFILE_DISABLE_DRILL_PATH } else { Resolve-VertaPreferredPath $canonicalProfileDisableDrillPath $legacyProfileDisableDrillPath }
$canonicalRollbackDrillPath = Get-VertaOutputPath $repoRoot "operator-rollout-rollback-drill-summary.json"
$legacyRollbackDrillPath = Get-VertaLegacyOutputPath $repoRoot "operator-rollout-rollback-drill-summary.json"
$rollbackDrillPath = if ($env:VERTA_PHASE_L_OPERATOR_READINESS_ROLLBACK_DRILL_PATH) { $env:VERTA_PHASE_L_OPERATOR_READINESS_ROLLBACK_DRILL_PATH } else { Resolve-VertaPreferredPath $canonicalRollbackDrillPath $legacyRollbackDrillPath }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the Phase L operator-readiness wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/phase-l-operator-readiness.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    & "$PSScriptRoot\\operator-rollout-rollback-drill.ps1"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--runbook-matrix", $runbookMatrixPath,
        "--profile-disable-drill", $profileDisableDrillPath,
        "--rollback-drill", $rollbackDrillPath
    )
    $shouldMirrorDefault = $true
}

Write-Host "==> Running Phase L operator readiness signoff"
& cargo run -p ns-testkit --example phase_l_operator_readiness_signoff -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
