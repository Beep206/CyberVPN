[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CommandArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "VertaCompat.ps1")

Sync-VertaPhaseIEnv

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

function Read-EnvValue([string]$Path, [string]$Key) {
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^$Key=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }
    return $line.Substring($line.IndexOf('=') + 1)
}

if (-not $CommandArgs -or $CommandArgs.Count -eq 0) {
    Fail "Usage: with-local-remnawave-supported-upstream-env.ps1 <command> [args...]"
}

$packageRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$workspaceRoot = Resolve-Path (Join-Path $packageRoot "..\..")
$infraEnvPath = Join-Path $workspaceRoot "infra\.env"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "docker was not found. Install Docker before deriving local supported-upstream env."
}

if (-not (Test-Path $infraEnvPath)) {
    Fail "Local infra env file is missing at $infraEnvPath."
}

if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN) {
    $derivedApiToken = Read-EnvValue $infraEnvPath "HELIX_REMNAWAVE_TOKEN"
    if (-not $derivedApiToken) {
        Fail "HELIX_REMNAWAVE_TOKEN is missing in $infraEnvPath."
    }
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN = $derivedApiToken
}

if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT -or -not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID) {
    $firstUser = (& docker exec remnawave-db psql -U postgres -d postgres -t -A -c "select uuid || '|' || short_uuid from users order by created_at asc limit 1;").Trim()
    if (-not $firstUser) {
        Fail "No local Remnawave user was found in remnawave-db."
    }
    $parts = $firstUser.Split('|', 2)
    if ($parts.Count -ne 2) {
        Fail "Could not parse local Remnawave user identity from remnawave-db."
    }
    if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID) {
        $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID = $parts[0]
    }
    if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT) {
        $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT = $parts[1]
    }
}

if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL = "http://localhost"
}
if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE = "verta-local-webhook"
}
if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN = "verta-local-store-auth"
}
if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL = "remnawave-local-docker"
}
if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_LIFECYCLE) {
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_LIFECYCLE = "disabled"
}
if (-not $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SOURCE_VERSION) {
    $sourceVersion = (& docker inspect remnawave --format '{{range .Config.Env}}{{println .}}{{end}}' | Select-String '^__RW_METADATA_VERSION=' | Select-Object -First 1).ToString()
    if (-not $sourceVersion) {
        Fail "Could not derive __RW_METADATA_VERSION from the remnawave container."
    }
    $env:VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SOURCE_VERSION = $sourceVersion.Substring($sourceVersion.IndexOf('=') + 1)
}

Sync-VertaPhaseIEnv

& $CommandArgs[0] @($CommandArgs | Select-Object -Skip 1)
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
