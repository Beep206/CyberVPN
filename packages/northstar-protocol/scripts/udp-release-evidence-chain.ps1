[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$readinessMatrixPath = if ($env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_READINESS_MATRIX_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_READINESS_MATRIX_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-matrix-summary.json"
}
$stagedMatrixPath = if ($env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_STAGED_MATRIX_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_STAGED_MATRIX_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-matrix-summary-staged.json"
}
$linuxReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_LINUX_READINESS_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_LINUX_READINESS_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-linux.json"
}
$macosReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_MACOS_READINESS_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_MACOS_READINESS_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-macos.json"
}
$windowsReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_WINDOWS_READINESS_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_WINDOWS_READINESS_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-windows.json"
}
$linuxStagedPath = if ($env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_LINUX_STAGED_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_LINUX_STAGED_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-linux-staged.json"
}
$macosStagedPath = if ($env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_MACOS_STAGED_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_EVIDENCE_CHAIN_MACOS_STAGED_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-macos-staged.json"
}
$finalSummaryPath = if ($env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CERTIFICATION_SUMMARY_PATH) {
    $env:NORTHSTAR_UDP_RELEASE_CANDIDATE_CERTIFICATION_SUMMARY_PATH
}
else {
    Join-Path $repoRoot "target\\northstar\\udp-release-candidate-certification-summary.json"
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release evidence chain."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-evidence-chain.ps1."
}

$requiredPaths = @(
    $linuxReadinessPath,
    $macosReadinessPath,
    $windowsReadinessPath,
    $linuxStagedPath,
    $macosStagedPath
)

foreach ($requiredPath in $requiredPaths) {
    if (-not (Test-Path $requiredPath)) {
        Fail "Required release-evidence input is missing at $requiredPath."
    }
}

Write-Host "==> Building machine-readable readiness rollout matrix"
& (Join-Path $repoRoot "scripts\\udp-rollout-matrix.ps1") --summary-path $readinessMatrixPath --input $linuxReadinessPath --input $macosReadinessPath --input $windowsReadinessPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> Building machine-readable staged-rollout matrix"
& (Join-Path $repoRoot "scripts\\udp-rollout-matrix.ps1") --summary-path $stagedMatrixPath --input $linuxStagedPath --input $macosStagedPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> Running release-facing evidence chain"
& (Join-Path $repoRoot "scripts\\udp-release-workflow.ps1") --summary-path (Join-Path $repoRoot "target\\northstar\\udp-release-workflow-summary.json") --input $readinessMatrixPath --input $stagedMatrixPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$steps = @(
    "udp-deployment-signoff.ps1",
    "udp-release-prep.ps1",
    "udp-release-candidate-signoff.ps1",
    "udp-release-burn-in.ps1",
    "udp-release-soak.ps1",
    "udp-release-gate.ps1",
    "udp-release-readiness-burndown.ps1",
    "udp-release-stability-signoff.ps1",
    "udp-release-candidate-consolidation.ps1",
    "udp-release-candidate-hardening.ps1",
    "udp-release-candidate-evidence-freeze.ps1",
    "udp-release-candidate-signoff-closure.ps1",
    "udp-release-candidate-stabilization.ps1",
    "udp-release-candidate-readiness.ps1",
    "udp-release-candidate-acceptance.ps1",
    "udp-release-candidate-certification.ps1"
)

foreach ($step in $steps) {
    & (Join-Path $repoRoot "scripts\\$step")
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path $finalSummaryPath)) {
    Fail "UDP release candidate certification summary was not produced at $finalSummaryPath."
}

Write-Host "Northstar UDP release evidence chain completed successfully."
Write-Host "readiness_matrix_summary=$readinessMatrixPath"
Write-Host "staged_matrix_summary=$stagedMatrixPath"
Write-Host "release_candidate_certification_summary=$finalSummaryPath"
