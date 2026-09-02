param(
    [string]$EvidencePath,
    [string]$CargoPath = 'cargo',
    [string]$NodePath = 'node',
    [string]$NpmPath = 'npm.cmd'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
    $EvidencePath = Join-Path $repositoryRoot 'docs\evidence\remnawave-3.4.3\desktop-gates.json'
}
$manifestPath = Join-Path $repositoryRoot 'apps\desktop-client\src-tauri\Cargo.toml'
$results = [System.Collections.Generic.List[object]]::new()

function Invoke-DesktopGate {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$ArgumentList
    )

    $rawOutput = (& $Executable @ArgumentList 2>&1 | Out-String).Trim()
    $exitCode = $LASTEXITCODE
    $redactedOutput = $rawOutput.Replace($repositoryRoot, '<repo>')
    $displayArguments = @($ArgumentList | ForEach-Object {
        $_.Replace($repositoryRoot, '<repo>')
    })
    $results.Add([ordered]@{
        name = $Name
        command = (($Executable + ' ' + ($displayArguments -join ' ')).Trim())
        workingDirectory = '<repo>'
        exitCode = $exitCode
        passed = $exitCode -eq 0
        output = $redactedOutput
    })
}

Push-Location $repositoryRoot
try {
    Invoke-DesktopGate 'desktop-rustfmt' $CargoPath @(
        'fmt', '--manifest-path', $manifestPath, '--all', '--', '--check'
    )
    Invoke-DesktopGate 'desktop-clippy' $CargoPath @(
        'clippy', '--locked', '--manifest-path', $manifestPath, '--all-targets', '--all-features', '--', '-D', 'warnings'
    )
    Invoke-DesktopGate 'desktop-rust-tests' $CargoPath @(
        'test', '--locked', '--manifest-path', $manifestPath, '--all-features'
    )
    if ($IsWindows) {
        Invoke-DesktopGate 'desktop-native-keyring-persistence' $CargoPath @(
            'test', '--locked', '--manifest-path', $manifestPath,
            'engine::subscription::tests::native_windows_keyring_persists_across_processes_and_deletes',
            '--', '--nocapture'
        )
    }
    Invoke-DesktopGate 'desktop-unit-tests' $NpmPath @(
        'run', 'test:unit', '-w', 'apps/desktop-client'
    )
    Invoke-DesktopGate 'desktop-typescript' $NodePath @(
        'apps/desktop-client/node_modules/typescript/bin/tsc',
        '--noEmit',
        '-p',
        'apps/desktop-client/tsconfig.json'
    )
    Invoke-DesktopGate 'desktop-production-build' $NpmPath @(
        'run', 'build', '-w', 'apps/desktop-client'
    )
}
finally {
    Pop-Location
}

$evidence = [ordered]@{
    schemaVersion = 1
    generatedAtUtc = [DateTimeOffset]::UtcNow.ToString('o')
    scope = 'Final local Desktop/Tauri validation after the Remnawave 3.4.3 protocol and subscription hardening patch; native live-connect and packaging smoke are not claimed.'
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
    throw "Desktop validation failed: $($failed.name -join ', '). Evidence: $EvidencePath"
}

Write-Output "Desktop validation passed: $($results.Count) gates."
Write-Output "Evidence: $EvidencePath"
