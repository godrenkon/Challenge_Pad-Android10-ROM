[CmdletBinding()]
param(
    [string]$AdbPath = 'adb',
    [string]$Serial = '',
    [string]$PropertiesFile = '',
    [string]$OutputPath = '',
    [ValidateSet('ja', 'en')][string]$Language = 'ja'
)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'lib/CtzTools.ps1')
    $root = Split-Path -Parent $PSScriptRoot
    $ui = Read-CtzJson (Join-Path $root ('config/ui.' + $Language + '.json'))
    $profile = Read-CtzJson (Join-Path $root 'config/ctz-stock.json')
    Write-Host $ui.inspectIntro
    if ($PropertiesFile) {
        if ($Serial) { throw 'PropertiesFile and Serial are mutually exclusive.' }
        $raw = Get-Content -LiteralPath $PropertiesFile -Raw -Encoding UTF8
        $source = 'offline-properties'
    } else {
        $adb = (Get-Command $AdbPath -CommandType Application -ErrorAction Stop).Source
        $lines = @(& $adb devices)
        if ($LASTEXITCODE -ne 0) { throw 'adb devices failed.' }
        $attached = @()
        foreach ($line in $lines) {
            if ($line -match '^(\S+)\s+(device|offline|unauthorized)\s*$') {
                $attached += [pscustomobject]@{ serial = $Matches[1]; state = $Matches[2] }
            }
        }
        if ($Serial) {
            $attached = @($attached | Where-Object { $_.serial -ceq $Serial })
        }
        if ($attached.Count -ne 1 -or $attached[0].state -cne 'device') {
            throw $ui.adbSelectionError
        }
        $raw = (@(& $adb -s $attached[0].serial shell getprop) -join "`n")
        if ($LASTEXITCODE -ne 0) { throw 'adb shell getprop failed.' }
        # Do not store serial numbers, MAC addresses, or the full getprop dump.
        $source = 'adb-read-only'
    }
    $properties = ConvertFrom-CtzProperties $raw
    $report = Get-CtzAssessment $properties $profile $source
    if (-not $OutputPath) {
        $OutputPath = Join-Path $root ('artifacts/ctz-report-' + [Guid]::NewGuid().ToString('N') + '.json')
    }
    $saved = Save-CtzJson $report $OutputPath
    Write-Host ($ui.reportSaved -f $saved)
    Write-Host $ui.noFlash
    if (-not $report.stockProfileMatched) {
        Write-Host $ui.profileMismatch
        exit 3
    }
    Write-Host $ui.profileMatched
    exit 0
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
