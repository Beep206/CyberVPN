[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$transitionDelaySeconds = if ($env:NORTHSTAR_SUPPORTED_UPSTREAM_DISABLE_DELAY_SECONDS) {
    [int]$env:NORTHSTAR_SUPPORTED_UPSTREAM_DISABLE_DELAY_SECONDS
} else {
    2
}

Write-Host "==> Running operator profile-disable drill"
& "$PSScriptRoot\\with-local-remnawave-supported-upstream-env.ps1" powershell -NoProfile -ExecutionPolicy Bypass -Command @'
param(
    [string]$ScriptRoot,
    [int]$TransitionDelaySeconds,
    [string[]]$WorkflowArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

& "$ScriptRoot\\ensure-local-remnawave-supported-upstream-user-active.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$job = Start-Job -ScriptBlock {
    param($ScriptRoot, $TransitionDelaySeconds)
    Set-StrictMode -Version Latest
    $ErrorActionPreference = "Stop"
    Start-Sleep -Seconds $TransitionDelaySeconds
    & "$ScriptRoot\\ensure-local-remnawave-supported-upstream-user-disabled.ps1"
    exit $LASTEXITCODE
} -ArgumentList $ScriptRoot, $TransitionDelaySeconds

& "$ScriptRoot\\remnawave-supported-upstream-lifecycle-verify.ps1" @WorkflowArgs
$exitCode = $LASTEXITCODE
Wait-Job $job | Out-Null
Receive-Job $job | Out-Null
Remove-Job $job -Force | Out-Null
if ($exitCode -ne 0) {
    exit $exitCode
}
'@ -ScriptRoot $PSScriptRoot -TransitionDelaySeconds $transitionDelaySeconds -WorkflowArgs $WorkflowArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
