[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL -or `
    -not $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN -or `
    -not $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID) {
    & "$PSScriptRoot\\with-local-remnawave-supported-upstream-env.ps1" "$PSCommandPath"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    exit 0
}

$baseUrl = $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL.TrimEnd('/')
$accountId = $env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID
$headers = @{ Authorization = "Bearer $($env:NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN)" }

try {
    $response = Invoke-WebRequest -Method Post -Uri "$baseUrl/api/users/$accountId/actions/disable" -Headers $headers -UseBasicParsing
    if ($response.StatusCode -in 200, 201) {
        Write-Host "==> Ensured local supported-upstream account is disabled"
        exit 0
    }
} catch {
    $message = $_.Exception.Message
    if ($message -match 'already disabled') {
        Write-Host "==> Local supported-upstream account was already disabled"
        exit 0
    }
    throw
}
