$venvPath = 'C:\Users\almir\AiMusicSeparator-Backend\.venv\Scripts\python.exe'
Write-Host "Searching for processes referencing: $venvPath" -ForegroundColor Cyan
try {
    $procs = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.CommandLine -and $_.CommandLine -like "*${venvPath}*" }
    if ($procs) {
        foreach ($p in $procs) {
            [pscustomobject]@{
                ProcessId = $p.ProcessId
                Name = $p.Name
                CommandLine = $p.CommandLine
            }
        }
    } else {
        Write-Host "No matching processes found." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error querying processes: $_" -ForegroundColor Red
    exit 1
}