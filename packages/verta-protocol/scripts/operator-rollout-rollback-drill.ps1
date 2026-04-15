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
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "operator-rollout-rollback-drill-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "operator-rollout-rollback-drill-summary.json"
$summaryPath = if ($env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_SUMMARY_PATH) { $env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_SUMMARY_PATH } elseif ($env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_SUMMARY_PATH) { $env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_SUMMARY_PATH } elseif ($env:VERTA_UDP_NET_CHAOS_SUMMARY_PATH) { $env:VERTA_UDP_NET_CHAOS_SUMMARY_PATH } elseif ($env:VERTA_UDP_NET_CHAOS_SUMMARY_PATH) { $env:VERTA_UDP_NET_CHAOS_SUMMARY_PATH } else { $canonicalSummaryPath }
$artifactRoot = if ($env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_ARTIFACT_ROOT) { $env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_ARTIFACT_ROOT } elseif ($env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_ARTIFACT_ROOT) { $env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_ARTIFACT_ROOT } elseif ($env:VERTA_UDP_NET_CHAOS_ARTIFACT_ROOT) { $env:VERTA_UDP_NET_CHAOS_ARTIFACT_ROOT } elseif ($env:VERTA_UDP_NET_CHAOS_ARTIFACT_ROOT) { $env:VERTA_UDP_NET_CHAOS_ARTIFACT_ROOT } else { Get-VertaOutputPath $repoRoot "operator-rollback-drill" }
$deploymentLabel = if ($env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_DEPLOYMENT_LABEL) { $env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_DEPLOYMENT_LABEL } elseif ($env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_DEPLOYMENT_LABEL) { $env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_DEPLOYMENT_LABEL } elseif ($env:VERTA_UDP_NET_CHAOS_DEPLOYMENT_LABEL) { $env:VERTA_UDP_NET_CHAOS_DEPLOYMENT_LABEL } elseif ($env:VERTA_UDP_NET_CHAOS_DEPLOYMENT_LABEL) { $env:VERTA_UDP_NET_CHAOS_DEPLOYMENT_LABEL } else { "operator-rollback-drill" }
$hostLabel = if ($env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_HOST_LABEL) { $env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_HOST_LABEL } elseif ($env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_HOST_LABEL) { $env:VERTA_OPERATOR_ROLLOUT_ROLLBACK_DRILL_HOST_LABEL } elseif ($env:VERTA_UDP_NET_CHAOS_HOST_LABEL) { $env:VERTA_UDP_NET_CHAOS_HOST_LABEL } elseif ($env:VERTA_UDP_NET_CHAOS_HOST_LABEL) { $env:VERTA_UDP_NET_CHAOS_HOST_LABEL } else { "local-operator" }

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
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/operator-rollout-rollback-drill.ps1."
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

$shouldMirrorDefault = $false
if (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs += @("--summary-path", $summaryPath)
    $shouldMirrorDefault = $true
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
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
