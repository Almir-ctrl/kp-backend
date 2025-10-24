param()

$files = Get-ChildItem -Path 'tests' -Filter *.py -File -Recurse
foreach ($file in $files) {
    $path = $file.FullName
    try {
        $text = Get-Content -Path $path -Raw -ErrorAction Stop
    } catch {
        Write-Output "skip $path (read error)"
        continue
    }
    $lines = $text -split "\r?\n"
    $trimmed = $lines | ForEach-Object { $_.TrimEnd() }
    while ($trimmed.Count -gt 0 -and $trimmed[-1] -eq '') { $trimmed = $trimmed[0..($trimmed.Count-2)] }
    $new = ($trimmed -join "`n") + "`n"
    if ($new -ne $text) {
        Set-Content -Path $path -Value $new -Encoding utf8
        Write-Output "fixed $path"
    }
}
