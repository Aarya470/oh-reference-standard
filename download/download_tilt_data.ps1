# Downloads ONLY the head-up tilt recordings from the PhysioNet
# "Cerebral Vasoregulation in Diabetes" dataset (v1.0.0).
#
# Open Access, CC-BY 4.0. No login, no application, no fee.
# 116 records, about 810 MB, instead of the full 3.0 GB archive.
#
# HOW TO RUN
#   1. Right click the Start button, choose "Windows PowerShell"
#   2. Paste this, press Enter:
#        powershell -ExecutionPolicy Bypass -File "<path to this file>"
#   3. Leave it running. Safe to stop and re-run, it resumes.

$ErrorActionPreference = 'Stop'

$Dest = 'C:\Users\aarya\dysautonomia_data'
$Base = 'https://physionet.org/files/cerebral-vasoreg-diabetes/1.0.0'

# ---------------------------------------------------------------- setup
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Write-Host "Destination: $Dest" -ForegroundColor Cyan

$curl = "$env:SystemRoot\System32\curl.exe"
if (-not (Test-Path $curl)) { throw "curl.exe not found. Tell Claude and he will switch methods." }

function Get-One {
    param([string]$RelPath)
    $out = Join-Path $Dest ($RelPath -replace '/', '\')
    $dir = Split-Path $out -Parent
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    # -C - resumes a partial file, -f fails loudly on HTTP errors
    & $curl -sS -f -L -C - -o $out "$Base/$RelPath"
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 33) {
        throw "Failed: $RelPath (curl exit $LASTEXITCODE)"
    }
    return $out
}

# ------------------------------------------------- small metadata files
$meta = @(
    'RECORDS',
    'LICENSE.txt',
    'SHA256SUMS.txt',
    'GE-71_Protocol.pdf',
    'Data_Description/GE-71_Data_Dictionary.csv',
    'Data_Description/GE-71_Data_Summary_Table.csv',
    'Data_Description/GE-71_File_and_channels.csv',
    'Data_Description/GE-71_Files_Per_Subject.csv',
    'Data_Description/GE-71_Head-up-tilt-Day1_Markers_per_subject.csv',
    'Data_Description/GE-71_Head-up-tilt-Day2_Markers_per_subject.csv'
)

Write-Host "`nStep 1 of 2  metadata ..." -ForegroundColor Yellow
foreach ($m in $meta) { Get-One $m | Out-Null; Write-Host "  ok  $m" }

# --------------------------------------------------- the tilt recordings
$records = Get-Content (Join-Path $Dest 'RECORDS') |
           ForEach-Object { $_.Trim() } |
           Where-Object { $_ -match 'Head-up-tilt' }

$total = $records.Count
Write-Host "`nStep 2 of 2  $total tilt recordings, roughly 810 MB ..." -ForegroundColor Yellow
if ($total -ne 116) { Write-Host "  note: expected 116, found $total" -ForegroundColor Magenta }

$i = 0
$skipped = 0
foreach ($r in $records) {
    $i++
    $name = Split-Path $r -Leaf
    $datLocal = Join-Path $Dest (($r + '.dat') -replace '/', '\')

    # skip if we already have the full file
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

# ------------------------------------------------------------ verify
Write-Host "`nVerifying ..." -ForegroundColor Yellow
$dats = Get-ChildItem -Path $Dest -Recurse -Filter '*.dat' |
        Where-Object { $_.FullName -match 'Head-up-tilt' }
$heas = Get-ChildItem -Path $Dest -Recurse -Filter '*.hea' |
        Where-Object { $_.FullName -match 'Head-up-tilt' }
$sizeGB = [math]::Round((($dats | Measure-Object Length -Sum).Sum) / 1GB, 2)

Write-Host "  .dat files : $($dats.Count) of $total"
Write-Host "  .hea files : $($heas.Count) of $total"
Write-Host "  total size : $sizeGB GB"
Write-Host "  skipped    : $skipped already present"

$empty = $dats | Where-Object { $_.Length -lt 100000 }
if ($empty) {
    Write-Host "`n  WARNING, these look truncated, re-run this script:" -ForegroundColor Red
    $empty | ForEach-Object { Write-Host "    $($_.Name)  $($_.Length) bytes" }
} elseif ($dats.Count -eq $total -and $heas.Count -eq $total) {
    Write-Host "`nDone. Everything is here." -ForegroundColor Cyan
    Write-Host "Tell Claude the download finished." -ForegroundColor Cyan
} else {
    Write-Host "`nSome files are missing. Re-run this script, it will only fetch the gaps." -ForegroundColor Red
}
