[CmdletBinding()]
param(
    [ValidateSet('vanilla', 'gapps')][string]$Variant = 'vanilla',
    [string]$Destination = '',
    [switch]$PlanOnly,
    [ValidateSet('ja', 'en')][string]$Language = 'ja'
)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'lib/CtzTools.ps1')
    $root = Split-Path -Parent $PSScriptRoot
    $ui = Read-CtzJson (Join-Path $root ('config/ui.' + $Language + '.json'))
    $lock = Read-CtzJson (Join-Path $root 'config/gsi-base.json')
    $asset = Get-CtzAsset $lock $Variant
    Write-Host $ui.downloadIntro
    if ($Variant -ceq 'gapps') { Write-Warning $ui.gappsWarning }
    Write-Host ($asset.name + ' (' + $asset.bytes + ' bytes)')
    Write-Host $asset.url
    if ($PlanOnly) { Write-Host $ui.planOnly; exit 0 }
    if (-not $Destination) { $Destination = Join-Path $root 'downloads' }
    $destinationPath = [IO.Path]::GetFullPath($Destination)
    [IO.Directory]::CreateDirectory($destinationPath) | Out-Null
    $output = Join-Path $destinationPath $asset.name
    if (Test-Path -LiteralPath $output) {
        Write-Host $ui.existingDownload
        $validation = Test-CtzAssetFile $output $asset
    } else {
        # Verify live metadata, but never replace the local lock with live values.
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $headers = @{ 'User-Agent' = 'CTZ-Android10-Preparation'; 'Accept' = 'application/vnd.github+json' }
        $release = Invoke-RestMethod -Uri ('https://api.github.com/repos/' + $lock.repository + '/releases/tags/' + $lock.release) -Headers $headers
        $live = @($release.assets | Where-Object { $_.name -ceq $asset.name })
        if ($release.tag_name -cne $lock.release -or $live.Count -ne 1 -or
            $live[0].size -ne $asset.bytes -or $live[0].browser_download_url -cne $asset.url) {
            throw 'Upstream metadata differs from pinned asset. Review the lock first.'
        }
        $temporary = Join-Path $destinationPath ($asset.name + '.' + [Guid]::NewGuid().ToString('N') + '.partial')
        # A unique partial file is retained on failure for diagnosis.
        Invoke-WebRequest -UseBasicParsing -Uri $asset.url -OutFile $temporary -Headers $headers
        $validation = Test-CtzAssetFile $temporary $asset
        # File.Move refuses to replace an existing final download.
        [IO.File]::Move($temporary, $output)
    }
    if (-not $validation.trustedDigestMatched) { Write-Warning $ui.hashWarning }
    $receipt = [pscustomobject]@{
        schemaVersion = 1; upstreamRepository = $lock.repository
        release = $lock.release; asset = $asset.name; url = $asset.url
        bytes = [long]$asset.bytes; sha256 = $validation.sha256
        trustedDigestMatched = $validation.trustedDigestMatched
        downloadedAtUtc = [DateTime]::UtcNow.ToString('o')
        status = $lock.status; flashReady = $false
    }
    $receiptPath = Join-Path $destinationPath ($asset.name + '.' + [Guid]::NewGuid().ToString('N') + '.receipt.json')
    $saved = Save-CtzJson $receipt $receiptPath
    Write-Host ($ui.downloadSaved -f $saved)
    Write-Host $ui.extractHint
    Write-Host $ui.noFlash
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
