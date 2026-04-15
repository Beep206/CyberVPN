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

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$canonicalSummaryPath = Get-VertaOutputPath $repoRoot "remnawave-supported-upstream-summary.json"
$legacySummaryPath = Get-VertaLegacyOutputPath $repoRoot "remnawave-supported-upstream-summary.json"
$summaryPath = if ($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH
} elseif ($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH
} else {
    $canonicalSummaryPath
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the supported-upstream verification wrapper."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-verify.ps1."
}

$shouldMirrorDefault = $false
if (-not $WorkflowArgs -or $WorkflowArgs.Count -eq 0) {
    $WorkflowArgs = @(
        "--summary-path", $summaryPath
    )
    $shouldMirrorDefault = $true
}

Write-Host "==> Running Remnawave supported-upstream verification"
& cargo run -p ns-testkit --example remnawave_supported_upstream_verification -- @WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
if ($shouldMirrorDefault) {
    Copy-VertaCanonicalOutputToLegacy -ActualPath $summaryPath -CanonicalDefaultPath $canonicalSummaryPath -LegacyDefaultPath $legacySummaryPath
}
