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
$summaryPath = if ($env:NORTHSTAR_UDP_NET_CHAOS_SUMMARY_PATH) { $env:NORTHSTAR_UDP_NET_CHAOS_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-net-chaos-campaign-summary.json" }
$artifactRoot = if ($env:NORTHSTAR_UDP_NET_CHAOS_ARTIFACT_ROOT) { $env:NORTHSTAR_UDP_NET_CHAOS_ARTIFACT_ROOT } else { Join-Path $repoRoot "target\\northstar\\net-chaos" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP net-chaos wrapper."
}

if (-not (Get-Command unshare -ErrorAction SilentlyContinue)) {
    Fail "unshare was not found. Install util-linux before running the UDP net-chaos wrapper."
}

if (-not (Get-Command tc -ErrorAction SilentlyContinue)) {
    Fail "tc was not found. Install iproute2 before running the UDP net-chaos wrapper."
}

if (-not (Get-Command tcpdump -ErrorAction SilentlyContinue)) {
    Fail "tcpdump was not found. Install tcpdump before running the UDP net-chaos wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-net-chaos-campaign.ps1."
}

if (-not $WorkflowArgs) {
    $WorkflowArgs = @()
}

if (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs += @("--summary-path", $summaryPath)
}

if (-not ($WorkflowArgs -contains "--artifact-root")) {
    $WorkflowArgs += @("--artifact-root", $artifactRoot)
}

Write-Host "==> Running machine-readable UDP net-chaos campaign"
& cargo run -p ns-testkit --example udp_net_chaos_campaign -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
