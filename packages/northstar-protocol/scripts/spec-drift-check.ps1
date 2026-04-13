[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$indexPath = Join-Path $repoRoot "docs\spec\INDEX.md"

$expectedDocs = @(
    "docs/spec/adaptive_proxy_vpn_protocol_master_plan.md",
    "docs/spec/northstar_blueprint_v0.md",
    "docs/spec/northstar_wire_format_freeze_candidate_v0_1.md",
    "docs/spec/northstar_remnawave_bridge_spec_v0_1.md",
    "docs/spec/northstar_threat_model_v0_1.md",
    "docs/spec/northstar_security_test_and_interop_plan_v0_1.md",
    "docs/spec/northstar_implementation_spec_rust_workspace_plan_v0_1.md",
    "docs/spec/northstar_protocol_rfc_draft_v0_1.md"
)

if (-not (Test-Path $indexPath)) {
    Fail "Spec index not found at $indexPath."
}

$indexContent = Get-Content $indexPath -Raw
$missingFiles = @()
$unindexedFiles = @()

foreach ($doc in $expectedDocs) {
    $absolutePath = Join-Path $repoRoot $doc
    if (-not (Test-Path $absolutePath)) {
        $missingFiles += $doc
    }

    $leafName = Split-Path $doc -Leaf
    if ($indexContent -notmatch [regex]::Escape($leafName)) {
        $unindexedFiles += $doc
    }
}

if ($missingFiles.Count -gt 0) {
    Fail ("Missing authoritative spec files:`n- " + ($missingFiles -join "`n- "))
}

if ($unindexedFiles.Count -gt 0) {
    Fail ("Spec index is missing entries for:`n- " + ($unindexedFiles -join "`n- "))
}

if (-not (Test-Path (Join-Path $repoRoot "Cargo.toml"))) {
    Write-Host "Authoritative specs are present and indexed."
    Write-Host "Deep code-vs-spec drift checks are not active yet because the Rust workspace has not been bootstrapped."
    exit 0
}

Write-Host "Authoritative specs are present and indexed."
Write-Warning "This script currently performs baseline spec presence checks only. Extend it with code-vs-spec assertions once production crates exist."
