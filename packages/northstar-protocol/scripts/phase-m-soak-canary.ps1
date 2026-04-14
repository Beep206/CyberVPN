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
$stageRoot = if ($env:NORTHSTAR_PHASE_M_STAGE_ROOT) { $env:NORTHSTAR_PHASE_M_STAGE_ROOT } else { Join-Path $repoRoot "target\northstar\phase-m-soak" }
$summaryPath = if ($env:NORTHSTAR_PHASE_M_SUMMARY_PATH) { $env:NORTHSTAR_PHASE_M_SUMMARY_PATH } else { Join-Path $repoRoot "target\northstar\phase-m-soak-canary-signoff-summary.json" }
$canaryPlanPath = if ($env:NORTHSTAR_PHASE_M_CANARY_PLAN_PATH) { $env:NORTHSTAR_PHASE_M_CANARY_PLAN_PATH } else { Join-Path $repoRoot "docs\runbooks\phase-m-canary-plan.json" }
$regressionLedgerPath = if ($env:NORTHSTAR_PHASE_M_REGRESSION_LEDGER_PATH) { $env:NORTHSTAR_PHASE_M_REGRESSION_LEDGER_PATH } else { Join-Path $repoRoot "docs\development\phase-m-regression-ledger.json" }
$phaseISummaryPath = if ($env:NORTHSTAR_PHASE_M_PHASE_I_SUMMARY_PATH) { $env:NORTHSTAR_PHASE_M_PHASE_I_SUMMARY_PATH } else { Join-Path $repoRoot "target\northstar\remnawave-supported-upstream-phase-i-signoff-summary.json" }
$wanStagingSummaryPath = if ($env:NORTHSTAR_PHASE_M_WAN_STAGING_SUMMARY_PATH) { $env:NORTHSTAR_PHASE_M_WAN_STAGING_SUMMARY_PATH } else { Join-Path $repoRoot "target\northstar\udp-wan-staging-interop-summary.json" }
$stagePauseSeconds = if ($env:NORTHSTAR_PHASE_M_STAGE_PAUSE_SECONDS) { [int]$env:NORTHSTAR_PHASE_M_STAGE_PAUSE_SECONDS } else { 5 }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the Phase M soak/canary wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/phase-m-soak-canary.ps1."
}

& "$PSScriptRoot\\remnawave-supported-upstream-phase-i-signoff.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$stageIds = @("canary_5", "canary_25", "canary_100")
for ($index = 0; $index -lt $stageIds.Count; $index++) {
    $stageId = $stageIds[$index]
    $stageDir = Join-Path $stageRoot $stageId
    $lifecycleSummaryPath = Join-Path $stageDir "lifecycle-summary.json"
    $rollbackSummaryPath = Join-Path $stageDir "rollback-summary.json"
    $rollbackArtifactRoot = Join-Path $stageDir "rollback-artifacts"
    $phaseLSummaryPath = Join-Path $stageDir "phase-l-summary.json"

    New-Item -ItemType Directory -Force -Path $stageDir | Out-Null
    & "$PSScriptRoot\\ensure-local-remnawave-supported-upstream-user-active.ps1"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH = $lifecycleSummaryPath
    & "$PSScriptRoot\\operator-profile-disable-drill.ps1"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $env:NORTHSTAR_UDP_NET_CHAOS_SUMMARY_PATH = $rollbackSummaryPath
    $env:NORTHSTAR_UDP_NET_CHAOS_ARTIFACT_ROOT = $rollbackArtifactRoot
    & "$PSScriptRoot\\operator-rollout-rollback-drill.ps1"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & cargo run -p ns-testkit --example phase_l_operator_readiness_signoff -- `
        --summary-path $phaseLSummaryPath `
        --profile-disable-drill $lifecycleSummaryPath `
        --rollback-drill $rollbackSummaryPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if ($stageId -ne "canary_100") {
        Start-Sleep -Seconds $stagePauseSeconds
    }
}

& cargo run -p ns-testkit --example phase_m_soak_canary_signoff -- `
    --summary-path $summaryPath `
    --stage-root $stageRoot `
    --canary-plan $canaryPlanPath `
    --regression-ledger $regressionLedgerPath `
    --phase-i $phaseISummaryPath `
    --wan-staging $wanStagingSummaryPath `
    @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
