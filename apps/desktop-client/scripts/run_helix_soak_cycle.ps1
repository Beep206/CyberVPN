param(
    [string]$AdapterUrl = "http://127.0.0.1:8088",
    [string]$InternalToken = "",
    [string]$DesktopBinaryPath = "",
    [int]$DurationMinutes = 5,
    [int]$ProbeIntervalSeconds = 15,
    [int]$ProbeDownloadBytesLimit = 65536,
    [int]$ConnectTimeoutSeconds = 10,
    [int]$StartupTimeoutSeconds = 30,
    [string]$OutputDir = "",
    [string]$ScenarioName = "helix-soak-cycle",
    [switch]$UseSyntheticLabTarget,
    [switch]$InjectFailover,
    [switch]$InjectReconnect
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "helix_lab_common.ps1")

function Get-SoakTarget {
    param([bool]$UseSynthetic)

    if ($UseSynthetic) {
        return [pscustomobject]@{
            label = "Synthetic 8M"
            host = Resolve-HelixLabTargetIp
            port = 80
            path = "/8mb.bin"
        }
    }

    return [pscustomobject]@{
        label = "Cloudflare 256K"
        host = "speed.cloudflare.com"
        port = 80
        path = "/__down?bytes=262144"
    }
}

function Get-HealthSummary {
    param($Health)

    return [ordered]@{
        status = $Health.status
        ready = $Health.ready
        route_count = $Health.route_count
        active_route_endpoint_ref = $Health.active_route_endpoint_ref
        active_route_score = $Health.active_route_score
        active_route_probe_latency_ms = $Health.active_route_probe_latency_ms
        standby_ready = $Health.standby_ready
        standby_route_endpoint_ref = $Health.standby_route_endpoint_ref
        active_streams = $Health.active_streams
        pending_open_streams = $Health.pending_open_streams
        frame_queue_depth = $Health.frame_queue_depth
        frame_queue_peak = $Health.frame_queue_peak
        continuity_grace_active = $Health.continuity_grace_active
        continuity_grace_route_endpoint_ref = $Health.continuity_grace_route_endpoint_ref
        continuity_grace_remaining_ms = $Health.continuity_grace_remaining_ms
        active_route_quarantined = $Health.active_route_quarantined
        active_route_quarantine_remaining_ms = $Health.active_route_quarantine_remaining_ms
        successful_continuity_recovers = $Health.active_route_successful_continuity_recovers
        failed_continuity_recovers = $Health.active_route_failed_continuity_recovers
        successful_cross_route_recovers = $Health.active_route_successful_cross_route_recovers
    }
}

function Get-TelemetrySummary {
    param($Telemetry)

    $recentRtts = @($Telemetry.recent_rtt_ms | ForEach-Object { [double]$_ })
    $recentFramePeaks = @($Telemetry.recent_streams | ForEach-Object {
        if ($null -ne $_.peak_frame_queue_depth) {
            [double]$_.peak_frame_queue_depth
        }
    })
    $recentInboundPeaks = @($Telemetry.recent_streams | ForEach-Object {
        if ($null -ne $_.peak_inbound_queue_depth) {
            [double]$_.peak_inbound_queue_depth
        }
    })

    return [ordered]@{
        collected_at = $Telemetry.collected_at
        recent_rtt_sample_count = $recentRtts.Count
        recent_rtt_p50_ms = Convert-ToMedian -Values $recentRtts
        recent_rtt_p95_ms = Convert-ToPercentile -Values $recentRtts -Percentile 0.95
        recent_stream_sample_count = @($Telemetry.recent_streams).Count
        recent_stream_peak_frame_queue_depth = Convert-ToPercentile -Values $recentFramePeaks -Percentile 0.95
        recent_stream_peak_inbound_queue_depth = Convert-ToPercentile -Values $recentInboundPeaks -Percentile 0.95
    }
}

function Invoke-SoakProbe {
    param(
        [Parameter(Mandatory = $true)][string]$ProxyUrl,
        [Parameter(Mandatory = $true)]$Target,
        [Parameter(Mandatory = $true)][int]$ConnectTimeoutSeconds,
        [Parameter(Mandatory = $true)][int]$DownloadBytesLimit,
        [Parameter(Mandatory = $true)][int]$Attempt
    )

    return Invoke-HelixBenchmarkAttempt `
        -ProxyUrl $ProxyUrl `
        -TargetHost $Target.host `
        -TargetPort $Target.port `
        -TargetPath $Target.path `
        -Attempt $Attempt `
        -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
        -DownloadBytesLimit $DownloadBytesLimit
}

$InternalToken = Get-HelixInternalToken -InternalToken $InternalToken
$DesktopBinaryPath = Resolve-HelixDesktopBinaryPath -DesktopBinaryPath $DesktopBinaryPath
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $PSScriptRoot "..\.artifacts\helix-soak"
}

$target = Get-SoakTarget -UseSynthetic:$UseSyntheticLabTarget
$durationMinutes = [Math]::Max($DurationMinutes, 1)
$probeIntervalSeconds = [Math]::Max($ProbeIntervalSeconds, 5)
$probeDownloadBytesLimit = [Math]::Max($ProbeDownloadBytesLimit, 4096)

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

    $startedAt = Get-Date
    $deadline = $startedAt.AddMinutes($durationMinutes)
    $failoverTriggered = $false
    $reconnectTriggered = $false
    $samples = New-Object System.Collections.Generic.List[object]
    $actions = New-Object System.Collections.Generic.List[object]
    $probeAttempt = 1

    while ((Get-Date) -lt $deadline) {
        $now = Get-Date
        $elapsedSeconds = [Math]::Round(($now - $startedAt).TotalSeconds, 2)
        $progress = ($now - $startedAt).TotalSeconds / ($deadline - $startedAt).TotalSeconds

        if ($InjectFailover -and -not $failoverTriggered -and $progress -ge 0.40) {
            $actionResult = Invoke-HelixSidecarAction -HealthUrl $healthUrl -Mode "failover"
            $actions.Add([pscustomobject]@{
                timestamp = (Get-Date).ToUniversalTime().ToString("o")
                mode = "failover"
                result = $actionResult
            })
            $failoverTriggered = $true
        }

        if ($InjectReconnect -and -not $reconnectTriggered -and $progress -ge 0.70) {
            $actionResult = Invoke-HelixSidecarAction -HealthUrl $healthUrl -Mode "reconnect"
            $actions.Add([pscustomobject]@{
                timestamp = (Get-Date).ToUniversalTime().ToString("o")
                mode = "reconnect"
                result = $actionResult
            })
            $reconnectTriggered = $true
        }

        $health = Get-HelixSidecarJson -Url $healthUrl
        $telemetry = Get-HelixSidecarJson -Url $telemetryUrl
        $probe = Invoke-SoakProbe `
            -ProxyUrl $proxyUrl `
            -Target $target `
            -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
            -DownloadBytesLimit $probeDownloadBytesLimit `
            -Attempt $probeAttempt

        $samples.Add([pscustomobject]@{
            timestamp = $now.ToUniversalTime().ToString("o")
            elapsed_seconds = $elapsedSeconds
            health = Get-HealthSummary -Health $health
            telemetry = Get-TelemetrySummary -Telemetry $telemetry
            probe = $probe
        })
        $probeAttempt += 1

        $remaining = ($deadline - (Get-Date)).TotalSeconds
        if ($remaining -le 0) {
            break
        }

        Start-Sleep -Seconds ([Math]::Min($probeIntervalSeconds, [Math]::Max([int][Math]::Floor($remaining), 1)))
    }

    $finalHealth = Get-HelixSidecarJson -Url $healthUrl
    $finalTelemetry = Get-HelixSidecarJson -Url $telemetryUrl

    $connectLatencies = @($samples | ForEach-Object { [double]$_.probe.connect_latency_ms })
    $firstByteLatencies = @($samples | ForEach-Object { [double]$_.probe.first_byte_latency_ms })
    $throughputs = @($samples | ForEach-Object { [double]$_.probe.throughput_kbps })
    $frameQueuePeaks = @($samples | ForEach-Object {
        if ($null -ne $_.health.frame_queue_peak) {
            [double]$_.health.frame_queue_peak
        }
    })
    $rttP95Values = @($samples | ForEach-Object {
        if ($null -ne $_.telemetry.recent_rtt_p95_ms) {
            [double]$_.telemetry.recent_rtt_p95_ms
        }
    })
    $routes = @($samples | ForEach-Object { $_.health.active_route_endpoint_ref } | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_)
    })
    $routeSwitches = 0
    for ($index = 1; $index -lt $routes.Count; $index++) {
        if ($routes[$index] -ne $routes[$index - 1]) {
            $routeSwitches += 1
        }
    }

    $reportPath = Join-Path $session.run_dir "helix-soak-report.json"
    $initialHealthPath = Join-Path $session.run_dir "helix-health-initial.json"
    $finalHealthPath = Join-Path $session.run_dir "helix-health-final.json"
    $finalTelemetryPath = Join-Path $session.run_dir "helix-telemetry-final.json"
    $soakReadyAck = $null
    $soakReadyError = $null
    Write-Utf8NoBomFile -Path $initialHealthPath -Content ($session.initial_health | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $finalHealthPath -Content ($finalHealth | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $finalTelemetryPath -Content ($finalTelemetry | ConvertTo-Json -Depth 16)

    try {
        $soakReadyAck = Publish-HelixReadyEvent `
            -AdapterUrl $AdapterUrl `
            -InternalToken $InternalToken `
            -Session $session `
            -Health $finalHealth `
            -Telemetry $finalTelemetry `
            -LatencyMs (Convert-ToNullableInt (Convert-ToMedian -Values $firstByteLatencies)) `
            -Reason "headless soak evidence"
    } catch {
        $soakReadyError = $_.Exception.Message
    }

    $report = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        scenario = $ScenarioName
        duration_minutes = $durationMinutes
        probe_interval_seconds = $probeIntervalSeconds
        target = $target
        adapter_url = $AdapterUrl
        desktop_binary_path = $DesktopBinaryPath
        output_dir = $session.run_dir
        manifest = [ordered]@{
            manifest_version_id = $session.manifest_response.manifest_version_id
            rollout_id = $session.manifest_response.manifest.rollout_id
            transport_profile_id = $session.manifest_response.manifest.transport_profile.transport_profile_id
            route_count = @($session.manifest_response.manifest.routes).Count
        }
        churn_actions = $actions
        summary = [ordered]@{
            sample_count = $samples.Count
            route_switch_count = $routeSwitches
            unique_routes = @($routes | Select-Object -Unique)
            median_connect_latency_ms = Convert-ToMedian -Values $connectLatencies
            p95_connect_latency_ms = Convert-ToPercentile -Values $connectLatencies -Percentile 0.95
            median_first_byte_latency_ms = Convert-ToMedian -Values $firstByteLatencies
            p95_first_byte_latency_ms = Convert-ToPercentile -Values $firstByteLatencies -Percentile 0.95
            average_throughput_kbps = if ($throughputs.Count -gt 0) {
                [Math]::Round((($throughputs | Measure-Object -Average).Average), 2)
            } else {
                $null
            }
            peak_frame_queue_depth = Convert-ToPercentile -Values $frameQueuePeaks -Percentile 1.0
            peak_recent_rtt_p95_ms = Convert-ToPercentile -Values $rttP95Values -Percentile 1.0
            final_successful_continuity_recovers = $finalHealth.active_route_successful_continuity_recovers
            final_successful_cross_route_recovers = $finalHealth.active_route_successful_cross_route_recovers
        }
        initial_health = Get-HealthSummary -Health $session.initial_health
        final_health = Get-HealthSummary -Health $finalHealth
        final_telemetry = Get-TelemetrySummary -Telemetry $finalTelemetry
        evidence_publish = [ordered]@{
            startup_ready_ack = $session.startup_ready_event_ack
            startup_ready_error = $session.startup_ready_event_error
            soak_ready_ack = $soakReadyAck
            soak_ready_error = $soakReadyError
        }
        samples = $samples
        artifacts = [ordered]@{
            runtime_config = $session.runtime_config_path
            manifest = $session.manifest_path
            sidecar_stdout = $session.stdout_path
            sidecar_stderr = $session.stderr_path
            initial_health = $initialHealthPath
            final_health = $finalHealthPath
            final_telemetry = $finalTelemetryPath
        }
    }

    Write-Utf8NoBomFile -Path $reportPath -Content ($report | ConvertTo-Json -Depth 24)
    Write-Host "Helix soak cycle completed."
    Write-Host "Scenario: $ScenarioName"
    Write-Host "Report: $reportPath"
    Write-Host "Samples: $($report.summary.sample_count)"
    Write-Host "Median connect: $($report.summary.median_connect_latency_ms) ms"
    Write-Host "Median first-byte: $($report.summary.median_first_byte_latency_ms) ms"
    Write-Host "Average throughput: $($report.summary.average_throughput_kbps) kbps"
    Write-Host "Route switches: $($report.summary.route_switch_count)"
} finally {
    Stop-HelixLabSession -Session $session
}
