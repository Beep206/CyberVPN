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
$summaryPath = if ($env:NORTHSTAR_PHASE_L_OPERATOR_READINESS_SUMMARY_PATH) { $env:NORTHSTAR_PHASE_L_OPERATOR_READINESS_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\phase-l-operator-readiness-signoff-summary.json" }
$runbookMatrixPath = if ($env:NORTHSTAR_PHASE_L_OPERATOR_READINESS_RUNBOOK_MATRIX_PATH) { $env:NORTHSTAR_PHASE_L_OPERATOR_READINESS_RUNBOOK_MATRIX_PATH } else { Join-Path $repoRoot "docs\\runbooks\\operator-recovery-matrix.json" }
$profileDisableDrillPath = if ($env:NORTHSTAR_PHASE_L_OPERATOR_READINESS_PROFILE_DISABLE_DRILL_PATH) { $env:NORTHSTAR_PHASE_L_OPERATOR_READINESS_PROFILE_DISABLE_DRILL_PATH } else { Join-Path $repoRoot "target\\northstar\\remnawave-supported-upstream-lifecycle-summary.json" }
$rollbackDrillPath = if ($env:NORTHSTAR_PHASE_L_OPERATOR_READINESS_ROLLBACK_DRILL_PATH) { $env:NORTHSTAR_PHASE_L_OPERATOR_READINESS_ROLLBACK_DRILL_PATH } else { Join-Path $repoRoot "target\\northstar\\operator-rollout-rollback-drill-summary.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the Phase L operator-readiness wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/phase-l-operator-readiness.ps1."
}

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
}

Write-Host "==> Running Phase L operator readiness signoff"
& cargo run -p ns-testkit --example phase_l_operator_readiness_signoff -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
