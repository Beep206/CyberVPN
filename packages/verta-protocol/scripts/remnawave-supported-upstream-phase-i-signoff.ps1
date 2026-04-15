[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "VertaCompat.ps1")

Sync-VertaPhaseIEnv

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

function Test-HaveSupportedUpstreamEnv {
    return `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL)
}

function Invoke-OptionalEnableCommand {
    if (-not [string]::IsNullOrWhiteSpace($env:VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND)) {
        Invoke-Expression $env:VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    elseif ($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL -eq "remnawave-local-docker") {
        & "$PSScriptRoot\\ensure-local-remnawave-supported-upstream-user-active.ps1"
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$canonicalUpstreamSummaryPath = Get-VertaOutputPath $repoRoot "remnawave-supported-upstream-summary.json"
$legacyUpstreamSummaryPath = Get-VertaLegacyOutputPath $repoRoot "remnawave-supported-upstream-summary.json"
$upstreamSummaryPath = if ($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH
} else {
    $canonicalUpstreamSummaryPath
}
$canonicalLifecycleSummaryPath = Get-VertaOutputPath $repoRoot "remnawave-supported-upstream-lifecycle-summary.json"
$legacyLifecycleSummaryPath = Get-VertaLegacyOutputPath $repoRoot "remnawave-supported-upstream-lifecycle-summary.json"
$lifecycleSummaryPath = if ($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH
} else {
    $canonicalLifecycleSummaryPath
}
$canonicalDeploymentRealitySummaryPath = Get-VertaOutputPath $repoRoot "remnawave-supported-upstream-deployment-reality-summary.json"
$legacyDeploymentRealitySummaryPath = Get-VertaLegacyOutputPath $repoRoot "remnawave-supported-upstream-deployment-reality-summary.json"
$deploymentRealitySummaryPath = if ($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH
} else {
    $canonicalDeploymentRealitySummaryPath
}
$canonicalPhaseISummaryPath = Get-VertaOutputPath $repoRoot "remnawave-supported-upstream-phase-i-signoff-summary.json"
$legacyPhaseISummaryPath = Get-VertaLegacyOutputPath $repoRoot "remnawave-supported-upstream-phase-i-signoff-summary.json"
$phaseISummaryPath = if ($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_PHASE_I_SIGNOFF_SUMMARY_PATH) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_PHASE_I_SIGNOFF_SUMMARY_PATH
} else {
    $canonicalPhaseISummaryPath
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the supported-upstream Phase I signoff wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-phase-i-signoff.ps1."
}

if (-not (Test-HaveSupportedUpstreamEnv)) {
    & "$PSScriptRoot\\with-local-remnawave-supported-upstream-env.ps1" `
        powershell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath @WorkflowArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    exit 0
}

Invoke-OptionalEnableCommand

Invoke-Lane "Remnawave supported-upstream verification" $upstreamSummaryPath @(
    "run", "-p", "ns-testkit", "--example", "remnawave_supported_upstream_verification", "--",
    "--summary-path", $upstreamSummaryPath
)
Copy-VertaCanonicalOutputToLegacy -ActualPath $upstreamSummaryPath -CanonicalDefaultPath $canonicalUpstreamSummaryPath -LegacyDefaultPath $legacyUpstreamSummaryPath

& "$PSScriptRoot\\operator-profile-disable-drill.ps1" --summary-path $lifecycleSummaryPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Copy-VertaCanonicalOutputToLegacy -ActualPath $lifecycleSummaryPath -CanonicalDefaultPath $canonicalLifecycleSummaryPath -LegacyDefaultPath $legacyLifecycleSummaryPath

Invoke-OptionalEnableCommand

Invoke-Lane "Remnawave supported-upstream deployment-reality verification" $deploymentRealitySummaryPath @(
    "run", "-p", "ns-testkit", "--example", "remnawave_supported_upstream_deployment_reality_verification", "--",
    "--summary-path", $deploymentRealitySummaryPath,
    "--supported-upstream-summary", $upstreamSummaryPath,
    "--supported-upstream-lifecycle-summary", $lifecycleSummaryPath
)
Copy-VertaCanonicalOutputToLegacy -ActualPath $deploymentRealitySummaryPath -CanonicalDefaultPath $canonicalDeploymentRealitySummaryPath -LegacyDefaultPath $legacyDeploymentRealitySummaryPath

$signoffArgs = @(
    "--summary-path", $phaseISummaryPath,
    "--upstream-summary-path", $upstreamSummaryPath,
    "--lifecycle-summary-path", $lifecycleSummaryPath,
    "--deployment-reality-summary-path", $deploymentRealitySummaryPath
)
if ($WorkflowArgs -and $WorkflowArgs.Count -gt 0) {
    $signoffArgs += $WorkflowArgs
}

$phaseICargoArgs = @(
    "run", "-p", "ns-testkit", "--example", "remnawave_supported_upstream_phase_i_signoff", "--"
) + $signoffArgs
Invoke-Lane "Remnawave supported-upstream Phase I signoff" $phaseISummaryPath $phaseICargoArgs
Copy-VertaCanonicalOutputToLegacy -ActualPath $phaseISummaryPath -CanonicalDefaultPath $canonicalPhaseISummaryPath -LegacyDefaultPath $legacyPhaseISummaryPath
