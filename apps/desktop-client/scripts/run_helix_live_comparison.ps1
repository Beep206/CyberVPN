param(
    [string]$AdapterUrl = "http://127.0.0.1:8088",
    [string]$InternalToken = "",
    [string]$DesktopBinaryPath = "",
    [string]$SingBoxBinaryPath = "",
    [string]$StableProxyHost = "127.0.0.1",
    [int]$StableProxyPort = 8899,
    [string]$TargetHost = "speed.cloudflare.com",
    [int]$TargetPort = 80,
    [string]$TargetPath = "/__down?bytes=1000000",
    [int]$Attempts = 7,
    [int]$WarmupAttempts = 1,
    [int]$DownloadBytesLimit = 262144,
    [int]$ConnectTimeoutSeconds = 10,
    [int]$StartupTimeoutSeconds = 30,
    [string]$OutputDir = "",
    [string]$ScenarioName = "helix-live-comparison",
    [switch]$UseSyntheticLabTarget,
    [switch]$PublishBenchmarkEvent
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "helix_lab_common.ps1")

function Resolve-SingBoxBinaryPath {
    param([string]$SingBoxBinaryPath)

    if (-not [string]::IsNullOrWhiteSpace($SingBoxBinaryPath)) {
        if (-not (Test-Path $SingBoxBinaryPath)) {
            throw "Sing-box binary was not found at $SingBoxBinaryPath"
        }
        return (Resolve-Path $SingBoxBinaryPath).Path
    }

    $candidates = @(
        "C:\Users\user\AppData\Roaming\com.beep.desktop-client\bin\sing-box.exe",
        (Join-Path $PSScriptRoot "..\src-tauri\bin\sing-box.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "Sing-box binary was not found in the default desktop runtime locations."
}

function Get-TargetDefinition {
    param(
        [string]$TargetHost,
        [int]$TargetPort,
        [string]$TargetPath,
        [bool]$UseSyntheticLabTarget
    )

    if ($UseSyntheticLabTarget) {
        return [pscustomobject]@{
            host = Resolve-HelixLabTargetIp
            port = 80
            path = "/8mb.bin"
            label = "synthetic-lab-target"
        }
    }

    return [pscustomobject]@{
        host = $TargetHost
        port = $TargetPort
        path = $TargetPath
        label = "external-target"
    }
}

function New-SingBoxLabConfig {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][int]$LocalProxyPort,
        [Parameter(Mandatory = $true)][string]$StableProxyHost,
        [Parameter(Mandatory = $true)][int]$StableProxyPort
    )

    $config = [ordered]@{
        log = [ordered]@{
            level = "info"
            timestamp = $true
        }
        inbounds = @(
            [ordered]@{
                type = "mixed"
                tag = "mixed-in"
                listen = "127.0.0.1"
                listen_port = $LocalProxyPort
                sniff = $true
                sniff_override_destination = $true
            }
        )
        outbounds = @(
            [ordered]@{
                type = "http"
                tag = "proxy"
                server = $StableProxyHost
                server_port = $StableProxyPort
            },
            [ordered]@{
                type = "direct"
                tag = "direct"
            },
            [ordered]@{
                type = "dns"
                tag = "dns-out"
            }
        )
        route = [ordered]@{
            rules = @(
                [ordered]@{
                    protocol = "dns"
                    outbound = "dns-out"
                }
            )
            final = "proxy"
            auto_detect_interface = $true
        }
        dns = [ordered]@{
            servers = @(
                [ordered]@{
                    tag = "dns-local"
                    address = "1.1.1.1"
                    detour = "direct"
                }
            )
            final = "dns-local"
        }
    }

    Write-Utf8NoBomFile -Path $Path -Content ($config | ConvertTo-Json -Depth 12)
}

function Start-SingBoxLabProcess {
    param(
        [Parameter(Mandatory = $true)][string]$SingBoxBinaryPath,
        [Parameter(Mandatory = $true)][string]$ConfigPath,
        [Parameter(Mandatory = $true)][string]$StdoutPath,
        [Parameter(Mandatory = $true)][string]$StderrPath
    )

    return Start-Process `
        -FilePath $SingBoxBinaryPath `
        -ArgumentList @("run", "-c", $ConfigPath) `
        -PassThru `
        -RedirectStandardOutput $StdoutPath `
        -RedirectStandardError $StderrPath
}

function Stop-LabProcess {
    param($Process)

    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force
    }
}

function Get-MedianGapFromAttemptSeries {
    param($BenchmarkSeries)

    $gaps = @($BenchmarkSeries.attempts | ForEach-Object {
        [double]([Math]::Max($_.first_byte_latency_ms - $_.connect_latency_ms, 0))
    })
    return Convert-ToMedian -Values $gaps
}

function Get-Ratio {
    param(
        [Nullable[double]]$Value,
        [Nullable[double]]$Baseline
    )

    if ($null -eq $Value -or $null -eq $Baseline) {
        return $null
    }
    if ([Math]::Abs([double]$Baseline) -lt [double]::Epsilon) {
        return $null
    }
    return [Math]::Round(([double]$Value / [double]$Baseline), 4)
}

function Get-RecentRttP95 {
    param($Telemetry)

    if ($null -eq $Telemetry -or $null -eq $Telemetry.recent_rtt_ms) {
        return $null
    }

    $values = @($Telemetry.recent_rtt_ms | ForEach-Object { [double]$_ })
    if ($values.Count -eq 0) {
        return $null
    }

    return Convert-ToPercentile -Values $values -Percentile 0.95
}

function Convert-ToNullableInt {
    param($Value)

    if ($null -eq $Value) {
        return $null
    }

    return [int][Math]::Round([double]$Value, 0)
}

function Publish-HelixBenchmarkEvent {
    param(
        [Parameter(Mandatory = $true)][string]$AdapterUrl,
        [Parameter(Mandatory = $true)][string]$InternalToken,
        [Parameter(Mandatory = $true)]$Session,
        [Parameter(Mandatory = $true)]$HelixBenchmark,
        [Parameter(Mandatory = $true)][Nullable[double]]$RelativeThroughputRatio,
        [Parameter(Mandatory = $true)][Nullable[double]]$RelativeGapRatio,
        [Parameter(Mandatory = $true)]$HelixHealth,
        [Parameter(Mandatory = $true)]$HelixTelemetry,
        [Parameter(Mandatory = $true)][int]$Attempts
    )

    $gapValues = @($HelixBenchmark.attempts | ForEach-Object {
        [double]([Math]::Max($_.first_byte_latency_ms - $_.connect_latency_ms, 0))
    })

    $payload = [ordered]@{
        schema_version = "1.0"
        event_id = [guid]::NewGuid().ToString()
        user_id = "lab-bench-user"
        desktop_client_id = "desktop-helix-bench"
        manifest_version_id = $Session.manifest_response.manifest_version_id
        rollout_id = $Session.manifest_response.manifest.rollout_id
        transport_profile_id = $Session.manifest_response.manifest.transport_profile.transport_profile_id
        event_kind = "benchmark"
        active_core = "helix"
        fallback_core = $null
        latency_ms = (Convert-ToNullableInt $HelixBenchmark.metrics.median_first_byte_latency_ms)
        route_count = @($Session.manifest_response.manifest.routes).Count
        reason = "comparison benchmark evidence"
        observed_at = (Get-Date).ToUniversalTime().ToString("o")
        payload = [ordered]@{
            stage = "benchmark"
            runtime = "embedded-sidecar"
            requested_core = "helix"
            benchmark = [ordered]@{
                benchmark_kind = "comparison"
                baseline_core = "sing-box"
                target_count = 1
                successful_targets = 1
                attempts = $Attempts
                successes = @($HelixBenchmark.attempts).Count
                failures = 0
                throughput_kbps = $HelixBenchmark.metrics.average_throughput_kbps
                relative_throughput_ratio_vs_baseline = $RelativeThroughputRatio
                median_connect_latency_ms = (Convert-ToNullableInt $HelixBenchmark.metrics.median_connect_latency_ms)
                median_first_byte_latency_ms = (Convert-ToNullableInt $HelixBenchmark.metrics.median_first_byte_latency_ms)
                median_open_to_first_byte_gap_ms = (Convert-ToNullableInt (Convert-ToMedian -Values $gapValues))
                p95_open_to_first_byte_gap_ms = (Convert-ToNullableInt (Convert-ToPercentile -Values $gapValues -Percentile 0.95))
                relative_open_to_first_byte_gap_ratio_vs_baseline = $RelativeGapRatio
                frame_queue_peak = $HelixHealth.frame_queue_peak
                recent_rtt_p95_ms = (Convert-ToNullableInt (Get-RecentRttP95 -Telemetry $HelixTelemetry))
                active_streams = $HelixHealth.active_streams
                pending_open_streams = $HelixHealth.pending_open_streams
            }
        }
    }

    $headers = @{
        "x-internal-token" = $InternalToken
        "content-type" = "application/json"
    }

    return Invoke-RestMethod `
        -Uri "$AdapterUrl/internal/desktop/runtime-events" `
        -Headers $headers `
        -Method Post `
        -Body ($payload | ConvertTo-Json -Depth 16)
}

$InternalToken = Get-HelixInternalToken -InternalToken $InternalToken
$DesktopBinaryPath = Resolve-HelixDesktopBinaryPath -DesktopBinaryPath $DesktopBinaryPath
$SingBoxBinaryPath = Resolve-SingBoxBinaryPath -SingBoxBinaryPath $SingBoxBinaryPath

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $PSScriptRoot "..\.artifacts\helix-live-comparison"
}

$target = Get-TargetDefinition `
    -TargetHost $TargetHost `
    -TargetPort $TargetPort `
    -TargetPath $TargetPath `
    -UseSyntheticLabTarget:$UseSyntheticLabTarget

$session = $null
$singBoxProcess = $null

try {
    $session = New-HelixLabSession `
        -AdapterUrl $AdapterUrl `
        -InternalToken $InternalToken `
        -DesktopBinaryPath $DesktopBinaryPath `
        -OutputDir $OutputDir `
        -StartupTimeoutSeconds $StartupTimeoutSeconds `
        -ScenarioName $ScenarioName

    $healthUrl = $session.runtime_config.health_url
    $telemetryUrl = Get-HelixSidecarEndpointUrl -HealthUrl $healthUrl -Path "/telemetry"
    $helixHealthBefore = Get-HelixSidecarJson -Url $healthUrl
    $helixTelemetryBefore = Get-HelixSidecarJson -Url $telemetryUrl

    $helixBenchmark = Invoke-HelixBenchmarkSeries `
        -ProxyUrl $session.runtime_config.proxy_url `
        -TargetHost $target.host `
        -TargetPort $target.port `
        -TargetPath $target.path `
        -Attempts $Attempts `
        -WarmupAttempts $WarmupAttempts `
        -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
        -DownloadBytesLimit $DownloadBytesLimit

    $singBoxProxyPort = Get-FreeTcpPort
    $singBoxConfigPath = Join-Path $session.run_dir "sing-box-config.json"
    $singBoxStdoutPath = Join-Path $session.run_dir "sing-box.stdout.log"
    $singBoxStderrPath = Join-Path $session.run_dir "sing-box.stderr.log"
    $singBoxProxyUrl = "socks5://127.0.0.1:$singBoxProxyPort"

    New-SingBoxLabConfig `
        -Path $singBoxConfigPath `
        -LocalProxyPort $singBoxProxyPort `
        -StableProxyHost $StableProxyHost `
        -StableProxyPort $StableProxyPort

    $singBoxProcess = Start-SingBoxLabProcess `
        -SingBoxBinaryPath $SingBoxBinaryPath `
        -ConfigPath $singBoxConfigPath `
        -StdoutPath $singBoxStdoutPath `
        -StderrPath $singBoxStderrPath

    $null = Wait-ForHelixProxyReady `
        -ProxyUrl $singBoxProxyUrl `
        -TargetHost $target.host `
        -TargetPort $target.port `
        -TargetPath $target.path `
        -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
        -DownloadBytesLimit $DownloadBytesLimit `
        -TimeoutMilliseconds ($StartupTimeoutSeconds * 1000)

    $singBoxBenchmark = Invoke-HelixBenchmarkSeries `
        -ProxyUrl $singBoxProxyUrl `
        -TargetHost $target.host `
        -TargetPort $target.port `
        -TargetPath $target.path `
        -Attempts $Attempts `
        -WarmupAttempts $WarmupAttempts `
        -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
        -DownloadBytesLimit $DownloadBytesLimit

    $helixHealthAfter = Get-HelixSidecarJson -Url $healthUrl
    $helixTelemetryAfter = Get-HelixSidecarJson -Url $telemetryUrl

    $helixMedianGap = Get-MedianGapFromAttemptSeries -BenchmarkSeries $helixBenchmark
    $singBoxMedianGap = Get-MedianGapFromAttemptSeries -BenchmarkSeries $singBoxBenchmark
    $relativeThroughputRatio = Get-Ratio `
        -Value $helixBenchmark.metrics.average_throughput_kbps `
        -Baseline $singBoxBenchmark.metrics.average_throughput_kbps
    $relativeGapRatio = Get-Ratio `
        -Value $helixMedianGap `
        -Baseline $singBoxMedianGap

    $comparisonReportPath = Join-Path $session.run_dir "helix-live-comparison-report.json"
    $helixHealthBeforePath = Join-Path $session.run_dir "helix-health-before.json"
    $helixHealthAfterPath = Join-Path $session.run_dir "helix-health-after.json"
    $helixTelemetryBeforePath = Join-Path $session.run_dir "helix-telemetry-before.json"
    $helixTelemetryAfterPath = Join-Path $session.run_dir "helix-telemetry-after.json"
    Write-Utf8NoBomFile -Path $helixHealthBeforePath -Content ($helixHealthBefore | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $helixHealthAfterPath -Content ($helixHealthAfter | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $helixTelemetryBeforePath -Content ($helixTelemetryBefore | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $helixTelemetryAfterPath -Content ($helixTelemetryAfter | ConvertTo-Json -Depth 16)

    $ack = $null
    $canaryEvidence = $null
    if ($PublishBenchmarkEvent) {
        $ack = Publish-HelixBenchmarkEvent `
            -AdapterUrl $AdapterUrl `
            -InternalToken $InternalToken `
            -Session $session `
            -HelixBenchmark $helixBenchmark `
            -RelativeThroughputRatio $relativeThroughputRatio `
            -RelativeGapRatio $relativeGapRatio `
            -HelixHealth $helixHealthAfter `
            -HelixTelemetry $helixTelemetryAfter `
            -Attempts $Attempts

        $headers = @{ "x-internal-token" = $InternalToken }
        $canaryEvidence = Invoke-RestMethod `
            -Uri "$AdapterUrl/internal/rollouts/$($session.manifest_response.manifest.rollout_id)/canary-evidence" `
            -Headers $headers `
            -Method Get
    }

    $report = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        scenario = $ScenarioName
        target = [ordered]@{
            label = $target.label
            host = $target.host
            port = $target.port
            path = $target.path
        }
        manifest = [ordered]@{
            manifest_version_id = $session.manifest_response.manifest_version_id
            rollout_id = $session.manifest_response.manifest.rollout_id
            transport_profile_id = $session.manifest_response.manifest.transport_profile.transport_profile_id
            route_count = @($session.manifest_response.manifest.routes).Count
        }
        benchmark_policy = [ordered]@{
            attempts = $Attempts
            warmup_attempts = $WarmupAttempts
            download_bytes_limit = $DownloadBytesLimit
            connect_timeout_seconds = $ConnectTimeoutSeconds
            baseline_core = "sing-box"
            stable_proxy_host = $StableProxyHost
            stable_proxy_port = $StableProxyPort
        }
        helix = [ordered]@{
            proxy_url = $session.runtime_config.proxy_url
            benchmark = $helixBenchmark
            health_before = $helixHealthBefore
            telemetry_before = $helixTelemetryBefore
            health_after = $helixHealthAfter
            telemetry_after = $helixTelemetryAfter
            median_open_to_first_byte_gap_ms = $helixMedianGap
        }
        sing_box = [ordered]@{
            proxy_url = $singBoxProxyUrl
            benchmark = $singBoxBenchmark
            median_open_to_first_byte_gap_ms = $singBoxMedianGap
        }
        comparison = [ordered]@{
            baseline_core = "sing-box"
            relative_throughput_ratio = $relativeThroughputRatio
            relative_open_to_first_byte_gap_ratio = $relativeGapRatio
        }
        evidence_publish = [ordered]@{
            published = [bool]$PublishBenchmarkEvent
            startup_ready_ack = $session.startup_ready_event_ack
            startup_ready_error = $session.startup_ready_event_error
            ack = $ack
            canary_evidence = $canaryEvidence
        }
        artifacts = [ordered]@{
            runtime_config = $session.runtime_config_path
            manifest = $session.manifest_path
            helix_stdout = $session.stdout_path
            helix_stderr = $session.stderr_path
            sing_box_config = $singBoxConfigPath
            sing_box_stdout = $singBoxStdoutPath
            sing_box_stderr = $singBoxStderrPath
            helix_health_before = $helixHealthBeforePath
            helix_health_after = $helixHealthAfterPath
            helix_telemetry_before = $helixTelemetryBeforePath
            helix_telemetry_after = $helixTelemetryAfterPath
        }
    }

    Write-Utf8NoBomFile -Path $comparisonReportPath -Content ($report | ConvertTo-Json -Depth 24)

    Write-Host "Helix live comparison completed."
    Write-Host "Scenario: $ScenarioName"
    Write-Host "Report: $comparisonReportPath"
    Write-Host "Helix avg throughput: $($helixBenchmark.metrics.average_throughput_kbps) kbps"
    Write-Host "Sing-box avg throughput: $($singBoxBenchmark.metrics.average_throughput_kbps) kbps"
    Write-Host "Relative throughput ratio: $relativeThroughputRatio"
    Write-Host "Relative open->first-byte gap ratio: $relativeGapRatio"
} finally {
    Stop-LabProcess -Process $singBoxProcess
    if ($null -ne $session) {
        Stop-HelixLabSession -Session $session
    }
}
