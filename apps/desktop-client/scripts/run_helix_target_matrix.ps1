param(
    [string]$AdapterUrl = "http://127.0.0.1:8088",
    [string]$InternalToken = "",
    [string]$DesktopBinaryPath = "",
    [ValidateSet("lab", "external", "mixed")][string]$Preset = "external",
    [string]$TargetsJsonPath = "",
    [int]$Attempts = 5,
    [int]$DownloadBytesLimit = 262144,
    [int]$ConnectTimeoutSeconds = 10,
    [int]$StartupTimeoutSeconds = 30,
    [string]$OutputDir = "",
    [string]$ScenarioName = "helix-target-matrix",
    [switch]$UseSyntheticLabTarget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "helix_lab_common.ps1")

function Get-DefaultMatrixTargets {
    param(
        [Parameter(Mandatory = $true)][string]$PresetName,
        [Parameter(Mandatory = $true)][bool]$IncludeSynthetic
    )

    $targets = switch ($PresetName) {
        "lab" {
            @(
                [pscustomobject]@{ label = "Lab Warm HTTP"; host = "example.com"; port = 80; path = "/" }
            )
        }
        "mixed" {
            @(
                [pscustomobject]@{ label = "Warm HTTP"; host = "example.com"; port = 80; path = "/" }
                [pscustomobject]@{ label = "Cloudflare 256K"; host = "speed.cloudflare.com"; port = 80; path = "/__down?bytes=262144" }
                [pscustomobject]@{ label = "Cloudflare 1M"; host = "speed.cloudflare.com"; port = 80; path = "/__down?bytes=1000000" }
            )
        }
        default {
            @(
                [pscustomobject]@{ label = "Warm HTTP"; host = "example.com"; port = 80; path = "/" }
                [pscustomobject]@{ label = "Cloudflare 256K"; host = "speed.cloudflare.com"; port = 80; path = "/__down?bytes=262144" }
                [pscustomobject]@{ label = "Cloudflare 1M"; host = "speed.cloudflare.com"; port = 80; path = "/__down?bytes=1000000" }
            )
        }
    }

    if ($IncludeSynthetic) {
        $syntheticHost = Resolve-HelixLabTargetIp
        $targets = @(
            [pscustomobject]@{ label = "Synthetic 8M"; host = $syntheticHost; port = 80; path = "/8mb.bin" }
        ) + $targets
    }

    return $targets
}

function Get-MatrixTargets {
    param(
        [string]$TargetsJsonPath,
        [string]$Preset,
        [bool]$UseSyntheticLabTarget
    )

    if (-not [string]::IsNullOrWhiteSpace($TargetsJsonPath)) {
        if (-not (Test-Path $TargetsJsonPath)) {
            throw "Targets JSON file was not found at $TargetsJsonPath"
        }

        $raw = Get-Content -Path $TargetsJsonPath -Raw
        $parsed = $raw | ConvertFrom-Json
        if ($parsed -isnot [System.Collections.IEnumerable]) {
            throw "Targets JSON must be an array."
        }

        return @($parsed | ForEach-Object {
            [pscustomobject]@{
                label = [string]$_.label
                host = [string]$_.host
                port = [int]$_.port
                path = [string]$_.path
            }
        })
    }

    return Get-DefaultMatrixTargets -PresetName $Preset -IncludeSynthetic:$UseSyntheticLabTarget
}

$InternalToken = Get-HelixInternalToken -InternalToken $InternalToken
$DesktopBinaryPath = Resolve-HelixDesktopBinaryPath -DesktopBinaryPath $DesktopBinaryPath
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $PSScriptRoot "..\.artifacts\helix-target-matrix"
}

$targets = Get-MatrixTargets `
    -TargetsJsonPath $TargetsJsonPath `
    -Preset $Preset `
    -UseSyntheticLabTarget:$UseSyntheticLabTarget

if ($targets.Count -eq 0) {
    throw "Helix target matrix needs at least one target."
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

    $targetReports = @()
    foreach ($target in $targets) {
        $benchmark = Invoke-HelixBenchmarkSeries `
            -ProxyUrl $proxyUrl `
            -TargetHost $target.host `
            -TargetPort $target.port `
            -TargetPath $target.path `
            -Attempts $Attempts `
            -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
            -DownloadBytesLimit $DownloadBytesLimit

        $targetReports += [pscustomobject]@{
            label = $target.label
            host = $target.host
            port = $target.port
            path = $target.path
            benchmark = $benchmark
        }
    }

    $healthAfter = Get-HelixSidecarJson -Url $healthUrl
    $telemetryAfter = Get-HelixSidecarJson -Url $telemetryUrl

    $medianConnects = @($targetReports | ForEach-Object {
        if ($null -ne $_.benchmark.metrics.median_connect_latency_ms) {
            [double]$_.benchmark.metrics.median_connect_latency_ms
        }
    })
    $medianFirstBytes = @($targetReports | ForEach-Object {
        if ($null -ne $_.benchmark.metrics.median_first_byte_latency_ms) {
            [double]$_.benchmark.metrics.median_first_byte_latency_ms
        }
    })
    $averageThroughputs = @($targetReports | ForEach-Object {
        if ($null -ne $_.benchmark.metrics.average_throughput_kbps) {
            [double]$_.benchmark.metrics.average_throughput_kbps
        }
    })

    $reportPath = Join-Path $session.run_dir "helix-lab-target-matrix-report.json"
    $healthBeforePath = Join-Path $session.run_dir "helix-health-before.json"
    $healthAfterPath = Join-Path $session.run_dir "helix-health-after.json"
    $telemetryBeforePath = Join-Path $session.run_dir "helix-telemetry-before.json"
    $telemetryAfterPath = Join-Path $session.run_dir "helix-telemetry-after.json"
    Write-Utf8NoBomFile -Path $healthBeforePath -Content ($healthBefore | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $healthAfterPath -Content ($healthAfter | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $telemetryBeforePath -Content ($telemetryBefore | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $telemetryAfterPath -Content ($telemetryAfter | ConvertTo-Json -Depth 16)

    $report = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        scenario = $ScenarioName
        preset = $Preset
        adapter_url = $AdapterUrl
        desktop_binary_path = $DesktopBinaryPath
        output_dir = $session.run_dir
        manifest = [ordered]@{
            manifest_version_id = $session.manifest_response.manifest_version_id
            rollout_id = $session.manifest_response.manifest.rollout_id
            transport_profile_id = $session.manifest_response.manifest.transport_profile.transport_profile_id
            route_count = @($session.manifest_response.manifest.routes).Count
            routes = $session.manifest_response.manifest.routes
        }
        benchmark_policy = [ordered]@{
            attempts = $Attempts
            download_bytes_limit = $DownloadBytesLimit
            connect_timeout_seconds = $ConnectTimeoutSeconds
        }
        health_before = $healthBefore
        telemetry_before = $telemetryBefore
        aggregate = [ordered]@{
            target_count = $targetReports.Count
            median_connect_latency_ms = Convert-ToMedian -Values $medianConnects
            median_first_byte_latency_ms = Convert-ToMedian -Values $medianFirstBytes
            average_throughput_kbps = if ($averageThroughputs.Count -gt 0) {
                [Math]::Round((($averageThroughputs | Measure-Object -Average).Average), 2)
            } else {
                $null
            }
        }
        targets = $targetReports
        health_after = $healthAfter
        telemetry_after = $telemetryAfter
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
    Write-Host "Helix target matrix completed."
    Write-Host "Scenario: $ScenarioName"
    Write-Host "Report: $reportPath"
    Write-Host "Aggregate median connect: $($report.aggregate.median_connect_latency_ms) ms"
    Write-Host "Aggregate median first-byte: $($report.aggregate.median_first_byte_latency_ms) ms"
    Write-Host "Aggregate average throughput: $($report.aggregate.average_throughput_kbps) kbps"
} finally {
    Stop-HelixLabSession -Session $session
}
