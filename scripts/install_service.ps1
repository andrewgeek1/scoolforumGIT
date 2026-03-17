# Установка как служба Windows
$appPath = (Get-Location).Path
$pythonPath = (Get-Command python).Source

# Создаем задачу в планировщике
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "$appPath\app.py --auto-run --port 5000"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "SchoolApp" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Школьная социальная сеть на testingfm.ru"

Write-Host "✅ Служба установлена и будет запускаться автоматически" -ForegroundColor Green