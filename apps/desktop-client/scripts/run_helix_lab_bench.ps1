param(
    [string]$AdapterUrl = "http://127.0.0.1:8088",
    [string]$InternalToken = "",
    [string]$DesktopBinaryPath = "",
    [string]$TargetHost = "speed.cloudflare.com",
    [int]$TargetPort = 80,
    [string]$TargetPath = "/__down?bytes=1000000",
    [int]$Attempts = 7,
    [int]$ConnectTimeoutSeconds = 10,
    [int]$StartupTimeoutSeconds = 30,
    [string]$OutputDir = "",
    [string]$ScenarioName = "external-cloudflare",
    [switch]$UseSyntheticLabTarget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try {
        return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    } finally {
        $listener.Stop()
    }
}

function Resolve-HelixLabTargetIp {
    try {
        $ip = (& docker inspect -f "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" helix-bench-target | Out-String).Trim()
        if (-not [string]::IsNullOrWhiteSpace($ip)) {
            return $ip
        }
    } catch {
    }

    return "helix-bench-target"
}

if ($UseSyntheticLabTarget) {
    $TargetHost = Resolve-HelixLabTargetIp
    $TargetPort = 80
    $TargetPath = "/8mb.bin"
    if ($ScenarioName -eq "external-cloudflare") {
        $ScenarioName = "synthetic-lab-target"
    }
}

function Wait-ForHealth {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-RestMethod -Uri $Url -Method Get
            if ($response.ready -eq $true -or $response.status -eq "ready") {
                return $response
            }
        } catch {
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)

    throw "Helix sidecar health endpoint did not become ready in time: $Url"
}

function Convert-ToMedian {
    param([double[]]$Values)

    if (-not $Values -or $Values.Count -eq 0) {
        return $null
    }

    $sorted = $Values | Sort-Object
    $middle = [int]($sorted.Count / 2)
    if ($sorted.Count % 2 -eq 1) {
        return [Math]::Round($sorted[$middle], 2)
    }

    return [Math]::Round((($sorted[$middle - 1] + $sorted[$middle]) / 2.0), 2)
}

function Convert-ToPercentile {
    param(
        [double[]]$Values,
        [double]$Percentile
    )

    if (-not $Values -or $Values.Count -eq 0) {
        return $null
    }

    $sorted = $Values | Sort-Object
    $index = [Math]::Ceiling(($sorted.Count * $Percentile)) - 1
    if ($index -lt 0) {
        $index = 0
    }
    if ($index -ge $sorted.Count) {
        $index = $sorted.Count - 1
    }

    return [Math]::Round([double]$sorted[$index], 2)
}

function Get-DefaultOutputDir {
    $scriptDir = Split-Path -Parent $PSCommandPath
    return (Join-Path $scriptDir "..\.artifacts\helix-lab")
}

function Write-Utf8NoBomFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

if ([string]::IsNullOrWhiteSpace($InternalToken)) {
    $infraEnvPath = Join-Path (Join-Path $PSScriptRoot "..\..\..\infra") ".env"
    if (Test-Path $infraEnvPath) {
        foreach ($line in Get-Content -Path $infraEnvPath) {
            if ($line -match "^\s*HELIX_INTERNAL_AUTH_TOKEN=(.+)$") {
                $InternalToken = $Matches[1].Trim()
                break
            }
        }
    }
}

if ([string]::IsNullOrWhiteSpace($InternalToken)) {
    throw "HELIX internal token was not provided and could not be loaded from infra/.env."
}

if ([string]::IsNullOrWhiteSpace($DesktopBinaryPath)) {
    $DesktopBinaryPath = Join-Path $PSScriptRoot "..\src-tauri\target\release\desktop-client.exe"
}

if (-not (Test-Path $DesktopBinaryPath)) {
    throw "Desktop binary was not found at $DesktopBinaryPath"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Get-DefaultOutputDir
}

$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runDir = Join-Path $OutputDir $timestamp
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$headers = @{ "x-internal-token" = $InternalToken }
$postHeaders = @{
    "x-internal-token" = $InternalToken
    "content-type" = "application/json"
}

$capabilities = Invoke-RestMethod `
    -Uri "$AdapterUrl/internal/client-capabilities/defaults" `
    -Headers $headers `
    -Method Get

$manifestRequest = @{
    user_id = "lab-bench-user"
    desktop_client_id = "desktop-helix-bench"
    entitlement_id = "subscription:lab-bench-user"
    trace_id = "trace-$([guid]::NewGuid().ToString('N'))"
    channel = "lab"
    supported_protocol_versions = $capabilities.supported_protocol_versions
    supported_transport_profiles = $capabilities.supported_transport_profiles
    preferred_fallback_core = "sing-box"
}

$manifestResponse = Invoke-RestMethod `
    -Uri "$AdapterUrl/internal/manifests/resolve" `
    -Headers $postHeaders `
    -Method Post `
    -Body ($manifestRequest | ConvertTo-Json -Depth 10)

$healthPort = Get-FreeTcpPort
$proxyPort = Get-FreeTcpPort

$runtimeConfig = @{
    schema_version = "1.0"
    manifest_id = $manifestResponse.manifest.manifest_id
    manifest_version_id = $manifestResponse.manifest_version_id
    rollout_id = $manifestResponse.manifest.rollout_id
    health_bind_addr = "127.0.0.1:$healthPort"
    health_url = "http://127.0.0.1:$healthPort/healthz"
    proxy_bind_addr = "127.0.0.1:$proxyPort"
    proxy_url = "socks5://127.0.0.1:$proxyPort"
    transport_family = $manifestResponse.manifest.transport.transport_family
    session_mode = $manifestResponse.manifest.transport.session_mode
    transport_profile_id = $manifestResponse.manifest.transport_profile.transport_profile_id
    profile_family = $manifestResponse.manifest.transport_profile.profile_family
    profile_version = $manifestResponse.manifest.transport_profile.profile_version
    policy_version = $manifestResponse.manifest.transport_profile.policy_version
    compatibility_window = $manifestResponse.manifest.compatibility_window
    fallback_core = $manifestResponse.manifest.capability_profile.fallback_core
    required_capabilities = $manifestResponse.manifest.capability_profile.required_capabilities
    startup_timeout_seconds = $manifestResponse.manifest.capability_profile.health_policy.startup_timeout_seconds
    runtime_unhealthy_threshold = $manifestResponse.manifest.capability_profile.health_policy.runtime_unhealthy_threshold
    credentials = $manifestResponse.manifest.credentials
    routes = $manifestResponse.manifest.routes
    observability = $manifestResponse.manifest.observability
    integrity = $manifestResponse.manifest.integrity
}

$runtimeConfigPath = Join-Path $runDir "runtime.json"
$manifestPath = Join-Path $runDir "manifest.json"
$stdoutPath = Join-Path $runDir "helix-sidecar.stdout.log"
$stderrPath = Join-Path $runDir "helix-sidecar.stderr.log"
$reportPath = Join-Path $runDir "helix-lab-benchmark-report.json"
$healthPath = Join-Path $runDir "helix-sidecar-health.json"
Write-Utf8NoBomFile -Path $manifestPath -Content ($manifestResponse | ConvertTo-Json -Depth 16)
Write-Utf8NoBomFile -Path $runtimeConfigPath -Content ($runtimeConfig | ConvertTo-Json -Depth 16)

$process = Start-Process `
    -FilePath $DesktopBinaryPath `
    -ArgumentList @("run", "-c", $runtimeConfigPath) `
    -PassThru `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath

try {
    $initialHealth = Wait-ForHealth -Url $runtimeConfig.health_url -TimeoutSeconds $StartupTimeoutSeconds

    $attemptResults = @()
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $url = "http://${TargetHost}:${TargetPort}${TargetPath}"
        $curlResult = & curl.exe `
            --silent `
            --show-error `
            --output NUL `
            --proxy ("socks5h://127.0.0.1:{0}" -f $proxyPort) `
            --connect-timeout $ConnectTimeoutSeconds `
            --max-time ($ConnectTimeoutSeconds * 3) `
            --write-out "%{time_connect}|%{time_starttransfer}|%{time_total}|%{size_download}|%{speed_download}|%{http_code}|%{remote_ip}" `
            $url

        if ($LASTEXITCODE -ne 0) {
            throw "curl benchmark attempt failed with exit code $LASTEXITCODE"
        }

        $parts = ($curlResult | Out-String).Trim() -split "\|", 7
        if ($parts.Count -ne 7) {
            throw "Unexpected curl benchmark output: $curlResult"
        }

        $attemptResults += [pscustomobject]@{
            attempt = $attempt
            connect_latency_ms = [Math]::Round([double]$parts[0] * 1000, 2)
            first_byte_latency_ms = [Math]::Round([double]$parts[1] * 1000, 2)
            total_time_ms = [Math]::Round([double]$parts[2] * 1000, 2)
            bytes_downloaded = [int64]$parts[3]
            throughput_kbps = [Math]::Round(([double]$parts[4] * 8) / 1000, 2)
            http_code = [int]$parts[5]
            remote_ip = [string]$parts[6]
        }
    }

    $finalHealth = Invoke-RestMethod -Uri $runtimeConfig.health_url -Method Get
    Write-Utf8NoBomFile -Path $healthPath -Content ($finalHealth | ConvertTo-Json -Depth 12)

    $connectValues = @($attemptResults | ForEach-Object { [double]$_.connect_latency_ms })
    $firstByteValues = @($attemptResults | ForEach-Object { [double]$_.first_byte_latency_ms })
    $throughputValues = @($attemptResults | ForEach-Object { [double]$_.throughput_kbps })

    $report = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        scenario = $ScenarioName
        adapter_url = $AdapterUrl
        desktop_binary_path = (Resolve-Path $DesktopBinaryPath).Path
        output_dir = $runDir
        target = @{
            host = $TargetHost
            port = $TargetPort
            path = $TargetPath
            attempts = $Attempts
        }
        manifest = @{
            manifest_version_id = $manifestResponse.manifest_version_id
            rollout_id = $manifestResponse.manifest.rollout_id
            transport_profile_id = $manifestResponse.manifest.transport_profile.transport_profile_id
            route_count = @($manifestResponse.manifest.routes).Count
            routes = $manifestResponse.manifest.routes
        }
        initial_health = $initialHealth
        final_health = $finalHealth
        metrics = @{
            median_connect_latency_ms = Convert-ToMedian -Values $connectValues
            p95_connect_latency_ms = Convert-ToPercentile -Values $connectValues -Percentile 0.95
            median_first_byte_latency_ms = Convert-ToMedian -Values $firstByteValues
            p95_first_byte_latency_ms = Convert-ToPercentile -Values $firstByteValues -Percentile 0.95
            average_throughput_kbps = if ($throughputValues.Count -gt 0) {
                [Math]::Round((($throughputValues | Measure-Object -Average).Average), 2)
            } else {
                $null
            }
            bytes_downloaded_total = ($attemptResults | Measure-Object -Property bytes_downloaded -Sum).Sum
        }
        attempts = $attemptResults
        artifacts = @{
            runtime_config = $runtimeConfigPath
            manifest = $manifestPath
            sidecar_stdout = $stdoutPath
            sidecar_stderr = $stderrPath
            sidecar_health = $healthPath
        }
    }

    Write-Utf8NoBomFile -Path $reportPath -Content ($report | ConvertTo-Json -Depth 16)
    Write-Host "Helix lab benchmark completed."
    Write-Host "Scenario: $ScenarioName"
    Write-Host "Report: $reportPath"
    Write-Host "Median connect latency: $($report.metrics.median_connect_latency_ms) ms"
    Write-Host "Median first-byte latency: $($report.metrics.median_first_byte_latency_ms) ms"
    Write-Host "Average throughput: $($report.metrics.average_throughput_kbps) kbps"
} finally {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
}
