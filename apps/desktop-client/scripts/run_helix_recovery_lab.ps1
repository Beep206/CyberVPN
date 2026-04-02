param(
    [string]$AdapterUrl = "http://127.0.0.1:8088",
    [string]$InternalToken = "",
    [string]$DesktopBinaryPath = "",
    [ValidateSet("failover", "reconnect")][string]$Mode = "failover",
    [string]$TargetHost = "speed.cloudflare.com",
    [int]$TargetPort = 80,
    [string]$TargetPath = "/__down?bytes=262144",
    [int]$PostRecoveryAttempts = 1,
    [int]$DownloadBytesLimit = 262144,
    [int]$ConnectTimeoutSeconds = 10,
    [int]$StartupTimeoutSeconds = 30,
    [int]$RecoveryTimeoutMilliseconds = 8000,
    [string]$OutputDir = "",
    [string]$ScenarioName = "helix-recovery-lab",
    [switch]$UseSyntheticLabTarget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "helix_lab_common.ps1")

if ($UseSyntheticLabTarget) {
    $TargetHost = Resolve-HelixLabTargetIp
    $TargetPort = 80
    $TargetPath = "/8mb.bin"
    if ($ScenarioName -eq "helix-recovery-lab") {
        $ScenarioName = "helix-recovery-synthetic"
    }
}

$InternalToken = Get-HelixInternalToken -InternalToken $InternalToken
$DesktopBinaryPath = Resolve-HelixDesktopBinaryPath -DesktopBinaryPath $DesktopBinaryPath
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $PSScriptRoot "..\.artifacts\helix-recovery-lab"
}

$session = New-HelixLabSession `
    -AdapterUrl $AdapterUrl `
    -InternalToken $InternalToken `
    -DesktopBinaryPath $DesktopBinaryPath `
    -OutputDir $OutputDir `
    -StartupTimeoutSeconds $StartupTimeoutSeconds `
    -ScenarioName $ScenarioName

try {
    $healthUrl = $session.runtime_config.health_url
    $proxyUrl = $session.runtime_config.proxy_url
    $telemetryUrl = Get-HelixSidecarEndpointUrl -HealthUrl $healthUrl -Path "/telemetry"
    $healthBefore = Get-HelixSidecarJson -Url $healthUrl
    $telemetryBefore = Get-HelixSidecarJson -Url $telemetryUrl
    $warmupProbe = $null
    try {
        $warmupProbe = Invoke-HelixBenchmarkAttempt `
            -ProxyUrl $proxyUrl `
            -TargetHost $TargetHost `
            -TargetPort $TargetPort `
            -TargetPath $TargetPath `
            -Attempt 0 `
            -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
            -DownloadBytesLimit ([Math]::Min($DownloadBytesLimit, 32768))
    } catch {
    }

    $actionStartedAt = [DateTime]::UtcNow
    $actionReport = Invoke-HelixSidecarAction -HealthUrl $healthUrl -Mode $Mode
    $deadline = [DateTime]::UtcNow.AddMilliseconds($RecoveryTimeoutMilliseconds)
    $healthAfter = $null
    $readyRecoveryLatencyMs = $null
    $proxyReadyProbe = $null
    $proxyReadyLatencyMs = $null

    do {
        if ($null -eq $healthAfter) {
            try {
                $candidateHealth = Get-HelixSidecarJson -Url $healthUrl
                if ($candidateHealth.ready -eq $true -or $candidateHealth.status -eq "ready") {
                    $healthAfter = $candidateHealth
                    $readyRecoveryLatencyMs = [Math]::Round(
                        ([DateTime]::UtcNow - $actionStartedAt).TotalMilliseconds,
                        2
                    )
                }
            } catch {
            }
        }

        if ($null -eq $proxyReadyProbe) {
            try {
                $remainingProbeBudgetMs = [Math]::Max(
                    [int]($deadline - [DateTime]::UtcNow).TotalMilliseconds,
                    100
                )
                $proxyReadyProbe = Invoke-HelixBenchmarkAttempt `
                    -ProxyUrl $proxyUrl `
                    -TargetHost $TargetHost `
                    -TargetPort $TargetPort `
                    -TargetPath $TargetPath `
                    -Attempt 1 `
                    -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
                    -DownloadBytesLimit 4096 `
                    -StopAfterFirstBodyByte `
                    -OperationTimeoutMilliseconds ([Math]::Min($remainingProbeBudgetMs, 400))
                $proxyReadyLatencyMs = [Math]::Round(
                    ([DateTime]::UtcNow - $actionStartedAt).TotalMilliseconds,
                    2
                )
            } catch {
            }
        }

        if ($null -ne $healthAfter -and $null -ne $proxyReadyProbe) {
            break
        }

        Start-Sleep -Milliseconds 10
    } while ([DateTime]::UtcNow -lt $deadline)

    if ($null -eq $healthAfter) {
        throw "Helix sidecar health endpoint did not become ready before ${RecoveryTimeoutMilliseconds} ms."
    }

    if ($null -eq $proxyReadyProbe) {
        throw "Helix proxy did not become ready before ${RecoveryTimeoutMilliseconds} ms."
    }

    $standbyHealthAfter = $null
    $standbyRewarmLatencyMs = $null
    if (($healthAfter.route_count | ForEach-Object { [int]$_ }) -gt 1 -and -not [string]::IsNullOrWhiteSpace($healthAfter.active_route_endpoint_ref)) {
        $standbyHealthAfter = Wait-ForHelixStandbyReady `
            -Url $healthUrl `
            -TimeoutMilliseconds $RecoveryTimeoutMilliseconds `
            -ActiveRouteEndpointRef $healthAfter.active_route_endpoint_ref
        if ($null -ne $standbyHealthAfter) {
            $standbyRewarmLatencyMs = [Math]::Round(([DateTime]::UtcNow - $actionStartedAt).TotalMilliseconds, 2)
        }
    }

    $telemetryAfter = Get-HelixSidecarJson -Url $telemetryUrl
    $postRecoveryBenchmark = Invoke-HelixBenchmarkSeries `
        -ProxyUrl $proxyUrl `
        -TargetHost $TargetHost `
        -TargetPort $TargetPort `
        -TargetPath $TargetPath `
        -Attempts ([Math]::Max($PostRecoveryAttempts, 1)) `
        -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
        -DownloadBytesLimit $DownloadBytesLimit

    $healthBeforePath = Join-Path $session.run_dir "helix-health-before.json"
    $healthAfterPath = Join-Path $session.run_dir "helix-health-after.json"
    $telemetryBeforePath = Join-Path $session.run_dir "helix-telemetry-before.json"
    $telemetryAfterPath = Join-Path $session.run_dir "helix-telemetry-after.json"
    $reportPath = Join-Path $session.run_dir "helix-lab-recovery-report.json"

    Write-Utf8NoBomFile -Path $healthBeforePath -Content ($healthBefore | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $healthAfterPath -Content ($healthAfter | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $telemetryBeforePath -Content ($telemetryBefore | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $telemetryAfterPath -Content ($telemetryAfter | ConvertTo-Json -Depth 16)

    $report = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        scenario = $ScenarioName
        mode = $Mode
        adapter_url = $AdapterUrl
        desktop_binary_path = $DesktopBinaryPath
        output_dir = $session.run_dir
        target = [ordered]@{
            host = $TargetHost
            port = $TargetPort
            path = $TargetPath
            post_recovery_attempts = $PostRecoveryAttempts
        }
        manifest = [ordered]@{
            manifest_version_id = $session.manifest_response.manifest_version_id
            rollout_id = $session.manifest_response.manifest.rollout_id
            transport_profile_id = $session.manifest_response.manifest.transport_profile.transport_profile_id
            route_count = @($session.manifest_response.manifest.routes).Count
            routes = $session.manifest_response.manifest.routes
        }
        health_before = $healthBefore
        telemetry_before = $telemetryBefore
        action = $actionReport
        ready_recovery_latency_ms = $readyRecoveryLatencyMs
        proxy_ready_latency_ms = $proxyReadyLatencyMs
        proxy_ready_measurement = "time-to-first-byte-through-socks-probe"
        standby_rewarm_latency_ms = $standbyRewarmLatencyMs
        proxy_ready_probe = $proxyReadyProbe
        health_after = $healthAfter
        health_after_standby_rewarm = $standbyHealthAfter
        telemetry_after = $telemetryAfter
        post_recovery_benchmark = $postRecoveryBenchmark
        warmup_probe = $warmupProbe
        artifacts = [ordered]@{
            runtime_config = $session.runtime_config_path
            manifest = $session.manifest_path
            sidecar_stdout = $session.stdout_path
            sidecar_stderr = $session.stderr_path
            health_before = $healthBeforePath
            health_after = $healthAfterPath
            telemetry_before = $telemetryBeforePath
            telemetry_after = $telemetryAfterPath
        }
    }

    Write-Utf8NoBomFile -Path $reportPath -Content ($report | ConvertTo-Json -Depth 20)
    Write-Host "Helix recovery lab completed."
    Write-Host "Scenario: $ScenarioName"
    Write-Host "Mode: $Mode"
    Write-Host "Report: $reportPath"
    Write-Host "Ready recovery latency: $readyRecoveryLatencyMs ms"
    Write-Host "Proxy ready latency: $proxyReadyLatencyMs ms"
    Write-Host "Post-recovery throughput: $($postRecoveryBenchmark.metrics.average_throughput_kbps) kbps"
} finally {
    Stop-HelixLabSession -Session $session
}
