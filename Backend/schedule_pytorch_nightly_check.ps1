# PowerShell script to schedule daily PyTorch Nightly CUDA 12.4 check with email notification
# Edit the variables below before running!

$pythonPath = "C:\Users\almir\.venv\Scripts\python.exe"  # Path to your Python interpreter
$scriptPath = "C:\Users\almir\AiMusicSeparator-Backend\check_pytorch_nightly_match_notify.py"
$email = "almir.agovich@outlook.com"
$smtpServer = "smtp.office365.com"
$smtpPort = 587
$smtpUser = "almir.agovich@outlook.com"
$smtpPass = "yourpass"
$taskName = "Check PyTorch Nightly CUDA 12.4"
$startIn = "C:\Users\almir\AiMusicSeparator-Backend"
$time = "09:00"  # 24-hour format

# Build arguments
$args = "`"$scriptPath`" --email $email --smtp-server $smtpServer --smtp-port $smtpPort --smtp-user $smtpUser --smtp-pass $smtpPass"

# Remove existing task if present
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Register new scheduled task
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $args -WorkingDirectory $startIn
$trigger = New-ScheduledTaskTrigger -Daily -At $time
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName $taskName -Description "Checks for new matching PyTorch Nightly CUDA 12.4 builds and emails if found." -User "$env:USERNAME" -RunLevel Highest

Write-Host "Scheduled task '$taskName' created. It will run daily at $time and notify $email if a new set is found." -ForegroundColor Green
