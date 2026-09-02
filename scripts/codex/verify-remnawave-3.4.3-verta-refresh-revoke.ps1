param(
    [string]$EvidencePath,
    [string]$CargoPath = 'cargo'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
    $EvidencePath = Join-Path $repositoryRoot 'docs\evidence\remnawave-3.4.3\verta-refresh-revoke.json'
}
$manifestPath = Join-Path $repositoryRoot 'packages\verta-protocol\Cargo.toml'
$results = [System.Collections.Generic.List[object]]::new()

function Invoke-VertaCase {
    param(
        [string]$Name,
        [string[]]$ArgumentList
    )

    $rawOutput = (& $CargoPath @ArgumentList 2>&1 | Out-String).Trim()
    $exitCode = $LASTEXITCODE
    $results.Add([ordered]@{
        name = $Name
        command = (($CargoPath + ' ' + ($ArgumentList -join ' ')).Replace($repositoryRoot, '<repo>'))
        workingDirectory = '<repo>'
        exitCode = $exitCode
        passed = $exitCode -eq 0
        output = $rawOutput.Replace($repositoryRoot, '<repo>')
    })
}

Push-Location $repositoryRoot
try {
    Invoke-VertaCase 'bridge-refresh-and-unknown-field-fixtures' @(
        'test', '--manifest-path', $manifestPath, '-p', 'ns-bridge-api', '--test', 'bridge_fixtures'
    )
    Invoke-VertaCase 'revoked-token-subject-fixture' @(
        'test', '--manifest-path', $manifestPath, '-p', 'ns-auth', '--test', 'token_fixtures',
        'rejects_revoked_subject_fixture'
    )
    Invoke-VertaCase 'revoked-device-after-durable-reopen' @(
        'test', '--manifest-path', $manifestPath, '-p', 'ns-bridge-domain', '--test',
        'shared_store_replay_and_policy', 'revoked_device_blocks_token_exchange_after_reopen'
    )
    Invoke-VertaCase 'refresh-manifest-binding-after-durable-reopen' @(
        'test', '--manifest-path', $manifestPath, '-p', 'ns-bridge-domain', '--test',
        'shared_store_replay_and_policy', 'refresh_credential_manifest_binding_survives_reopen'
    )
    Invoke-VertaCase 'revoked-refresh-credential-token-exchange' @(
        'test', '--manifest-path', $manifestPath, '-p', 'ns-bridge-domain',
        'rejects_revoked_refresh_credential_during_token_exchange'
    )
}
finally {
    Pop-Location
}

$evidence = [ordered]@{
    schemaVersion = 1
    generatedAtUtc = [DateTimeOffset]::UtcNow.ToString('o')
    scope = 'Local deterministic Verta refresh/revoke fixtures only; no live service, staging, production, or network connection claim is made.'
    results = $results
}
$evidenceDirectory = Split-Path -Parent $EvidencePath
[System.IO.Directory]::CreateDirectory($evidenceDirectory) | Out-Null
[System.IO.File]::WriteAllText(
    $EvidencePath,
    ($evidence | ConvertTo-Json -Depth 20) + [Environment]::NewLine
)

$failed = @($results | Where-Object { -not $_.passed })
if ($failed.Count -gt 0) {
    throw "Verta refresh/revoke verification failed: $($failed.name -join ', '). Evidence: $EvidencePath"
}

Write-Output "Verta refresh/revoke verification passed: $($results.Count) cases."
Write-Output "Evidence: $EvidencePath"
