[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "VertaCompat.ps1")

Sync-VertaPhaseNEnv

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "phase-n-production-ready-signoff-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "phase-n-production-ready-signoff-summary.json"
$summaryPath = if ($env:VERTA_PHASE_N_SUMMARY_PATH) { $env:VERTA_PHASE_N_SUMMARY_PATH } else { $canonicalSummaryPath }
$canonicalPhaseISummaryPath = Get-VertaOutputPath $repoRoot "remnawave-supported-upstream-phase-i-signoff-summary.json"
$legacyPhaseISummaryPath = Get-VertaLegacyOutputPath $repoRoot "remnawave-supported-upstream-phase-i-signoff-summary.json"
$phaseISummaryPath = if ($env:VERTA_PHASE_N_PHASE_I_SUMMARY_PATH) { $env:VERTA_PHASE_N_PHASE_I_SUMMARY_PATH } else { Resolve-VertaPreferredPath $canonicalPhaseISummaryPath $legacyPhaseISummaryPath }
$canonicalPhaseJSummaryPath = Get-VertaOutputPath $repoRoot "udp-phase-j-signoff-summary.json"
$legacyPhaseJSummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-phase-j-signoff-summary.json"
$phaseJSummaryPath = if ($env:VERTA_PHASE_N_PHASE_J_SUMMARY_PATH) { $env:VERTA_PHASE_N_PHASE_J_SUMMARY_PATH } else { Resolve-VertaPreferredPath $canonicalPhaseJSummaryPath $legacyPhaseJSummaryPath }
$canonicalPhaseLSummaryPath = Get-VertaOutputPath $repoRoot "phase-l-operator-readiness-signoff-summary.json"
$legacyPhaseLSummaryPath = Get-VertaLegacyOutputPath $repoRoot "phase-l-operator-readiness-signoff-summary.json"
$phaseLSummaryPath = if ($env:VERTA_PHASE_N_PHASE_L_SUMMARY_PATH) { $env:VERTA_PHASE_N_PHASE_L_SUMMARY_PATH } else { Resolve-VertaPreferredPath $canonicalPhaseLSummaryPath $legacyPhaseLSummaryPath }
$canonicalPhaseMSummaryPath = Get-VertaOutputPath $repoRoot "phase-m-soak-canary-signoff-summary.json"
$legacyPhaseMSummaryPath = Get-VertaLegacyOutputPath $repoRoot "phase-m-soak-canary-signoff-summary.json"
$phaseMSummaryPath = if ($env:VERTA_PHASE_N_PHASE_M_SUMMARY_PATH) { $env:VERTA_PHASE_N_PHASE_M_SUMMARY_PATH } else { Resolve-VertaPreferredPath $canonicalPhaseMSummaryPath $legacyPhaseMSummaryPath }
$releaseChecklistPath = if ($env:VERTA_PHASE_N_RELEASE_CHECKLIST_PATH) { $env:VERTA_PHASE_N_RELEASE_CHECKLIST_PATH } else { Join-Path $repoRoot "docs\release\production-ready-checklist.json" }
$supportMatrixPath = if ($env:VERTA_PHASE_N_SUPPORT_MATRIX_PATH) { $env:VERTA_PHASE_N_SUPPORT_MATRIX_PATH } else { Join-Path $repoRoot "docs\release\supported-environment-matrix.json" }
$knownLimitationsPath = if ($env:VERTA_PHASE_N_KNOWN_LIMITATIONS_PATH) { $env:VERTA_PHASE_N_KNOWN_LIMITATIONS_PATH } else { Join-Path $repoRoot "docs\release\known-limitations.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the Phase N production-ready wrapper."
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail "git was not found. Install git before running the Phase N production-ready wrapper."
}
if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/phase-n-production-ready.ps1."
}

$projectRoot = (& git -C $repoRoot rev-parse --show-toplevel 2>$null)
if (-not $projectRoot) {
    Fail "Unable to resolve the project root via git."
}

$gitHead = (& git -C $projectRoot rev-parse HEAD 2>$null)
$gitBranch = (& git -C $projectRoot branch --show-current 2>$null)
$gitStatus = (& git -C $projectRoot status --porcelain)
$gitClean = if ([string]::IsNullOrWhiteSpace(($gitStatus -join ""))) { "true" } else { "false" }

Write-Host "==> Running Phase N production-ready signoff"
& cargo run --manifest-path $workspaceManifest -p ns-testkit --example phase_n_production_ready_signoff -- `
    --project-root $projectRoot `
    --summary-path $summaryPath `
    --phase-i $phaseISummaryPath `
    --phase-j $phaseJSummaryPath `
    --phase-l $phaseLSummaryPath `
    --phase-m $phaseMSummaryPath `
    --release-checklist $releaseChecklistPath `
    --support-matrix $supportMatrixPath `
    --known-limitations $knownLimitationsPath `
    --git-head $gitHead `
    --git-branch $gitBranch `
    --git-clean $gitClean `
    @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
