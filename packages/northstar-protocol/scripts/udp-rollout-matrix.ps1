[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$MatrixArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP rollout matrix wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-rollout-matrix.ps1."
}

if ($MatrixArgs.Count -eq 0) {
    Fail "Usage: .\\scripts\\udp-rollout-matrix.ps1 --summary-path <path> --input <comparison-summary-path> [--input <comparison-summary-path> ...]"
}

Write-Host "==> Running machine-readable UDP rollout matrix"
& cargo run -p ns-testkit --example udp_rollout_matrix -- @MatrixArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
