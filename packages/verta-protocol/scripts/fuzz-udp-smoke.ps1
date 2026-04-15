[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)

if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    Fail "cargo was not found. Install the Rust stable toolchain before running UDP fuzz smoke checks."
}

Push-Location $repoRoot
try {
    Write-Host "==> Synchronizing UDP fuzz corpus"
    cargo run -p ns-testkit --example sync_udp_fuzz_corpus
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Host "==> Replaying UDP fuzz smoke seeds"
    cargo run -p ns-testkit --example udp_fuzz_smoke
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Host "UDP fuzz smoke checks completed successfully."
