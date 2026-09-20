# Downloads ONLY the head-up tilt recordings from the PhysioNet
# "Cerebral Vasoregulation in Elderly with Stroke" dataset (cves v1.0.0).
#
# Open Access, Open Data Commons Attribution License. No login, no fee.
# 136 records, about 2.9 GB, instead of the full 173.9 GB archive.
#
# Same laboratory, same rig and same protocol as the diabetes dataset already
# downloaded. Its headers declare 500 Hz, which is the external corroboration
# for the sampling-rate error found in the diabetes dataset.
#
# HOW TO RUN
#   Right click Start, choose "Windows PowerShell", paste:
#     powershell -ExecutionPolicy Bypass -File "<path to this file>"
#   Safe to stop and re-run, it resumes and skips what it already has.

$ErrorActionPreference = 'Stop'

$Dest = 'C:\Users\aarya\dysautonomia_data\cves'
$Base = 'https://physionet.org/files/cves/1.0.0'

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Write-Host "Destination: $Dest" -ForegroundColor Cyan

$curl = "$env:SystemRoot\System32\curl.exe"
if (-not (Test-Path $curl)) { throw "curl.exe not found. Tell Claude." }

function Get-One {
    param([string]$RelPath)
    $out = Join-Path $Dest ($RelPath -replace '/', '\')
    New-Item -ItemType Directory -Force -Path (Split-Path $out -Parent) | Out-Null
    & $curl -sS -f -L -C - -o $out "$Base/$RelPath"
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 33) {
        throw "Failed: $RelPath (curl exit $LASTEXITCODE)"
    }
    return $out
}

Write-Host "`nStep 1 of 2  metadata ..." -ForegroundColor Yellow
foreach ($m in @('RECORDS', 'LICENSE.txt', 'SHA256SUMS.txt')) {
    try { Get-One $m | Out-Null; Write-Host "  ok  $m" }
    catch { Write-Host "  skip $m" -ForegroundColor DarkGray }
}

$records = Get-Content (Join-Path $Dest 'RECORDS') |
           ForEach-Object { $_.Trim() } |
           Where-Object { $_ -match 'head-up-tilt' }

$total = $records.Count
Write-Host "`nStep 2 of 2  $total tilt recordings, roughly 2.9 GB ..." -ForegroundColor Yellow

$i = 0; $skipped = 0
foreach ($r in $records) {
    $i++
    $name = Split-Path $r -Leaf
    $datLocal = Join-Path $Dest (($r + '.dat') -replace '/', '\')

    $have = $false
    if (Test-Path $datLocal) {
        $localLen  = (Get-Item $datLocal).Length
        $remoteLen = (& $curl -sS -f -L -I "$Base/$r.dat" |
                      Select-String -Pattern '^content-length:\s*(\d+)' |
                      ForEach-Object { $_.Matches[0].Groups[1].Value } |
                      Select-Object -Last 1)
        if ($remoteLen -and [int64]$localLen -eq [int64]$remoteLen) { $have = $true }
    }

    if ($have) {
        $skipped++
        Write-Host ("  [{0,3}/{1}] {2}  already complete" -f $i, $total, $name) -ForegroundColor DarkGray
    } else {
        Get-One "$r.hea" | Out-Null
        Get-One "$r.dat" | Out-Null
        $mb = [math]::Round((Get-Item $datLocal).Length / 1MB, 1)
        Write-Host ("  [{0,3}/{1}] {2}  {3} MB" -f $i, $total, $name, $mb) -ForegroundColor Green
    }
}

Write-Host "`nVerifying ..." -ForegroundColor Yellow
$dats = Get-ChildItem -Path $Dest -Recurse -Filter '*.dat'
$heas = Get-ChildItem -Path $Dest -Recurse -Filter '*.hea'
$sizeGB = [math]::Round((($dats | Measure-Object Length -Sum).Sum) / 1GB, 2)
Write-Host "  .dat files : $($dats.Count) of $total"
Write-Host "  .hea files : $($heas.Count) of $total"
Write-Host "  total size : $sizeGB GB"
Write-Host "  skipped    : $skipped already present"

if ($dats.Count -eq $total -and $heas.Count -eq $total) {
    Write-Host "`nDone. Tell Claude the second dataset finished." -ForegroundColor Cyan
} else {
    Write-Host "`nSome files missing. Re-run, it will only fetch the gaps." -ForegroundColor Red
}
