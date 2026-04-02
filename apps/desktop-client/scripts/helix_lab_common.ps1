Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:HelixReadyPollIntervalMs = 10

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

function Write-Utf8NoBomFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Convert-ToMedian {
    param([double[]]$Values)

    $valuesArray = @($Values)
    if ($valuesArray.Count -eq 0) {
        return $null
    }

    $sorted = @($valuesArray | Sort-Object)
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

    $valuesArray = @($Values)
    if ($valuesArray.Count -eq 0) {
        return $null
    }

    $sorted = @($valuesArray | Sort-Object)
    $index = [Math]::Ceiling(($sorted.Count * $Percentile)) - 1
    if ($index -lt 0) {
        $index = 0
    }
    if ($index -ge $sorted.Count) {
        $index = $sorted.Count - 1
    }

    return [Math]::Round([double]$sorted[$index], 2)
}

function Get-HelixInternalToken {
    param([string]$InternalToken)

    if (-not [string]::IsNullOrWhiteSpace($InternalToken)) {
        return $InternalToken
    }

    $infraEnvPath = Join-Path (Join-Path $PSScriptRoot "..\..\..\infra") ".env"
    if (Test-Path $infraEnvPath) {
        foreach ($line in Get-Content -Path $infraEnvPath) {
            if ($line -match "^\s*HELIX_INTERNAL_AUTH_TOKEN=(.+)$") {
                return $Matches[1].Trim()
            }
        }
    }

    throw "HELIX internal token was not provided and could not be loaded from infra/.env."
}

function Resolve-HelixDesktopBinaryPath {
    param([string]$DesktopBinaryPath)

    if ([string]::IsNullOrWhiteSpace($DesktopBinaryPath)) {
        $DesktopBinaryPath = Join-Path $PSScriptRoot "..\src-tauri\target\release\desktop-client.exe"
    }

    if (-not (Test-Path $DesktopBinaryPath)) {
        throw "Desktop binary was not found at $DesktopBinaryPath"
    }

    return (Resolve-Path $DesktopBinaryPath).Path
}

function New-HelixRunDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$BaseDir
    )

    $baseDir = [System.IO.Path]::GetFullPath($BaseDir)
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 6)
    $runDir = Join-Path $baseDir "$timestamp-$suffix"
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    return $runDir
}

function Wait-ForHelixHealth {
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
        Start-Sleep -Milliseconds $script:HelixReadyPollIntervalMs
    } while ((Get-Date) -lt $deadline)

    throw "Helix sidecar health endpoint did not become ready in time: $Url"
}

function Wait-ForHelixStandbyReady {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][int]$TimeoutMilliseconds,
        [Parameter(Mandatory = $true)][string]$ActiveRouteEndpointRef
    )

    $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMilliseconds)
    do {
        try {
            $response = Invoke-RestMethod -Uri $Url -Method Get
            if (
                $response.standby_ready -eq $true -and
                -not [string]::IsNullOrWhiteSpace($response.standby_route_endpoint_ref) -and
                $response.standby_route_endpoint_ref -ne $ActiveRouteEndpointRef
            ) {
                return $response
            }
        } catch {
        }

        Start-Sleep -Milliseconds $script:HelixReadyPollIntervalMs
    } while ([DateTime]::UtcNow -lt $deadline)

    return $null
}

function Get-HelixSidecarJson {
    param(
        [Parameter(Mandatory = $true)][string]$Url
    )

    return Invoke-RestMethod -Uri $Url -Method Get
}

function Get-HelixSidecarEndpointUrl {
    param(
        [Parameter(Mandatory = $true)][string]$HealthUrl,
        [Parameter(Mandatory = $true)][string]$Path
    )

    $uriBuilder = [System.UriBuilder]::new($HealthUrl)
    $uriBuilder.Path = $Path
    return $uriBuilder.Uri.AbsoluteUri
}

function Invoke-HelixSidecarAction {
    param(
        [Parameter(Mandatory = $true)][string]$HealthUrl,
        [Parameter(Mandatory = $true)][ValidateSet("failover", "reconnect")][string]$Mode
    )

    $path = if ($Mode -eq "failover") { "/bench/failover" } else { "/bench/reconnect" }
    $url = Get-HelixSidecarEndpointUrl -HealthUrl $HealthUrl -Path $path
    return Invoke-RestMethod -Uri $url -Method Post
}

function Read-ExactBytes {
    param(
        [Parameter(Mandatory = $true)][System.Net.Sockets.NetworkStream]$Stream,
        [Parameter(Mandatory = $true)][byte[]]$Buffer,
        [Parameter(Mandatory = $true)][int]$Count
    )

    $offset = 0
    while ($offset -lt $Count) {
        $read = $Stream.Read($Buffer, $offset, $Count - $offset)
        if ($read -le 0) {
            throw "Unexpected EOF while reading SOCKS5/HTTP probe stream."
        }

        $offset += $read
    }
}

function Get-Socks5AddressPayload {
    param(
        [Parameter(Mandatory = $true)][string]$TargetName
    )

    $ipAddress = $null
    if ([System.Net.IPAddress]::TryParse($TargetName, [ref]$ipAddress)) {
        $atyp = switch ($ipAddress.AddressFamily) {
            ([System.Net.Sockets.AddressFamily]::InterNetwork) { [byte]0x01; break }
            ([System.Net.Sockets.AddressFamily]::InterNetworkV6) { [byte]0x04; break }
            default { throw "Unsupported IP address family for SOCKS5 probe: $($ipAddress.AddressFamily)" }
        }

        return [pscustomobject]@{
            atyp = $atyp
            payload = [byte[]]$ipAddress.GetAddressBytes()
        }
    }

    $hostBytes = [System.Text.Encoding]::ASCII.GetBytes($TargetName)
    if ($hostBytes.Length -gt 255) {
        throw "SOCKS5 domain target exceeds 255 bytes: $TargetName"
    }

    $payload = New-Object byte[] ($hostBytes.Length + 1)
    $payload[0] = [byte]$hostBytes.Length
    [Array]::Copy($hostBytes, 0, $payload, 1, $hostBytes.Length)

    return [pscustomobject]@{
        atyp = [byte]0x03
        payload = $payload
    }
}

function Read-Socks5ConnectReply {
    param(
        [Parameter(Mandatory = $true)][System.Net.Sockets.NetworkStream]$Stream
    )

    $responseHeader = New-Object byte[] 4
    Read-ExactBytes -Stream $Stream -Buffer $responseHeader -Count 4

    if ($responseHeader[0] -ne 0x05) {
        throw "Unexpected SOCKS5 version in connect reply: $($responseHeader[0])"
    }

    if ($responseHeader[1] -ne 0x00) {
        throw "SOCKS5 CONNECT failed with reply code $($responseHeader[1])"
    }

    switch ($responseHeader[3]) {
        0x01 {
            $discard = New-Object byte[] 6
            Read-ExactBytes -Stream $Stream -Buffer $discard -Count $discard.Length
        }
        0x03 {
            $lengthBuffer = New-Object byte[] 1
            Read-ExactBytes -Stream $Stream -Buffer $lengthBuffer -Count 1
            $discard = New-Object byte[] ([int]$lengthBuffer[0] + 2)
            Read-ExactBytes -Stream $Stream -Buffer $discard -Count $discard.Length
        }
        0x04 {
            $discard = New-Object byte[] 18
            Read-ExactBytes -Stream $Stream -Buffer $discard -Count $discard.Length
        }
        default {
            throw "Unsupported SOCKS5 bound address type in reply: $($responseHeader[3])"
        }
    }
}

function Invoke-HelixBenchmarkAttempt {
    param(
        [Parameter(Mandatory = $true)][string]$ProxyUrl,
        [Parameter(Mandatory = $true)][string]$TargetHost,
        [Parameter(Mandatory = $true)][int]$TargetPort,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [Parameter(Mandatory = $true)][int]$Attempt,
        [Parameter(Mandatory = $true)][int]$ConnectTimeoutSeconds,
        [Parameter(Mandatory = $true)][int]$DownloadBytesLimit,
        [int]$OperationTimeoutMilliseconds = 0,
        [switch]$StopAfterFirstBodyByte
    )

    $proxyUri = [System.Uri]::new($ProxyUrl)
    $proxyHost = $proxyUri.Host
    $proxyPort = $proxyUri.Port
    $socksAddress = Get-Socks5AddressPayload -TargetName $TargetHost
    $networkStream = $null
    $tcpClient = $null

    try {
        $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
        $tcpClient = [System.Net.Sockets.TcpClient]::new()
        $tcpClient.NoDelay = $true
        $effectiveTimeoutMs = if ($OperationTimeoutMilliseconds -gt 0) {
            $OperationTimeoutMilliseconds
        } else {
            $ConnectTimeoutSeconds * 1000
        }

        $connectTask = $tcpClient.ConnectAsync($proxyHost, $proxyPort)
        if (-not $connectTask.Wait([TimeSpan]::FromMilliseconds($effectiveTimeoutMs))) {
            throw "Timed out connecting to Helix SOCKS5 ingress at $ProxyUrl"
        }
        if ($connectTask.IsFaulted) {
            throw $connectTask.Exception.InnerException
        }

        $networkStream = $tcpClient.GetStream()
        $networkStream.ReadTimeout = $effectiveTimeoutMs
        $networkStream.WriteTimeout = $effectiveTimeoutMs

        $authGreeting = [byte[]](0x05, 0x01, 0x00)
        $networkStream.Write($authGreeting, 0, $authGreeting.Length)
        $authResponse = New-Object byte[] 2
        Read-ExactBytes -Stream $networkStream -Buffer $authResponse -Count 2
        if ($authResponse[0] -ne 0x05 -or $authResponse[1] -ne 0x00) {
            throw "SOCKS5 ingress refused no-auth handshake."
        }

        $connectRequest = New-Object byte[] (4 + $socksAddress.payload.Length + 2)
        $connectRequest[0] = 0x05
        $connectRequest[1] = 0x01
        $connectRequest[2] = 0x00
        $connectRequest[3] = $socksAddress.atyp
        [Array]::Copy($socksAddress.payload, 0, $connectRequest, 4, $socksAddress.payload.Length)
        $targetPortBytes = [System.BitConverter]::GetBytes([uint16]$TargetPort)
        if ([System.BitConverter]::IsLittleEndian) {
            [Array]::Reverse($targetPortBytes)
        }
        [Array]::Copy(
            $targetPortBytes,
            0,
            $connectRequest,
            4 + $socksAddress.payload.Length,
            2
        )

        $networkStream.Write($connectRequest, 0, $connectRequest.Length)
        Read-Socks5ConnectReply -Stream $networkStream
        $connectLatencyMs = [Math]::Round($stopwatch.Elapsed.TotalMilliseconds, 2)

        $rangeHeader = if ($DownloadBytesLimit -gt 0) {
            "Range: bytes=0-$([Math]::Max($DownloadBytesLimit - 1, 0))`r`n"
        } else {
            ""
        }
        $httpRequest = (
            "GET $TargetPath HTTP/1.1`r`n" +
            "Host: $TargetHost`r`n" +
            "Accept: */*`r`n" +
            $rangeHeader +
            "Connection: close`r`n" +
            "User-Agent: CyberVPN-Helix-Lab/1.0`r`n`r`n"
        )
        $requestBytes = [System.Text.Encoding]::ASCII.GetBytes($httpRequest)
        $networkStream.Write($requestBytes, 0, $requestBytes.Length)

        $readBuffer = New-Object byte[] 8192
        $headerBytes = New-Object System.Collections.Generic.List[byte]
        $firstByteLatencyMs = $null
        $httpCode = 0
        [int64]$bytesDownloaded = 0
        $headerParsed = $false

        while (-not $headerParsed) {
            $read = $networkStream.Read($readBuffer, 0, $readBuffer.Length)
            if ($read -le 0) {
                throw "HTTP probe did not return a response body."
            }

            $chunkBytes = [byte[]]$readBuffer[0..($read - 1)]
            $headerBytes.AddRange($chunkBytes)
            $headerText = [System.Text.Encoding]::ASCII.GetString($headerBytes.ToArray())
            $separatorIndex = $headerText.IndexOf("`r`n`r`n")
            if ($separatorIndex -lt 0) {
                if ($headerBytes.Count -gt 65536) {
                    throw "HTTP probe headers exceeded 64 KiB."
                }
                continue
            }

            $headerParsed = $true
            $statusLine = ($headerText.Substring(0, $separatorIndex) -split "`r`n")[0]
            if ($statusLine -match "^HTTP/\d+\.\d+\s+(\d{3})") {
                $httpCode = [int]$Matches[1]
            }

            $headerLength = $separatorIndex + 4
            $bodyBytesInBuffer = $headerBytes.Count - $headerLength
            if ($bodyBytesInBuffer -gt 0) {
                $firstByteLatencyMs = [Math]::Round($stopwatch.Elapsed.TotalMilliseconds, 2)
                $bytesDownloaded += [Math]::Min([int64]$bodyBytesInBuffer, [int64]$DownloadBytesLimit)
                if ($StopAfterFirstBodyByte) {
                    break
                }
            }
        }

        while (-not $StopAfterFirstBodyByte -and $bytesDownloaded -lt $DownloadBytesLimit) {
            $read = $networkStream.Read($readBuffer, 0, $readBuffer.Length)
            if ($read -le 0) {
                break
            }

            if ($null -eq $firstByteLatencyMs) {
                $firstByteLatencyMs = [Math]::Round($stopwatch.Elapsed.TotalMilliseconds, 2)
            }

            $remainingBytes = [Math]::Max([int64]$DownloadBytesLimit - $bytesDownloaded, 0)
            $bytesDownloaded += [Math]::Min([int64]$read, $remainingBytes)
        }

        $totalTimeMs = [Math]::Round($stopwatch.Elapsed.TotalMilliseconds, 2)
        if ($null -eq $firstByteLatencyMs) {
            $firstByteLatencyMs = $totalTimeMs
        }

        $throughputKbps = if ($totalTimeMs -gt 0) {
            [Math]::Round((($bytesDownloaded * 8) / 1000.0) / ($totalTimeMs / 1000.0), 2)
        } else {
            $null
        }

        $remoteIp = try {
            ([System.Net.IPEndPoint]$tcpClient.Client.RemoteEndPoint).Address.ToString()
        } catch {
            $proxyHost
        }

        return [pscustomobject]@{
            attempt = $Attempt
            connect_latency_ms = $connectLatencyMs
            first_byte_latency_ms = $firstByteLatencyMs
            total_time_ms = $totalTimeMs
            bytes_downloaded = $bytesDownloaded
            throughput_kbps = $throughputKbps
            http_code = $httpCode
            remote_ip = $remoteIp
        }
    } finally {
        if ($null -ne $networkStream) {
            $networkStream.Dispose()
        }
        if ($null -ne $tcpClient) {
            $tcpClient.Dispose()
        }
    }
}

function Invoke-HelixBenchmarkSeries {
    param(
        [Parameter(Mandatory = $true)][string]$ProxyUrl,
        [Parameter(Mandatory = $true)][string]$TargetHost,
        [Parameter(Mandatory = $true)][int]$TargetPort,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [Parameter(Mandatory = $true)][int]$Attempts,
        [Parameter(Mandatory = $true)][int]$ConnectTimeoutSeconds,
        [Parameter(Mandatory = $true)][int]$DownloadBytesLimit
    )

    $attemptResults = @()
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        $attemptResults += Invoke-HelixBenchmarkAttempt `
            -ProxyUrl $ProxyUrl `
            -TargetHost $TargetHost `
            -TargetPort $TargetPort `
            -TargetPath $TargetPath `
            -Attempt $attempt `
            -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
            -DownloadBytesLimit $DownloadBytesLimit
    }

    $connectValues = @($attemptResults | ForEach-Object { [double]$_.connect_latency_ms })
    $firstByteValues = @($attemptResults | ForEach-Object { [double]$_.first_byte_latency_ms })
    $throughputValues = @($attemptResults | ForEach-Object { [double]$_.throughput_kbps })

    return [pscustomobject]@{
        attempts = $attemptResults
        metrics = [ordered]@{
            median_connect_latency_ms = Convert-ToMedian -Values $connectValues
            p95_connect_latency_ms = Convert-ToPercentile -Values $connectValues -Percentile 0.95
            median_first_byte_latency_ms = Convert-ToMedian -Values $firstByteValues
            p95_first_byte_latency_ms = Convert-ToPercentile -Values $firstByteValues -Percentile 0.95
            average_throughput_kbps = if (@($throughputValues).Count -gt 0) {
                [Math]::Round((($throughputValues | Measure-Object -Average).Average), 2)
            } else {
                $null
            }
            bytes_downloaded_total = ($attemptResults | Measure-Object -Property bytes_downloaded -Sum).Sum
        }
    }
}

function Wait-ForHelixProxyReady {
    param(
        [Parameter(Mandatory = $true)][string]$ProxyUrl,
        [Parameter(Mandatory = $true)][string]$TargetHost,
        [Parameter(Mandatory = $true)][int]$TargetPort,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [Parameter(Mandatory = $true)][int]$ConnectTimeoutSeconds,
        [Parameter(Mandatory = $true)][int]$DownloadBytesLimit,
        [Parameter(Mandatory = $true)][int]$TimeoutMilliseconds
    )

    $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMilliseconds)
    do {
        try {
            $remainingTimeoutMs = [Math]::Max(
                [int]($deadline - [DateTime]::UtcNow).TotalMilliseconds,
                100
            )
            $attemptTimeoutMs = [Math]::Min($remainingTimeoutMs, 750)
            return Invoke-HelixBenchmarkAttempt `
                -ProxyUrl $ProxyUrl `
                -TargetHost $TargetHost `
                -TargetPort $TargetPort `
                -TargetPath $TargetPath `
                -Attempt 1 `
                -ConnectTimeoutSeconds $ConnectTimeoutSeconds `
                -DownloadBytesLimit ([Math]::Min($DownloadBytesLimit, 4096)) `
                -StopAfterFirstBodyByte `
                -OperationTimeoutMilliseconds $attemptTimeoutMs
        } catch {
            Start-Sleep -Milliseconds $script:HelixReadyPollIntervalMs
        }
    } while ([DateTime]::UtcNow -lt $deadline)

    throw "Helix proxy did not become ready before ${TimeoutMilliseconds} ms."
}

function New-HelixLabSession {
    param(
        [Parameter(Mandatory = $true)][string]$AdapterUrl,
        [Parameter(Mandatory = $true)][string]$InternalToken,
        [Parameter(Mandatory = $true)][string]$DesktopBinaryPath,
        [Parameter(Mandatory = $true)][string]$OutputDir,
        [Parameter(Mandatory = $true)][int]$StartupTimeoutSeconds,
        [Parameter(Mandatory = $true)][string]$ScenarioName
    )

    $runDir = New-HelixRunDirectory -BaseDir $OutputDir
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

    $runtimeConfig = [ordered]@{
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
    Write-Utf8NoBomFile -Path $manifestPath -Content ($manifestResponse | ConvertTo-Json -Depth 16)
    Write-Utf8NoBomFile -Path $runtimeConfigPath -Content ($runtimeConfig | ConvertTo-Json -Depth 16)

    $process = Start-Process `
        -FilePath $DesktopBinaryPath `
        -ArgumentList @("run", "-c", $runtimeConfigPath) `
        -PassThru `
        -RedirectStandardOutput $stdoutPath `
        -RedirectStandardError $stderrPath

    $initialHealth = Wait-ForHelixHealth -Url $runtimeConfig.health_url -TimeoutSeconds $StartupTimeoutSeconds

    return [pscustomobject]@{
        scenario = $ScenarioName
        run_dir = $runDir
        manifest_response = $manifestResponse
        runtime_config = $runtimeConfig
        runtime_config_path = $runtimeConfigPath
        manifest_path = $manifestPath
        stdout_path = $stdoutPath
        stderr_path = $stderrPath
        process = $process
        initial_health = $initialHealth
    }
}

function Stop-HelixLabSession {
    param(
        [Parameter(Mandatory = $true)]$Session
    )

    if ($null -ne $Session.process -and -not $Session.process.HasExited) {
        Stop-Process -Id $Session.process.Id -Force
    }
}
