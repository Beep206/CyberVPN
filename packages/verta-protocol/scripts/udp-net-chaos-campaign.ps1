[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "VertaCompat.ps1")

Sync-VertaPhaseJEnv

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "udp-net-chaos-campaign-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-net-chaos-campaign-summary.json"
$summaryPath = if ($env:VERTA_UDP_NET_CHAOS_SUMMARY_PATH) { $env:VERTA_UDP_NET_CHAOS_SUMMARY_PATH } else { $canonicalSummaryPath }
$artifactRoot = if ($env:VERTA_UDP_NET_CHAOS_ARTIFACT_ROOT) { $env:VERTA_UDP_NET_CHAOS_ARTIFACT_ROOT } else { Get-VertaOutputPath $repoRoot "net-chaos" }

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
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-net-chaos-campaign.ps1."
}

if (-not $WorkflowArgs) {
    $WorkflowArgs = @()
}

$shouldMirrorDefault = $false
if (-not ($WorkflowArgs -contains "--summary-path")) {
    $WorkflowArgs += @("--summary-path", $summaryPath)
    $shouldMirrorDefault = $true
}

if (-not ($WorkflowArgs -contains "--artifact-root")) {
    $WorkflowArgs += @("--artifact-root", $artifactRoot)
}

Write-Host "==> Running machine-readable UDP net-chaos campaign"
& cargo run -p ns-testkit --example udp_net_chaos_campaign -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
