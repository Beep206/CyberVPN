[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "VertaCompat.ps1")

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$fuzzRoot = Join-Path $repoRoot "fuzz\\cargo-fuzz"
$isWindowsHost = $env:OS -eq "Windows_NT"
Sync-VertaRolloutReadinessEnv
$canonicalDefaultSummaryPath = Get-VertaOutputPath $repoRoot "udp-active-fuzz-summary.json"
$legacyDefaultSummaryPath = Get-VertaLegacyOutputPath $repoRoot "udp-active-fuzz-summary.json"
$summaryPath = if ($env:VERTA_UDP_ACTIVE_FUZZ_SUMMARY_PATH) {
    $env:VERTA_UDP_ACTIVE_FUZZ_SUMMARY_PATH
}
else {
    $canonicalDefaultSummaryPath
}
$fuzzSeconds = if ($env:VERTA_UDP_ACTIVE_FUZZ_SECONDS) {
    [int]$env:VERTA_UDP_ACTIVE_FUZZ_SECONDS
}
else {
    15
}
$fuzzSanitizer = if ($env:VERTA_UDP_ACTIVE_FUZZ_SANITIZER) {
    $env:VERTA_UDP_ACTIVE_FUZZ_SANITIZER
}
else {
    "none"
}

if ($fuzzSeconds -le 0) {
    Fail "VERTA_UDP_ACTIVE_FUZZ_SECONDS must be a positive integer. The legacy VERTA_UDP_ACTIVE_FUZZ_SECONDS alias remains accepted during migration."
}

if ($fuzzSanitizer -notin @("none", "address")) {
    Fail "VERTA_UDP_ACTIVE_FUZZ_SANITIZER must be either 'none' or 'address'. The legacy VERTA_UDP_ACTIVE_FUZZ_SANITIZER alias remains accepted during migration."
}

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running the UDP active fuzz gate."
}

if (-not (Get-Command cargo-fuzz -ErrorAction SilentlyContinue)) {
    Fail "cargo-fuzz was not found. Install it with `cargo install cargo-fuzz` before enabling the UDP active fuzz gate."
}

if ($isWindowsHost) {
    Fail "the opt-in active UDP cargo-fuzz lane is not supported on the current Windows MSVC path. Use scripts\\fuzz-udp-smoke.ps1 locally, or run the compatible-host active-fuzz lane from scripts/fuzz-udp-active.sh or .github/workflows/udp-optional-gates.yml."
}

& cargo +nightly --version *> $null
if ($LASTEXITCODE -ne 0) {
    Fail "the nightly Rust toolchain was not found. Install it with `rustup toolchain install nightly --profile minimal` before enabling the UDP active fuzz gate."
}

Write-Host "==> Synchronizing reviewed UDP fuzz corpora"
& cargo run -p ns-testkit --example sync_udp_fuzz_corpus
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> Replaying the reviewed UDP fuzz smoke corpus"
& cargo run -p ns-testkit --example udp_fuzz_smoke
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$summaryDir = Split-Path -Parent $summaryPath
if ($summaryDir) {
    New-Item -ItemType Directory -Path $summaryDir -Force | Out-Null
}
$results = @()

Push-Location $fuzzRoot
try {
    foreach ($target in @("control_frame_decoder", "udp_fallback_frame_decoder", "udp_datagram_decoder")) {
        $corpusDir = Join-Path $fuzzRoot "corpus\\$target"
        Write-Host "==> Running active UDP fuzz target $target for $fuzzSeconds seconds with sanitizer $fuzzSanitizer"
        & cargo +nightly fuzz run --fuzz-dir $fuzzRoot --sanitizer $fuzzSanitizer $target $corpusDir -- "-max_total_time=$fuzzSeconds"
        $exitCode = $LASTEXITCODE
        $results += [pscustomobject]@{
            target      = $target
            seconds     = $fuzzSeconds
            sanitizer   = $fuzzSanitizer
            corpus_path = $corpusDir
            exit_code   = $exitCode
            status      = if ($exitCode -eq 0) { "passed" } else { "failed" }
        }
        if ($exitCode -ne 0) {
            break
        }
    }
}
finally {
    Pop-Location
}

([pscustomobject]@{
        summary_version = 1
        seconds         = $fuzzSeconds
        sanitizer       = $fuzzSanitizer
        all_passed      = -not ($results | Where-Object { $_.exit_code -ne 0 })
        results         = $results
    } | ConvertTo-Json -Depth 5) | Set-Content -Path $summaryPath

if ($results | Where-Object { $_.exit_code -ne 0 }) {
    exit (($results | Where-Object { $_.exit_code -ne 0 } | Select-Object -First 1).exit_code)
}

Copy-VertaCanonicalOutputToLegacy $summaryPath $canonicalDefaultSummaryPath $legacyDefaultSummaryPath

Write-Host "Verta UDP active fuzz gate completed successfully."
Write-Host "machine_readable_summary=$summaryPath"
