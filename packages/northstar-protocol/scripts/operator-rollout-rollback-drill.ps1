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
$summaryPath = if ($env:NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_SUMMARY_PATH) { $env:NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\operator-rollout-rollback-drill-summary.json" }
$artifactRoot = if ($env:NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_ARTIFACT_ROOT) { $env:NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_ARTIFACT_ROOT } else { Join-Path $repoRoot "target\\northstar\\operator-rollback-drill" }
$deploymentLabel = if ($env:NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_DEPLOYMENT_LABEL) { $env:NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_DEPLOYMENT_LABEL } else { "operator-rollback-drill" }
$hostLabel = if ($env:NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_HOST_LABEL) { $env:NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_HOST_LABEL } else { "local-operator" }

if ($env:NORTHSTAR_UDP_NET_CHAOS_SUMMARY_PATH) {
    $summaryPath = $env:NORTHSTAR_UDP_NET_CHAOS_SUMMARY_PATH
}
if ($env:NORTHSTAR_UDP_NET_CHAOS_ARTIFACT_ROOT) {
    $artifactRoot = $env:NORTHSTAR_UDP_NET_CHAOS_ARTIFACT_ROOT
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the operator rollback drill wrapper."
}

if (-not (Get-Command unshare -ErrorAction SilentlyContinue)) {
    Fail "unshare was not found. Install util-linux before running the operator rollback drill wrapper."
}

if (-not (Get-Command tc -ErrorAction SilentlyContinue)) {
    Fail "tc was not found. Install iproute2 before running the operator rollback drill wrapper."
}

if (-not (Get-Command tcpdump -ErrorAction SilentlyContinue)) {
    Fail "tcpdump was not found. Install tcpdump before running the operator rollback drill wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/operator-rollout-rollback-drill.ps1."
}

if (-not $WorkflowArgs) {
    $WorkflowArgs = @()
}

if (-not ($WorkflowArgs -contains "--all")) {
    $hasProfile = $false
    for ($i = 0; $i -lt $WorkflowArgs.Count; $i++) {
        $value = $WorkflowArgs[$i]
        if ($value -in @("--summary-path", "--artifact-root", "--deployment-label", "--host-label", "--format")) {
            $i++
            continue
        }
        if (-not $value.StartsWith("-")) {
            $hasProfile = $true
            break
        }
    }
    if (-not $hasProfile) {
        $WorkflowArgs = @("--profile", "udp-blocked") + $WorkflowArgs
    }
}

if (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs += @("--summary-path", $summaryPath)
}
if (-not ($WorkflowArgs -contains "--artifact-root")) {
    $WorkflowArgs += @("--artifact-root", $artifactRoot)
}
if (-not ($WorkflowArgs -contains "--deployment-label")) {
    $WorkflowArgs += @("--deployment-label", $deploymentLabel)
}
if (-not ($WorkflowArgs -contains "--host-label")) {
    $WorkflowArgs += @("--host-label", $hostLabel)
}

Write-Host "==> Running operator rollout rollback drill"
& cargo run -p ns-testkit --example udp_net_chaos_campaign -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
