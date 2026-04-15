[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceManifest = Join-Path $repoRoot "Cargo.toml"
$isWindowsHost = $env:OS -eq "Windows_NT"

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running repository checks."
}

if (-not (Test-Path $workspaceManifest)) {
    Fail "No root Cargo.toml was found at $workspaceManifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/check.ps1."
}

$checks = @(
    @{ Name = "cargo fmt"; Args = @("fmt", "--all", "--check") },
    @{ Name = "cargo clippy"; Args = @("clippy", "--workspace", "--all-targets", "--all-features", "--", "-D", "warnings") },
    @{ Name = "cargo test"; Args = @("test", "--workspace", "--all-targets", "--all-features") }
)

foreach ($check in $checks) {
    Write-Host "==> Running $($check.Name)"
    & cargo @($check.Args)
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($env:VERTA_ENABLE_UDP_FUZZ_SMOKE -eq "1") {
    Write-Host "==> Running optional UDP fuzz smoke gate"
    & cargo run -p ns-testkit --example sync_udp_fuzz_corpus
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    & cargo run -p ns-testkit --example udp_fuzz_smoke
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($env:VERTA_ENABLE_UDP_ACTIVE_FUZZ -eq "1") {
    if ($isWindowsHost) {
        Write-Host "==> Skipping optional UDP active fuzz gate on the Windows-first local path"
        Write-Host "    Use scripts\\fuzz-udp-smoke.ps1 locally, or the compatible-host active-fuzz lane for cargo-fuzz."
    }
    else {
        Write-Host "==> Running optional UDP active fuzz gate"
        & (Join-Path $repoRoot "scripts\\fuzz-udp-active.ps1")
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}

if ($env:VERTA_ENABLE_UDP_PERF_GATE -eq "1") {
    Write-Host "==> Running optional UDP performance gate"
    & cargo run -p ns-testkit --example udp_perf_gate
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($env:VERTA_ENABLE_UDP_WAN_LAB -eq "1") {
    Write-Host "==> Running optional UDP WAN-lab verification path"
    & (Join-Path $repoRoot "scripts\\udp-wan-lab.ps1")
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host "All configured checks completed successfully."
