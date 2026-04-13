[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Title
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Error $Message
    exit 1
}

$repoRoot = Resolve-Path (Split-Path -Parent $PSScriptRoot)
$templatePath = Join-Path $repoRoot "docs\templates\adr-template.md"
$adrDir = Join-Path $repoRoot "docs\adr"

if (-not (Test-Path $templatePath)) {
    Fail "ADR template not found at $templatePath."
}

if (-not (Test-Path $adrDir)) {
    New-Item -ItemType Directory -Path $adrDir | Out-Null
}

$existingNumbers = Get-ChildItem -Path $adrDir -Filter "*.md" -File -ErrorAction SilentlyContinue |
    ForEach-Object {
        if ($_.BaseName -match '^(\d{4})-') {
            [int]$matches[1]
        }
    }

$nextNumber = if ($existingNumbers) {
    "{0:D4}" -f ((($existingNumbers | Measure-Object -Maximum).Maximum) + 1)
} else {
    "0001"
}

$slug = $Title.ToLowerInvariant()
$slug = $slug -replace '[^a-z0-9]+', '-'
$slug = $slug -replace '(^-+|-+$)', ''

if ([string]::IsNullOrWhiteSpace($slug)) {
    Fail "Title '$Title' did not produce a valid ADR slug."
}

$outputPath = Join-Path $adrDir "$nextNumber-$slug.md"
if (Test-Path $outputPath) {
    Fail "ADR already exists at $outputPath."
}

$content = Get-Content $templatePath -Raw
$content = $content.Replace('{{ADR_NUMBER}}', $nextNumber)
$content = $content.Replace('{{ADR_TITLE}}', $Title)
$content = $content.Replace('{{ADR_DATE}}', (Get-Date -Format 'yyyy-MM-dd'))
$content = $content.Replace('{{ADR_STATUS}}', 'Proposed')

Set-Content -Path $outputPath -Value $content
Write-Host "Created ADR: $outputPath"
