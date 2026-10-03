$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts/lib/CtzTools.ps1')
function Assert-True { param([bool]$Value, [string]$Message); if (-not $Value) { throw $Message } }
function Assert-Throws {
    param([scriptblock]$Action, [string]$Message)
    $threw = $false
    try { & $Action | Out-Null } catch { $threw = $true }
    Assert-True $threw $Message
}
$temp = Join-Path ([IO.Path]::GetTempPath()) ('ctz-tools-test-' + [Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($temp) | Out-Null
try {
    # Ensure every PowerShell file parses in the current interpreter (5.1 and 7).
    foreach ($file in Get-ChildItem -LiteralPath $root -Filter '*.ps1' -Recurse) {
        $tokens = $null; $parseErrors = $null
        [Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
        Assert-True (@($parseErrors).Count -eq 0) ('Parse failed: ' + $file.FullName)
        Assert-True (@([IO.File]::ReadAllBytes($file.FullName) | Where-Object { $_ -gt 127 }).Count -eq 0) 'PS1 must remain ASCII-only'
    }
    $profile = Read-CtzJson (Join-Path $root 'config/ctz-stock.json')
    $props = @{}
    foreach ($entry in $profile.required.PSObject.Properties) { $props[$entry.Name] = $entry.Value }
    $props['ro.product.cpu.abilist'] = 'arm64-v8a,armeabi-v7a,armeabi'
    $props['ro.serialno'] = 'PRIVATE-SERIAL-MUST-NOT-APPEAR'
    $valid = Get-CtzAssessment $props $profile 'test'
    Assert-True $valid.stockProfileMatched 'Exact stock profile should match'
    Assert-True (-not $valid.flashReady) 'No report may approve flashing'
    Assert-True (($valid | ConvertTo-Json -Depth 12) -notmatch 'PRIVATE-SERIAL') 'Private serial leaked'
    foreach ($entry in $profile.required.PSObject.Properties) {
        $wrong = $props.Clone(); $wrong[$entry.Name] = 'wrong'
        Assert-True (-not (Get-CtzAssessment $wrong $profile 'test').stockProfileMatched) ('Mismatch ignored: ' + $entry.Name)
        $missing = $props.Clone(); $missing.Remove($entry.Name)
        Assert-True (-not (Get-CtzAssessment $missing $profile 'test').stockProfileMatched) ('Missing ignored: ' + $entry.Name)
    }
    $wrongAbi = $props.Clone(); $wrongAbi['ro.product.cpu.abilist'] = 'not-arm64-v8a'
    Assert-True (-not (Get-CtzAssessment $wrongAbi $profile 'test').stockProfileMatched) 'ABI must match a token'
    Assert-True (-not (Get-CtzAssessment @{} $profile 'test').stockProfileMatched) 'Empty input matched'
    $parsed = ConvertFrom-CtzProperties "[ro.product.model]: [TAB-A05-BA1]`n[empty]: []`r`nx=y=z"
    Assert-True ($parsed['x'] -ceq 'y=z' -and $parsed['empty'] -ceq '') 'Property parsing failed'
    Assert-Throws { ConvertFrom-CtzProperties "x=1`nx=2" } 'Conflicting duplicate accepted'
    Assert-Throws { ConvertFrom-CtzProperties 'not a property' } 'Malformed input accepted'

    $lock = Read-CtzJson (Join-Path $root 'config/gsi-base.json')
    foreach ($variant in @('vanilla', 'gapps')) { Get-CtzAsset $lock $variant | Out-Null }
    $badLock = Read-CtzJson (Join-Path $root 'config/gsi-base.json')
    $badLock.assets.vanilla.url = 'https://example.invalid/payload'
    Assert-Throws { Get-CtzAsset $badLock 'vanilla' } 'Unapproved URL accepted'
    $xz = Join-Path $temp 'small.xz'
    [IO.File]::WriteAllBytes($xz, [byte[]]@(253, 55, 122, 88, 90, 0, 1, 2))
    $testAsset = [pscustomobject]@{ bytes = 8; sha256 = $null }
    $check = Test-CtzAssetFile $xz $testAsset
    Assert-True (-not $check.trustedDigestMatched -and $check.sha256.Length -eq 64) 'Unpinned hash claimed trusted'
    $testAsset.sha256 = $check.sha256
    Assert-True (Test-CtzAssetFile $xz $testAsset).trustedDigestMatched 'Pinned hash not checked'
    $testAsset.sha256 = '0' * 64
    Assert-Throws { Test-CtzAssetFile $xz $testAsset } 'Wrong hash accepted'
    $testAsset.bytes = 9
    Assert-Throws { Test-CtzAssetFile $xz $testAsset } 'Wrong size accepted'
    [IO.File]::WriteAllBytes($xz, [Text.Encoding]::ASCII.GetBytes('<html>!!'))
    $testAsset.bytes = 8; $testAsset.sha256 = $null
    Assert-Throws { Test-CtzAssetFile $xz $testAsset } 'HTML accepted as XZ'
    $saved = Join-Path $temp 'report.json'
    Save-CtzJson $valid $saved | Out-Null
    Assert-Throws { Save-CtzJson $valid $saved } 'Report overwrite accepted'

    # Full script tests run in a child process; no device or network is used.
    $engine = (Get-Process -Id $PID).Path
    $fixture = Join-Path $temp 'fixture.prop'
    $text = ($props.GetEnumerator() | ForEach-Object { $_.Key + '=' + $_.Value }) -join "`n"
    [IO.File]::WriteAllText($fixture, $text, [Text.UTF8Encoding]::new($false))
    $cliReport = Join-Path $temp 'cli.json'
    & $engine -NoProfile -File (Join-Path $root 'scripts/inspect-ctz.ps1') -PropertiesFile $fixture -OutputPath $cliReport -Language en
    Assert-True ($LASTEXITCODE -eq 0) 'Offline inspector failed'
    Assert-True (-not (Read-CtzJson $cliReport).flashReady) 'CLI approved flashing'
    [IO.File]::WriteAllText($fixture, 'ro.product.model=TAB-A05-BD')
    & $engine -NoProfile -File (Join-Path $root 'scripts/inspect-ctz.ps1') -PropertiesFile $fixture -OutputPath (Join-Path $temp 'mismatch.json') -Language en
    Assert-True ($LASTEXITCODE -eq 3) 'Wrong model exit code not 3'
    & $engine -NoProfile -File (Join-Path $root 'scripts/fetch-android10-gsi.ps1') -PlanOnly -Destination (Join-Path $temp 'no-download') -Language ja
    Assert-True ($LASTEXITCODE -eq 0) 'PlanOnly failed'
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $temp 'no-download'))) 'PlanOnly created files'
    $emptyBin = Join-Path $temp 'missing-adb.exe'
    & $engine -NoProfile -File (Join-Path $root 'scripts/inspect-ctz.ps1') -AdbPath $emptyBin -Language en
    Assert-True ($LASTEXITCODE -eq 1) 'Missing adb did not fail'
    Write-Host 'All PowerShell offline tests passed.'
} finally {
    # Only the unique directory created by this test is removed.
    Remove-Item -LiteralPath $temp -Recurse -Force
}
# All asserted negative subprocess cases passed; do not leak their exit code.
exit 0
