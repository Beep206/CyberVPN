[CmdletBinding()]
param(
    [string]$DesktopBinaryPath = "C:\project\CyberVPN\apps\desktop-client\src-tauri\target\release\desktop-client.exe",
    [string]$ArtifactsRoot = "C:\project\CyberVPN\apps\desktop-client\.artifacts\desktop-internal-beta-smoke",
    [int]$SmokeDelayMs = 1500,
    [int]$TimeoutSeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Wait-File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $Path) {
            return
        }
        Start-Sleep -Milliseconds 200
    }

    throw "Timed out waiting for file: $Path"
}

function Wait-ProcessExit {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $Process.Refresh()
            if ($Process.HasExited) {
                return
            }
        } catch {
            return
        }
        Start-Sleep -Milliseconds 200
    }

    try {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    } catch {
    }

    throw "Smoke process did not exit within timeout: $($Process.Id)"
}

function Read-JsonFile {
    param([Parameter(Mandatory = $true)][string]$Path)
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Start-SmokeProcess {
    param(
        [Parameter(Mandatory = $true)][string]$ExecutablePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$AppDirOverride,
        [Parameter(Mandatory = $true)][string]$LifecycleStatePath,
        [int]$TimeoutSeconds = 30
    )

    $previousOverride = $env:CYBERVPN_APP_DIR_OVERRIDE
    $env:CYBERVPN_APP_DIR_OVERRIDE = $AppDirOverride
    try {
        $process = Start-Process `
            -FilePath $ExecutablePath `
            -ArgumentList $Arguments `
            -PassThru `
            -WindowStyle Hidden `
            -WorkingDirectory (Split-Path -Parent $ExecutablePath)
    } finally {
        if ([string]::IsNullOrWhiteSpace($previousOverride)) {
            Remove-Item Env:CYBERVPN_APP_DIR_OVERRIDE -ErrorAction SilentlyContinue
        } else {
            $env:CYBERVPN_APP_DIR_OVERRIDE = $previousOverride
        }
    }

    Wait-File -Path $LifecycleStatePath -TimeoutSeconds $TimeoutSeconds
    return $process
}

function Get-EventsTail {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [int]$Tail = 25
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return @()
    }

    return @(Get-Content -LiteralPath $Path -Tail $Tail)
}

function New-StepResult {
    param(
        [Parameter(Mandatory = $true)][string]$Step,
        [Parameter(Mandatory = $true)]$LifecycleState,
        $StartupRecovery
    )

    return [pscustomobject]@{
        step = $Step
        lifecycle = [pscustomobject]@{
            current_run_id = $LifecycleState.run_id
            started_at = $LifecycleState.started_at
            launch_mode = $LifecycleState.launch_mode
            clean_shutdown = [bool]$LifecycleState.clean_shutdown
            exit_kind = $LifecycleState.exit_kind
            exit_at = $LifecycleState.exit_at
            exit_message = $LifecycleState.exit_message
        }
        startup_recovery = if ($null -ne $StartupRecovery) {
            [pscustomobject]@{
                current_run_id = $StartupRecovery.current_run_id
                launch_mode = $StartupRecovery.launch_mode
                hidden_launch_requested = [bool]$StartupRecovery.hidden_launch_requested
                previous_unclean_shutdown_detected = [bool]$StartupRecovery.previous_unclean_shutdown_detected
                previous_run_id = $StartupRecovery.previous_run_id
                previous_started_at = $StartupRecovery.previous_started_at
                previous_exit_kind = $StartupRecovery.previous_exit_kind
                previous_exit_at = $StartupRecovery.previous_exit_at
                previous_exit_message = $StartupRecovery.previous_exit_message
                startup_cleanup_performed = [bool]$StartupRecovery.startup_cleanup_performed
                system_proxy_cleanup_succeeded = [bool]$StartupRecovery.system_proxy_cleanup_succeeded
            }
        } else {
            $null
        }
    }
}

New-Item -ItemType Directory -Force -Path $ArtifactsRoot | Out-Null

$resolvedBinaryPath = (Resolve-Path $DesktopBinaryPath).Path
$runId = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $ArtifactsRoot $runId
$appDataDir = Join-Path $runDir "app-data"
$diagnosticsDir = Join-Path $appDataDir "diagnostics"
$lifecycleStatePath = Join-Path $appDataDir "lifecycle-state.json"
$storePath = Join-Path $appDataDir "store.json"
$eventsLogPath = Join-Path $diagnosticsDir "events.jsonl"
$summaryPath = Join-Path $runDir "desktop-internal-beta-smoke-summary.json"

New-Item -ItemType Directory -Force -Path $appDataDir | Out-Null
New-Item -ItemType Directory -Force -Path $diagnosticsDir | Out-Null

$steps = New-Object System.Collections.Generic.List[object]

$firstProcess = Start-SmokeProcess `
    -ExecutablePath $resolvedBinaryPath `
    -Arguments @("--smoke-exit-after-ms", "$SmokeDelayMs") `
    -AppDirOverride $appDataDir `
    -LifecycleStatePath $lifecycleStatePath `
    -TimeoutSeconds $TimeoutSeconds
Wait-ProcessExit -Process $firstProcess -TimeoutSeconds $TimeoutSeconds
$firstLifecycle = Read-JsonFile -Path $lifecycleStatePath
$firstStore = Read-JsonFile -Path $storePath
$steps.Add((New-StepResult -Step "clean-start" -LifecycleState $firstLifecycle -StartupRecovery $firstStore.last_startup_recovery))

$hiddenProcess = Start-SmokeProcess `
    -ExecutablePath $resolvedBinaryPath `
    -Arguments @("--hidden", "--smoke-exit-after-ms", "$SmokeDelayMs") `
    -AppDirOverride $appDataDir `
    -LifecycleStatePath $lifecycleStatePath `
    -TimeoutSeconds $TimeoutSeconds
Wait-ProcessExit -Process $hiddenProcess -TimeoutSeconds $TimeoutSeconds
$hiddenLifecycle = Read-JsonFile -Path $lifecycleStatePath
$hiddenStore = Read-JsonFile -Path $storePath
$steps.Add((New-StepResult -Step "hidden-clean-start" -LifecycleState $hiddenLifecycle -StartupRecovery $hiddenStore.last_startup_recovery))

$crashProcess = Start-SmokeProcess `
    -ExecutablePath $resolvedBinaryPath `
    -Arguments @("--smoke-crash-after-ms", "$SmokeDelayMs") `
    -AppDirOverride $appDataDir `
    -LifecycleStatePath $lifecycleStatePath `
    -TimeoutSeconds $TimeoutSeconds
Wait-ProcessExit -Process $crashProcess -TimeoutSeconds $TimeoutSeconds
$crashLifecycle = Read-JsonFile -Path $lifecycleStatePath
$crashStore = Read-JsonFile -Path $storePath
$steps.Add((New-StepResult -Step "crash-start" -LifecycleState $crashLifecycle -StartupRecovery $crashStore.last_startup_recovery))

$recoveryProcess = Start-SmokeProcess `
    -ExecutablePath $resolvedBinaryPath `
    -Arguments @("--smoke-exit-after-ms", "$SmokeDelayMs") `
    -AppDirOverride $appDataDir `
    -LifecycleStatePath $lifecycleStatePath `
    -TimeoutSeconds $TimeoutSeconds
Wait-ProcessExit -Process $recoveryProcess -TimeoutSeconds $TimeoutSeconds
$recoveryLifecycle = Read-JsonFile -Path $lifecycleStatePath
$recoveryStore = Read-JsonFile -Path $storePath
$eventsTail = Get-EventsTail -Path $eventsLogPath
$steps.Add((New-StepResult -Step "post-crash-recovery" -LifecycleState $recoveryLifecycle -StartupRecovery $recoveryStore.last_startup_recovery))

$summary = [pscustomobject]@{
    generatedAt = (Get-Date).ToString("o")
    runId = $runId
    executablePath = $resolvedBinaryPath
    appDataDir = $appDataDir
    lifecycleStatePath = $lifecycleStatePath
    storePath = $storePath
    diagnosticsDir = $diagnosticsDir
    eventsLogPath = $eventsLogPath
    smokeDelayMs = $SmokeDelayMs
    steps = $steps
    validations = [pscustomobject]@{
        cleanStartExitedCleanly = ($firstLifecycle.clean_shutdown -and $firstLifecycle.exit_kind -eq "clean")
        hiddenLaunchWasCaptured = ($hiddenLifecycle.launch_mode -eq "hidden" -and [bool]$hiddenStore.last_startup_recovery.hidden_launch_requested)
        crashRunStayedUnclean = ((-not [bool]$crashLifecycle.clean_shutdown) -and [string]::IsNullOrWhiteSpace([string]$crashLifecycle.exit_kind))
        postCrashDetectedUncleanShutdown = [bool]$recoveryStore.last_startup_recovery.previous_unclean_shutdown_detected
        postCrashPerformedCleanup = [bool]$recoveryStore.last_startup_recovery.startup_cleanup_performed
        diagnosticsContainRecoveryEvent = [bool]($eventsTail -match "Previous desktop session ended uncleanly")
    }
    recentEventsTail = $eventsTail
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath

Write-Host "Desktop internal-beta smoke summary: $summaryPath"
Write-Host "Isolated app dir: $appDataDir"
Write-Host "Clean exit captured: $($summary.validations.cleanStartExitedCleanly)"
Write-Host "Hidden launch captured: $($summary.validations.hiddenLaunchWasCaptured)"
Write-Host "Crash stayed unclean: $($summary.validations.crashRunStayedUnclean)"
Write-Host "Post-crash recovery detected: $($summary.validations.postCrashDetectedUncleanShutdown)"
Write-Host "Post-crash cleanup performed: $($summary.validations.postCrashPerformedCleanup)"
Write-Host "Recovery event present in diagnostics: $($summary.validations.diagnosticsContainRecoveryEvent)"
exit 0
