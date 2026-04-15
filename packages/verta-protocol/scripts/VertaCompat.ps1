Set-StrictMode -Version Latest

function Get-VertaEnvValue {
    param([Parameter(Mandatory = $true)][string]$Name)

    $entry = Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue
    if ($null -eq $entry) {
        return $null
    }
    return $entry.Value
}

function Sync-VertaGlobalEnv {}

function Sync-VertaRolloutReadinessEnv {
    Sync-VertaGlobalEnv
}

function Sync-VertaPhaseIEnv {
    Sync-VertaGlobalEnv
}

function Sync-VertaPhaseNEnv {
    Sync-VertaGlobalEnv
}

function Sync-VertaPhaseJEnv {
    Sync-VertaGlobalEnv
}

function Sync-VertaPhaseLEnv {
    Sync-VertaPhaseIEnv
    Sync-VertaPhaseJEnv
}

function Sync-VertaPhaseMEnv {
    Sync-VertaPhaseLEnv
}

function Sync-VertaReleaseEvidenceEnv {
    Sync-VertaGlobalEnv
}

function Get-VertaTargetRoot {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    $targetRoot = Get-VertaEnvValue "VERTA_TARGET_ROOT"
    if ([string]::IsNullOrWhiteSpace($targetRoot)) {
        return (Join-Path $RepoRoot "target\verta")
    }
    return $targetRoot
}

function Get-VertaOutputPath {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$LeafName
    )

    return (Join-Path (Get-VertaTargetRoot $RepoRoot) $LeafName)
}

function Get-VertaLegacyOutputPath {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$LeafName
    )

    return (Get-VertaOutputPath $RepoRoot $LeafName)
}

function Resolve-VertaPreferredPath {
    param(
        [Parameter(Mandatory = $true)][string]$PrimaryPath,
        [Parameter(Mandatory = $true)][string]$FallbackPath
    )

    if (Test-Path $PrimaryPath) {
        return $PrimaryPath
    }
    return $FallbackPath
}

function Copy-VertaCanonicalOutputToLegacy {
    param(
        [Parameter(Mandatory = $true)][string]$ActualPath,
        [Parameter(Mandatory = $true)][string]$CanonicalDefaultPath,
        [Parameter(Mandatory = $true)][string]$LegacyDefaultPath
    )

    return
}
