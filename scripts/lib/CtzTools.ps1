# ASCII-only source: Windows PowerShell 5.1 also parses this without a BOM.
Set-StrictMode -Version Latest

function Read-CtzJson {
    param([Parameter(Mandatory = $true)][string]$Path)
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function ConvertFrom-CtzProperties {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text)
    $props = @{}
    foreach ($line in ($Text -split '\r?\n')) {
        $line = $line.Trim().TrimStart([char]0xFEFF)
        if ($line.Length -eq 0 -or $line.StartsWith('#')) { continue }
        if ($line -match '^\[([^\]]+)\]:\s*\[(.*)\]$') {
            $key = $Matches[1]; $value = $Matches[2]
        } elseif ($line -match '^([^=\s]+)=(.*)$') {
            $key = $Matches[1]; $value = $Matches[2]
        } else {
            throw 'Malformed property input; expected adb getprop or key=value.'
        }
        if ($props.ContainsKey($key) -and $props[$key] -cne $value) {
            throw ('Conflicting duplicate property: ' + $key)
        }
        $props[$key] = $value
    }
    return $props
}

function Get-CtzAssessment {
    param([hashtable]$Properties, [object]$Profile, [string]$InputSource)
    $checks = @()
    $selected = [ordered]@{}
    foreach ($entry in $Profile.required.PSObject.Properties) {
        $actual = $Properties[$entry.Name]
        $selected[$entry.Name] = $actual
        $checks += [pscustomobject]@{
            property = $entry.Name; expected = $entry.Value; actual = $actual
            matched = ($null -ne $actual -and $actual -ceq $entry.Value)
        }
    }
    $abis = $Properties['ro.product.cpu.abilist']
    $checks += [pscustomobject]@{
        property = 'ro.product.cpu.abilist'; expected = $Profile.abiToken
        actual = $abis; matched = (($abis -split ',') -ccontains $Profile.abiToken)
    }
    foreach ($key in $Profile.observational) { $selected[$key] = $Properties[$key] }
    $matched = (@($checks | Where-Object { -not $_.matched }).Count -eq 0)
    $status = 'identity-mismatch-or-missing'
    if ($matched) { $status = 'stock-profile-matched-candidate-only' }
    return [pscustomobject]@{
        schemaVersion = 1; target = $Profile.target
        generatedAtUtc = [DateTime]::UtcNow.ToString('o')
        inputSource = $InputSource; status = $status
        stockProfileMatched = $matched; flashReady = $false
        candidate = $Profile.candidate; checks = $checks; properties = $selected
        unverified = @('partition sizes', 'stock backup and restore',
            'bootloader unlock state', 'AVB policy', 'kernel compatibility',
            'touch panel variant', 'real-device Android 10 boot')
    }
}

function Save-CtzJson {
    param([object]$Value, [string]$Path)
    $absolute = [IO.Path]::GetFullPath($Path)
    $parent = [IO.Path]::GetDirectoryName($absolute)
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    # CreateNew refuses to overwrite an earlier report or receipt.
    $stream = [IO.File]::Open($absolute, [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $bytes = [Text.UTF8Encoding]::new($false).GetBytes(
            ($Value | ConvertTo-Json -Depth 12) + [Environment]::NewLine)
        $stream.Write($bytes, 0, $bytes.Length)
    } finally { $stream.Dispose() }
    return $absolute
}

function Get-CtzAsset {
    param([object]$Lock, [string]$Variant)
    if ($Lock.repository -cne 'phhusson/treble_experimentations' -or
        $Lock.release -cne 'v222' -or $Lock.androidVersion -cne '10') {
        throw 'Unsupported upstream release in GSI lock.'
    }
    if (@('vanilla', 'gapps') -cnotcontains $Variant) { throw 'Unknown variant.' }
    $asset = $Lock.assets.PSObject.Properties[$Variant].Value
    $expectedName = 'system-quack-arm64-ab-' + $Variant + '.img.xz'
    $expectedUrl = 'https://github.com/phhusson/treble_experimentations/releases/download/v222/' + $expectedName
    if ($asset.name -cne $expectedName -or $asset.url -cne $expectedUrl -or
        [long]$asset.bytes -le 0) { throw 'Unsafe or inconsistent asset lock.' }
    if ($null -ne $asset.sha256 -and $asset.sha256 -notmatch '^[0-9a-fA-F]{64}$') {
        throw 'Invalid SHA256 in lock.'
    }
    return $asset
}

function Test-CtzAssetFile {
    param([string]$Path, [object]$Asset)
    $file = Get-Item -LiteralPath $Path
    if ($file.Length -ne [long]$Asset.bytes) { throw 'Downloaded byte count differs from upstream metadata.' }
    $stream = [IO.File]::OpenRead($file.FullName)
    try {
        $magic = New-Object byte[] 6
        if ($stream.Read($magic, 0, 6) -ne 6 -or
            [BitConverter]::ToString($magic) -cne 'FD-37-7A-58-5A-00') {
            throw 'Not an XZ file; an HTML error page may have been downloaded.'
        }
    } finally { $stream.Dispose() }
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $verified = $false
    if ($null -ne $Asset.sha256) {
        if ($hash -cne $Asset.sha256.ToLowerInvariant()) { throw 'SHA256 mismatch.' }
        $verified = $true
    }
    return [pscustomobject]@{ sha256 = $hash; trustedDigestMatched = $verified }
}
