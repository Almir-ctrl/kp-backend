$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$src = 'C:\Users\almir\AiMusicSeparator-Backend\server\scripts'
$destdir = Join-Path $src '_training_backups'
if (-not (Test-Path $destdir)) { New-Item -ItemType Directory -Path $destdir | Out-Null }
$patterns = @('whisper*','train_whisper*','prepare_whisper*','normalize*','dataset*','generate*','fetch_youtube*','batch_transcribe*','WHISPER_TRAINING_README*')
$files = Get-ChildItem -Path $src -File | Where-Object {
    $name = $_.Name
    foreach ($p in $patterns) { if ($name -like $p) { return $true } }
    return $false
}
if ($files.Count -eq 0) { Write-Output 'No training files matched patterns.'; exit 0 }
$zip = Join-Path $destdir ("training_backup_$ts.zip")
Write-Output "Creating backup: $zip"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$temp = Join-Path $env:TEMP ("training_backup_$ts")
if (Test-Path $temp) { Remove-Item -Recurse -Force $temp }
New-Item -ItemType Directory -Path $temp | Out-Null
foreach ($f in $files) { Copy-Item -Path $f.FullName -Destination (Join-Path $temp $f.Name) }
[System.IO.Compression.ZipFile]::CreateFromDirectory($temp, $zip)
Remove-Item -Recurse -Force $temp
Write-Output "Created backup at: $zip"
Get-ChildItem -Path $destdir -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Format-Table Name,Length,LastWriteTime -AutoSize
