[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "VertaCompat.ps1")

Sync-VertaPhaseIEnv

$transitionDelaySeconds = if ($env:VERTA_SUPPORTED_UPSTREAM_DISABLE_DELAY_SECONDS) {
    [int]$env:VERTA_SUPPORTED_UPSTREAM_DISABLE_DELAY_SECONDS
} else {
    2
}

function Test-HaveSupportedUpstreamEnv {
    return `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE) -and `
        -not [string]::IsNullOrWhiteSpace($env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID)
}

Write-Host "==> Running operator profile-disable drill"
if (-not (Test-HaveSupportedUpstreamEnv)) {
    & "$PSScriptRoot\\with-local-remnawave-supported-upstream-env.ps1" `
        powershell -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath @WorkflowArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    exit 0
}

if (-not [string]::IsNullOrWhiteSpace($env:VERTA_SUPPORTED_UPSTREAM_DISABLE_COMMAND)) {
    if (-not [string]::IsNullOrWhiteSpace($env:VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND)) {
        Invoke-Expression $env:VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
}
else {
    & "$PSScriptRoot\\ensure-local-remnawave-supported-upstream-user-active.ps1"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$job = Start-Job -ScriptBlock {
    param($ScriptRoot, $TransitionDelaySeconds, $DisableCommand)
    Set-StrictMode -Version Latest
    $ErrorActionPreference = "Stop"
    Start-Sleep -Seconds $TransitionDelaySeconds
    if (-not [string]::IsNullOrWhiteSpace($DisableCommand)) {
        Invoke-Expression $DisableCommand
    }
    else {
        & "$ScriptRoot\\ensure-local-remnawave-supported-upstream-user-disabled.ps1"
    }
    exit $LASTEXITCODE
} -ArgumentList $PSScriptRoot, $transitionDelaySeconds, $env:VERTA_SUPPORTED_UPSTREAM_DISABLE_COMMAND

& "$PSScriptRoot\\remnawave-supported-upstream-lifecycle-verify.ps1" @WorkflowArgs
$exitCode = $LASTEXITCODE
Wait-Job $job | Out-Null
Receive-Job $job | Out-Null
Remove-Job $job -Force | Out-Null
if ($exitCode -ne 0) {
    exit $exitCode
}
