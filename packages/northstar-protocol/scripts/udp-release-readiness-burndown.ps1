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
$summaryPath = if ($env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_PATH) { $env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_SUMMARY_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-readiness-burndown-summary.json" }
$releaseGatePath = if ($env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_RELEASE_GATE_PATH) { $env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_RELEASE_GATE_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-release-gate-summary.json" }
$linuxReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_LINUX_READINESS_PATH) { $env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_LINUX_READINESS_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-linux.json" }
$macosReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_MACOS_READINESS_PATH) { $env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_MACOS_READINESS_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-macos.json" }
$windowsReadinessPath = if ($env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_WINDOWS_READINESS_PATH) { $env:NORTHSTAR_UDP_RELEASE_READINESS_BURNDOWN_WINDOWS_READINESS_PATH } else { Join-Path $repoRoot "target\\northstar\\udp-rollout-comparison-summary-windows.json" }

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP release-readiness burn-down wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-readiness-burndown.ps1."
}

if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath,
        "--release-gate", $releaseGatePath,
        "--linux-readiness", $linuxReadinessPath,
        "--macos-readiness", $macosReadinessPath,
        "--windows-readiness", $windowsReadinessPath
    )
}

Write-Host "==> Running machine-readable UDP release-readiness burn-down"
& cargo run -p ns-testkit --example udp_release_readiness_burndown -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
