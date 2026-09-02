param(
    [Parameter(Mandatory = $true)]
    [string]$XrayMinimumArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$XrayTargetArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$MihomoArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$SingBoxArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$XrayTargetLinuxArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$XrayTargetMacosX64ArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$XrayTargetMacosArm64ArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$SingBoxLinuxArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$SingBoxMacosX64ArchivePath,

    [Parameter(Mandatory = $true)]
    [string]$SingBoxMacosArm64ArchivePath,

    [string]$CargoPath = 'cargo',

    [string]$EvidencePath
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($EvidencePath)) {
    $EvidencePath = Join-Path $repositoryRoot 'docs\evidence\remnawave-3.4.3\protocol-matrix.json'
}

$temporaryBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$temporaryRoot = Join-Path $temporaryBase ("cybervpn-remnawave-protocol-matrix-" + [guid]::NewGuid())
[System.IO.Directory]::CreateDirectory($temporaryRoot) | Out-Null

$results = [System.Collections.Generic.List[object]]::new()

function Invoke-MatrixCase {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$ArgumentList,
        [bool]$ExpectSuccess
    )

    $rawOutput = (& $Executable @ArgumentList 2>&1 | Out-String).Trim()
    $exitCode = $LASTEXITCODE
    $passed = if ($ExpectSuccess) { $exitCode -eq 0 } else { $exitCode -ne 0 }
    $redactedOutput = $rawOutput.Replace($temporaryRoot, '<temp>').Replace($repositoryRoot, '<repo>')
    $displayArguments = @($ArgumentList | ForEach-Object {
        $_.Replace($temporaryRoot, '<temp>').Replace($repositoryRoot, '<repo>')
    })
    $results.Add([ordered]@{
        name = $Name
        expected = if ($ExpectSuccess) { 'accept' } else { 'reject' }
        exitCode = $exitCode
        passed = $passed
        command = ((Split-Path -Leaf $Executable) + ' ' + ($displayArguments -join ' ')).Trim()
        output = $redactedOutput
    })

    if (-not $passed) {
        throw "Protocol matrix case '$Name' produced exit code $exitCode, expected $(if ($ExpectSuccess) { 'success' } else { 'failure' })."
    }
}

function Write-JsonFixture {
    param([string]$Name, [object]$Value)
    $path = Join-Path $temporaryRoot $Name
    [System.IO.File]::WriteAllText($path, ($Value | ConvertTo-Json -Depth 30))
    return $path
}

function Expand-VerifiedArchive {
    param(
        [string]$Label,
        [string]$ArchivePath,
        [string]$ExpectedSha256,
        [string]$ExecutableName,
        [string]$ExpectedExecutableSha256,
        [System.Collections.IDictionary]$AdditionalRuntimePins = @{}
    )

    $resolvedArchive = (Resolve-Path -LiteralPath $ArchivePath).Path
    $actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolvedArchive).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $ExpectedSha256) {
        throw "Official archive integrity check failed for '$Label': expected $ExpectedSha256, got $actualSha256."
    }

    $destination = Join-Path $temporaryRoot ("verified-" + $Label)
    [System.IO.Directory]::CreateDirectory($destination) | Out-Null
    if ($resolvedArchive.EndsWith('.zip', [StringComparison]::OrdinalIgnoreCase)) {
        Expand-Archive -LiteralPath $resolvedArchive -DestinationPath $destination
    }
    elseif ($resolvedArchive.EndsWith('.tar.gz', [StringComparison]::OrdinalIgnoreCase)) {
        & tar -xzf $resolvedArchive -C $destination
        if ($LASTEXITCODE -ne 0) {
            throw "Verified archive '$Label' could not be extracted by tar (exit $LASTEXITCODE)."
        }
    }
    else {
        throw "Verified archive '$Label' uses an unsupported extension."
    }
    $candidates = @(Get-ChildItem -LiteralPath $destination -Recurse -File | Where-Object {
        $_.Name -eq $ExecutableName
    })
    if ($candidates.Count -ne 1) {
        throw "Verified archive '$Label' contained $($candidates.Count) '$ExecutableName' executables; expected exactly one."
    }

    $runtimeFiles = [ordered]@{}
    $executableSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $candidates[0].FullName).Hash.ToLowerInvariant()
    if ($executableSha256 -ne $ExpectedExecutableSha256) {
        throw "Verified archive '$Label' runtime integrity check failed for '$ExecutableName': expected $ExpectedExecutableSha256, got $executableSha256."
    }
    $runtimeFiles[$ExecutableName] = [ordered]@{
        sha256 = $executableSha256
        verifiedAfterExtraction = $true
    }

    foreach ($pin in $AdditionalRuntimePins.GetEnumerator()) {
        $supportCandidates = @(Get-ChildItem -LiteralPath $destination -Recurse -File | Where-Object {
            $_.Name -eq $pin.Key
        })
        if ($supportCandidates.Count -ne 1) {
            throw "Verified archive '$Label' contained $($supportCandidates.Count) '$($pin.Key)' support files; expected exactly one."
        }
        $supportSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $supportCandidates[0].FullName).Hash.ToLowerInvariant()
        if ($supportSha256 -ne $pin.Value) {
            throw "Verified archive '$Label' runtime integrity check failed for '$($pin.Key)': expected $($pin.Value), got $supportSha256."
        }
        $runtimeFiles[$pin.Key] = [ordered]@{
            sha256 = $supportSha256
            verifiedAfterExtraction = $true
        }
    }

    return [ordered]@{
        archiveFile = Split-Path -Leaf $resolvedArchive
        archiveSha256 = $actualSha256
        archiveVerified = $true
        runtimeFiles = $runtimeFiles
        executablePath = $candidates[0].FullName
    }
}

try {
    $tamperedArchivePath = Join-Path $temporaryRoot 'integrity-negative.zip'
    [System.IO.File]::WriteAllBytes($tamperedArchivePath, [byte[]](0x43, 0x59, 0x42, 0x45, 0x52))
    $tamperedRejectedBeforeExtraction = $false
    try {
        Expand-VerifiedArchive 'integrity-negative' $tamperedArchivePath ('0' * 64) 'unused.exe' ('0' * 64) | Out-Null
    }
    catch {
        if ($_.Exception.Message -notmatch '^Official archive integrity check failed') {
            throw "Archive integrity self-test failed at the wrong boundary: $($_.Exception.Message)"
        }
        $tamperedRejectedBeforeExtraction = $true
    }
    if (-not $tamperedRejectedBeforeExtraction) {
        throw 'Archive integrity self-test accepted a tampered archive.'
    }

    $crossPlatformArchives = [ordered]@{
        xrayLinuxX64 = Expand-VerifiedArchive 'xray-linux-x64' $XrayTargetLinuxArchivePath '8195d909f1109b8f3d99eefe401a3c451d7bf4af71f24d3815420f77e5dd2a40' 'xray' '64d46afb80adea1bf97a0d467e83f4a9ac1ebd0995891e84bca3f1a1d1affb1d'
        xrayMacosX64 = Expand-VerifiedArchive 'xray-macos-x64' $XrayTargetMacosX64ArchivePath '812f7d9de6d3506795eabda2f6928ba301c632c3fe6fa39c52ea8e0ed9e4e244' 'xray' '38571e7799c0f34b1151fc2dfc40cfe570bec55ea59dd93dcee19d52648cea03'
        xrayMacosArm64 = Expand-VerifiedArchive 'xray-macos-arm64' $XrayTargetMacosArm64ArchivePath '9b99a351febe31b7e0c7f22deeb1577a1da0b98aaa51aec7fd17832e68cf63d6' 'xray' 'bd4154efa640c5b8e21f10b68afcc9177c4f1f543be3ec0485b10c499b2a4b27'
        singBoxLinuxX64 = Expand-VerifiedArchive 'sing-box-linux-x64' $SingBoxLinuxArchivePath 'aab8841979aba14ae4c4dc72c4a593be1a16da95e75d53b494ed718f0223370f' 'sing-box' '83b7846dc85ffb1f64c1d14f63eba2fcf3d3b19ed4049c2fcd291ed6c29b5cc2' ([ordered]@{
            'libcronet.so' = '55c35e93dff3ab2174b9a338adbc99f5bd1dc54347f8aa605f44f129db30dd80'
        })
        singBoxMacosX64 = Expand-VerifiedArchive 'sing-box-macos-x64' $SingBoxMacosX64ArchivePath '0db6aca503dcdd5a816e668669e79231f991cdbbd13fcbf6dd4f9bcb8a1c3b0e' 'sing-box' '21a31b26bbb9d9299380083aaab59c949006130720fdc44db940c32f6493f0b6'
        singBoxMacosArm64 = Expand-VerifiedArchive 'sing-box-macos-arm64' $SingBoxMacosArm64ArchivePath 'e9e4c72a4a64c19d515b800b7191c50367522c8169654c569677b15873e08249' 'sing-box' '17e6a7f417a2bbff3693940c024856c3fc88fe5fc3acbc90146a7776d4211909'
    }

    $verifiedArchives = [ordered]@{
        xrayMinimum = Expand-VerifiedArchive 'xray-minimum' $XrayMinimumArchivePath 'd004c39288ce9ada487c6f398c7c545f7d749e44bdfdd59dbc9f865afba4e1ad' 'xray.exe' '15c2d007954ac53ba69b80ec91242786b3c0b71d52649165b4ca1d5cc96ef8f1'
        xrayTarget = Expand-VerifiedArchive 'xray-target' $XrayTargetArchivePath 'c7172078fca4711bcd92a4774dcd1822544579c58816197575c47533317fd8d1' 'xray.exe' '1d9674327972a21afd4c906a7a72bb0856935aa9e0227c87f34f03d11a88bddf'
        mihomo = Expand-VerifiedArchive 'mihomo' $MihomoArchivePath '6d8a079d01b3631e73e56b7b42a067afc14f9e3ad99f2880d38bb141cf8fcbe7' 'mihomo-windows-amd64-compatible.exe' 'a3799f2d75c623a7c6d307e1faf88269e24dd746c59df3e9f1c84d5cfbff6c92'
        singBox = Expand-VerifiedArchive 'sing-box' $SingBoxArchivePath '599b743e9618b38d16ae1af65b35ffa3afadcc531b5bd9fea616e644711be5b9' 'sing-box.exe' 'e4f0d76903dbec850121b20cd6cf917fa6c456a554c97fba53bd6cda7790fbd8' ([ordered]@{
            'libcronet.dll' = '43e2e6c8bf0d29263fed11a7a11c108b671c741c54eb8ba9f5bc5370db8a2684'
        })
    }
    $binaries = @{
        xrayMinimum = $verifiedArchives.xrayMinimum.executablePath
        xrayTarget = $verifiedArchives.xrayTarget.executablePath
        mihomo = $verifiedArchives.mihomo.executablePath
        singBox = $verifiedArchives.singBox.executablePath
    }

    $xrayMinimumVersion = (& $binaries.xrayMinimum version 2>&1 | Select-Object -First 1).ToString()
    $xrayTargetVersion = (& $binaries.xrayTarget version 2>&1 | Select-Object -First 1).ToString()
    $mihomoVersion = (& $binaries.mihomo -v 2>&1 | Select-Object -First 1).ToString()
    $singBoxVersion = (& $binaries.singBox version 2>&1 | Select-Object -First 1).ToString()

    if ($xrayMinimumVersion -notmatch '^Xray 26\.3\.27\b') {
        throw "Minimum Xray binary is not 26.3.27: $xrayMinimumVersion"
    }
    if ($xrayTargetVersion -notmatch '^Xray 26\.7\.28\b') {
        throw "Target Xray binary is not 26.7.28: $xrayTargetVersion"
    }
    if ($mihomoVersion -notmatch 'v1\.19\.28\b') {
        throw "Mihomo binary is not 1.19.28: $mihomoVersion"
    }
    if ($singBoxVersion -notmatch '^sing-box version 1\.13\.8\b') {
        throw "sing-box binary is not 1.13.8: $singBoxVersion"
    }

    # Test-only public material. No live endpoint or private key is present.
    $uuid = 'b831381d-6324-4d53-ad4f-8cda48b30811'
    $publicKey = 'ye-EGRj9KI06zeYwNZ0lZHnaRkMLtPif_66E6jJGbVo'
    $previousMatrixOutput = $env:CYBERVPN_PROTOCOL_MATRIX_OUTPUT
    $env:CYBERVPN_PROTOCOL_MATRIX_OUTPUT = $temporaryRoot
    try {
        Invoke-MatrixCase 'desktop-production-xray-config-export' $CargoPath @(
            'test',
            '--manifest-path',
            (Join-Path $repositoryRoot 'apps\desktop-client\src-tauri\Cargo.toml'),
            'exports_xray_protocol_matrix_fixtures_when_requested',
            '--',
            '--nocapture'
        ) $true
    }
    finally {
        $env:CYBERVPN_PROTOCOL_MATRIX_OUTPUT = $previousMatrixOutput
    }

    $rawXrayPath = Join-Path $temporaryRoot 'xray-raw.json'
    $xhttpXrayPath = Join-Path $temporaryRoot 'xray-xhttp.json'
    if (-not (Test-Path -LiteralPath $rawXrayPath) -or -not (Test-Path -LiteralPath $xhttpXrayPath)) {
        throw 'Desktop Rust generator did not export both Xray matrix fixtures.'
    }
    $xhttpXray = Get-Content -Raw -LiteralPath $xhttpXrayPath | ConvertFrom-Json
    $unknownNetworkXray = $xhttpXray | ConvertTo-Json -Depth 30 | ConvertFrom-Json
    $unknownNetworkXray.outbounds[0].streamSettings.network = 'magic'
    $unknownModeXray = $xhttpXray | ConvertTo-Json -Depth 30 | ConvertFrom-Json
    $unknownModeXray.outbounds[0].streamSettings.xhttpSettings.mode = 'unsafe'

    $unknownNetworkXrayPath = Write-JsonFixture 'xray-unknown-network.json' $unknownNetworkXray
    $unknownModeXrayPath = Write-JsonFixture 'xray-unknown-mode.json' $unknownModeXray

    foreach ($entry in @(
        @{ Label = 'minimum'; Path = $binaries.xrayMinimum },
        @{ Label = 'target'; Path = $binaries.xrayTarget }
    )) {
        Invoke-MatrixCase "xray-$($entry.Label)-raw-reality-vision" $entry.Path @('run', '-test', '-c', $rawXrayPath) $true
        Invoke-MatrixCase "xray-$($entry.Label)-xhttp-reality-no-flow" $entry.Path @('run', '-test', '-c', $xhttpXrayPath) $true
    }
    Invoke-MatrixCase 'xray-target-unknown-network-fail-closed' $binaries.xrayTarget @('run', '-test', '-c', $unknownNetworkXrayPath) $false
    Invoke-MatrixCase 'xray-target-unknown-xhttp-mode-fail-closed' $binaries.xrayTarget @('run', '-test', '-c', $unknownModeXrayPath) $false

    $mihomoYaml = @"
mixed-port: 2080
mode: rule
proxies:
  - name: raw
    type: vless
    server: raw.invalid
    port: 443
    uuid: $uuid
    network: tcp
    tls: true
    flow: xtls-rprx-vision
    servername: cover.invalid
    client-fingerprint: chrome
    reality-opts:
      public-key: $publicKey
      short-id: abcd
  - name: xhttp
    type: vless
    server: xhttp.invalid
    port: 8443
    uuid: $uuid
    network: xhttp
    tls: true
    servername: cover.invalid
    client-fingerprint: chrome
    reality-opts:
      public-key: $publicKey
      short-id: abcd
    xhttp-opts:
      path: /api/v3
      host: cdn.invalid
      mode: packet-up
proxy-groups:
  - name: proxy
    type: select
    proxies: [raw, xhttp]
rules:
  - MATCH,proxy
"@
    $mihomoPath = Join-Path $temporaryRoot 'mihomo.yaml'
    [System.IO.File]::WriteAllText($mihomoPath, $mihomoYaml)
    $mihomoUnknownPath = Join-Path $temporaryRoot 'mihomo-unknown.yaml'
    [System.IO.File]::WriteAllText(
        $mihomoUnknownPath,
        $mihomoYaml.Replace('network: xhttp', 'network: magic')
    )
    Invoke-MatrixCase 'mihomo-raw-vision-and-xhttp-no-flow' $binaries.mihomo @('-t', '-d', $temporaryRoot, '-f', $mihomoPath) $true
    # Mihomo's own validator accepts this unknown value (and may downgrade it);
    # CyberVPN's subscription parser is therefore the fail-closed boundary.
    Invoke-MatrixCase 'mihomo-validator-accepts-unknown-network-parser-guard-required' $binaries.mihomo @('-t', '-d', $temporaryRoot, '-f', $mihomoUnknownPath) $true

    $singBoxRaw = [ordered]@{
        log = [ordered]@{ level = 'warn' }
        inbounds = @([ordered]@{
            type = 'mixed'; tag = 'mixed-in'; listen = '127.0.0.1'; listen_port = 2080
        })
        outbounds = @(
            [ordered]@{
                type = 'vless'; tag = 'proxy'; server = 'raw.invalid'; server_port = 443
                uuid = $uuid; flow = 'xtls-rprx-vision'
                tls = [ordered]@{
                    enabled = $true; server_name = 'cover.invalid'
                    utls = [ordered]@{ enabled = $true; fingerprint = 'chrome' }
                    reality = [ordered]@{ enabled = $true; public_key = $publicKey; short_id = 'abcd' }
                }
            },
            [ordered]@{ type = 'direct'; tag = 'direct' }
        )
        route = [ordered]@{ final = 'proxy'; auto_detect_interface = $true }
    }
    $singBoxXhttp = $singBoxRaw | ConvertTo-Json -Depth 30 | ConvertFrom-Json
    $singBoxXhttp.outbounds[0].PSObject.Properties.Remove('flow')
    $singBoxXhttp.outbounds[0] | Add-Member -NotePropertyName transport -NotePropertyValue ([ordered]@{
        type = 'xhttp'; path = '/api/v3'; host = 'cdn.invalid'
    })
    $singBoxRawPath = Write-JsonFixture 'sing-box-raw.json' $singBoxRaw
    $singBoxXhttpPath = Write-JsonFixture 'sing-box-xhttp.json' $singBoxXhttp
    Invoke-MatrixCase 'sing-box-raw-reality-vision' $binaries.singBox @('check', '-c', $singBoxRawPath) $true
    Invoke-MatrixCase 'sing-box-xhttp-unsupported-fail-closed' $binaries.singBox @('check', '-c', $singBoxXhttpPath) $false

    $binaryEvidence = [ordered]@{}
    foreach ($entry in $binaries.GetEnumerator()) {
        $binaryEvidence[$entry.Key] = [ordered]@{
            file = Split-Path -Leaf $entry.Value
            sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Value).Hash.ToLowerInvariant()
        }
    }
    $binaryEvidence.xrayMinimum.version = $xrayMinimumVersion
    $binaryEvidence.xrayTarget.version = $xrayTargetVersion
    $binaryEvidence.mihomo.version = $mihomoVersion
    $binaryEvidence.singBox.version = $singBoxVersion

    $evidence = [ordered]@{
        schemaVersion = 1
        generatedAtUtc = [DateTimeOffset]::UtcNow.ToString('o')
        scope = 'Local Windows parser/config validation only. Windows executables came from verified official archives; Linux/macOS release-target archives and their pinned runtime members were hash-verified after extraction but were not executed. No live-connect, staging, production, revoke, or refresh claim is made.'
        remnawavePanel = '3.4.3'
        remnawaveNode = '3.4.1'
        desktopReleaseTargets = @('windows-x86_64', 'linux-x86_64', 'macos-x86_64', 'macos-aarch64')
        officialDigestSources = [ordered]@{
            xray = 'https://api.github.com/repos/XTLS/Xray-core/releases/tags/v26.7.28'
            singBox = 'https://api.github.com/repos/SagerNet/sing-box/releases/tags/v1.13.8'
        }
        archiveIntegritySelfTest = [ordered]@{
            tamperedArchiveRejected = $tamperedRejectedBeforeExtraction
            rejectedBeforeExtraction = $tamperedRejectedBeforeExtraction
        }
        officialAssets = [ordered]@{
            xrayMinimum = [ordered]@{
                url = 'https://github.com/XTLS/Xray-core/releases/download/v26.3.27/Xray-windows-64.zip'
                archiveFile = $verifiedArchives.xrayMinimum.archiveFile
                archiveSha256 = $verifiedArchives.xrayMinimum.archiveSha256
                archiveVerifiedBeforeExtraction = $verifiedArchives.xrayMinimum.archiveVerified
                runtimeFiles = $verifiedArchives.xrayMinimum.runtimeFiles
            }
            xrayTarget = [ordered]@{
                url = 'https://github.com/XTLS/Xray-core/releases/download/v26.7.28/Xray-windows-64.zip'
                archiveFile = $verifiedArchives.xrayTarget.archiveFile
                archiveSha256 = $verifiedArchives.xrayTarget.archiveSha256
                archiveVerifiedBeforeExtraction = $verifiedArchives.xrayTarget.archiveVerified
                runtimeFiles = $verifiedArchives.xrayTarget.runtimeFiles
                sourceCommit = '5ca6f4b7d4dc20a881d4330e498892697627ec0c'
            }
            mihomo = [ordered]@{
                url = 'https://github.com/MetaCubeX/mihomo/releases/download/v1.19.28/mihomo-windows-amd64-compatible-v1.19.28.zip'
                archiveFile = $verifiedArchives.mihomo.archiveFile
                archiveSha256 = $verifiedArchives.mihomo.archiveSha256
                archiveVerifiedBeforeExtraction = $verifiedArchives.mihomo.archiveVerified
                runtimeFiles = $verifiedArchives.mihomo.runtimeFiles
                sourceCommit = 'cbd11db1e13a75d8e680e0fe7742c95be4cba2be'
            }
            singBox = [ordered]@{
                url = 'https://github.com/SagerNet/sing-box/releases/download/v1.13.8/sing-box-1.13.8-windows-amd64.zip'
                archiveFile = $verifiedArchives.singBox.archiveFile
                archiveSha256 = $verifiedArchives.singBox.archiveSha256
                archiveVerifiedBeforeExtraction = $verifiedArchives.singBox.archiveVerified
                runtimeFiles = $verifiedArchives.singBox.runtimeFiles
                sourceCommit = 'd5adb54bc6c6b2c21ab6f748276c4ec62d9bb650'
            }
            xrayLinuxX64 = [ordered]@{
                url = 'https://github.com/XTLS/Xray-core/releases/download/v26.7.28/Xray-linux-64.zip'
                archiveFile = $crossPlatformArchives.xrayLinuxX64.archiveFile
                archiveSha256 = $crossPlatformArchives.xrayLinuxX64.archiveSha256
                archiveVerifiedBeforeExtraction = $crossPlatformArchives.xrayLinuxX64.archiveVerified
                runtimeFiles = $crossPlatformArchives.xrayLinuxX64.runtimeFiles
                executed = $false
            }
            xrayMacosX64 = [ordered]@{
                url = 'https://github.com/XTLS/Xray-core/releases/download/v26.7.28/Xray-macos-64.zip'
                archiveFile = $crossPlatformArchives.xrayMacosX64.archiveFile
                archiveSha256 = $crossPlatformArchives.xrayMacosX64.archiveSha256
                archiveVerifiedBeforeExtraction = $crossPlatformArchives.xrayMacosX64.archiveVerified
                runtimeFiles = $crossPlatformArchives.xrayMacosX64.runtimeFiles
                executed = $false
            }
            xrayMacosArm64 = [ordered]@{
                url = 'https://github.com/XTLS/Xray-core/releases/download/v26.7.28/Xray-macos-arm64-v8a.zip'
                archiveFile = $crossPlatformArchives.xrayMacosArm64.archiveFile
                archiveSha256 = $crossPlatformArchives.xrayMacosArm64.archiveSha256
                archiveVerifiedBeforeExtraction = $crossPlatformArchives.xrayMacosArm64.archiveVerified
                runtimeFiles = $crossPlatformArchives.xrayMacosArm64.runtimeFiles
                executed = $false
            }
            singBoxLinuxX64 = [ordered]@{
                url = 'https://github.com/SagerNet/sing-box/releases/download/v1.13.8/sing-box-1.13.8-linux-amd64.tar.gz'
                archiveFile = $crossPlatformArchives.singBoxLinuxX64.archiveFile
                archiveSha256 = $crossPlatformArchives.singBoxLinuxX64.archiveSha256
                archiveVerifiedBeforeExtraction = $crossPlatformArchives.singBoxLinuxX64.archiveVerified
                runtimeFiles = $crossPlatformArchives.singBoxLinuxX64.runtimeFiles
                executed = $false
            }
            singBoxMacosX64 = [ordered]@{
                url = 'https://github.com/SagerNet/sing-box/releases/download/v1.13.8/sing-box-1.13.8-darwin-amd64.tar.gz'
                archiveFile = $crossPlatformArchives.singBoxMacosX64.archiveFile
                archiveSha256 = $crossPlatformArchives.singBoxMacosX64.archiveSha256
                archiveVerifiedBeforeExtraction = $crossPlatformArchives.singBoxMacosX64.archiveVerified
                runtimeFiles = $crossPlatformArchives.singBoxMacosX64.runtimeFiles
                executed = $false
            }
            singBoxMacosArm64 = [ordered]@{
                url = 'https://github.com/SagerNet/sing-box/releases/download/v1.13.8/sing-box-1.13.8-darwin-arm64.tar.gz'
                archiveFile = $crossPlatformArchives.singBoxMacosArm64.archiveFile
                archiveSha256 = $crossPlatformArchives.singBoxMacosArm64.archiveSha256
                archiveVerifiedBeforeExtraction = $crossPlatformArchives.singBoxMacosArm64.archiveVerified
                runtimeFiles = $crossPlatformArchives.singBoxMacosArm64.runtimeFiles
                executed = $false
            }
        }
        binaries = $binaryEvidence
        results = $results
        limitations = @(
            'sing-box 1.13.8 rejects XHTTP; the desktop client routes imported XHTTP profiles to pinned Xray.',
            'Mihomo 1.19.28 config validation accepts an unknown VLESS network value; CyberVPN rejects it in parser tests before config generation.',
            'The managed Xray path is SOCKS-only and rejects TUN mode explicitly.',
            'Linux arm64 and Windows arm64 are not desktop-release workflow targets; automatic runtime download stays fail-closed until exact target pins are added.',
            'Configuration validation does not prove a successful network connection.'
        )
    }
    $evidenceDirectory = Split-Path -Parent $EvidencePath
    [System.IO.Directory]::CreateDirectory($evidenceDirectory) | Out-Null
    [System.IO.File]::WriteAllText(
        $EvidencePath,
        ($evidence | ConvertTo-Json -Depth 30) + [Environment]::NewLine
    )
    Write-Output "Protocol matrix passed: $($results.Count) deterministic cases."
    Write-Output "Evidence: $EvidencePath"
}
finally {
    $resolvedTemporaryRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
    if ($resolvedTemporaryRoot.StartsWith($temporaryBase, [StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path -Leaf $resolvedTemporaryRoot).StartsWith('cybervpn-remnawave-protocol-matrix-')) {
        Remove-Item -LiteralPath $resolvedTemporaryRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
