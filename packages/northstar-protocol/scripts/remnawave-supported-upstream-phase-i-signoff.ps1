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

function Invoke-Lane([string]$Label, [string]$ExpectedSummaryPath, [string[]]$CargoArgs) {
    Write-Host "==> Running $Label"
    if (Test-Path $ExpectedSummaryPath) {
        Remove-Item -LiteralPath $ExpectedSummaryPath -Force
    }
    & cargo @CargoArgs
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and -not (Test-Path $ExpectedSummaryPath)) {
        exit $exitCode
    }
    if ($exitCode -ne 0) {
        Write-Host "   Lane returned non-ready status; continuing because $ExpectedSummaryPath exists."
    }
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$upstreamSummaryPath = if ($env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH) {
    $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH
} else {
    Join-Path $repoRoot "target\northstar\remnawave-supported-upstream-summary.json"
}
$lifecycleSummaryPath = if ($env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH) {
    $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH
} else {
    Join-Path $repoRoot "target\northstar\remnawave-supported-upstream-lifecycle-summary.json"
}
$deploymentRealitySummaryPath = if ($env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH) {
    $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH
} else {
    Join-Path $repoRoot "target\northstar\remnawave-supported-upstream-deployment-reality-summary.json"
}
$phaseISummaryPath = if ($env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_PHASE_I_SIGNOFF_SUMMARY_PATH) {
    $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_PHASE_I_SIGNOFF_SUMMARY_PATH
} else {
    Join-Path $repoRoot "target\northstar\remnawave-supported-upstream-phase-i-signoff-summary.json"
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the supported-upstream Phase I signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-phase-i-signoff.ps1."
}

& "$PSScriptRoot\\with-local-remnawave-supported-upstream-env.ps1" powershell -NoProfile -ExecutionPolicy Bypass -Command @'
param(
    [string]$RepoRoot,
    [string]$UpstreamSummaryPath,
    [string]$LifecycleSummaryPath,
    [string]$DeploymentRealitySummaryPath,
    [string]$PhaseISummaryPath,
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Lane([string]$Label, [string]$ExpectedSummaryPath, [string[]]$CargoArgs) {
    Write-Host "==> Running $Label"
    if (Test-Path $ExpectedSummaryPath) {
        Remove-Item -LiteralPath $ExpectedSummaryPath -Force
    }
    & cargo @CargoArgs
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and -not (Test-Path $ExpectedSummaryPath)) {
        exit $exitCode
    }
    if ($exitCode -ne 0) {
        Write-Host "   Lane returned non-ready status; continuing because $ExpectedSummaryPath exists."
    }
}

& "$RepoRoot\\scripts\\ensure-local-remnawave-supported-upstream-user-active.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Invoke-Lane "Remnawave supported-upstream verification" $UpstreamSummaryPath @(
    "run", "-p", "ns-testkit", "--example", "remnawave_supported_upstream_verification", "--",
    "--summary-path", $UpstreamSummaryPath
)

& "$RepoRoot\\scripts\\operator-profile-disable-drill.ps1" --summary-path $LifecycleSummaryPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& "$RepoRoot\\scripts\\ensure-local-remnawave-supported-upstream-user-active.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Invoke-Lane "Remnawave supported-upstream deployment-reality verification" $DeploymentRealitySummaryPath @(
    "run", "-p", "ns-testkit", "--example", "remnawave_supported_upstream_deployment_reality_verification", "--",
    "--summary-path", $DeploymentRealitySummaryPath,
    "--supported-upstream-summary", $UpstreamSummaryPath,
    "--supported-upstream-lifecycle-summary", $LifecycleSummaryPath
)

$signoffArgs = @(
    "--summary-path", $PhaseISummaryPath,
    "--upstream-summary-path", $UpstreamSummaryPath,
    "--lifecycle-summary-path", $LifecycleSummaryPath,
    "--deployment-reality-summary-path", $DeploymentRealitySummaryPath
)
if ($WorkflowArgs -and $WorkflowArgs.Count -gt 0) {
    $signoffArgs += $WorkflowArgs
}

$phaseICargoArgs = @(
    "run", "-p", "ns-testkit", "--example", "remnawave_supported_upstream_phase_i_signoff", "--"
) + $signoffArgs
Invoke-Lane "Remnawave supported-upstream Phase I signoff" $PhaseISummaryPath $phaseICargoArgs
'@ -RepoRoot $repoRoot -UpstreamSummaryPath $upstreamSummaryPath -LifecycleSummaryPath $lifecycleSummaryPath -DeploymentRealitySummaryPath $deploymentRealitySummaryPath -PhaseISummaryPath $phaseISummaryPath -WorkflowArgs $WorkflowArgs

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
