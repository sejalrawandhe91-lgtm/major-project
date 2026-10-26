# PowerShell Launcher for Land Acquisition and Management System (NLAMS)

$PythonExe = "C:\Users\mina2\AppData\Local\Programs\Python\Python313\python.exe"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

Write-Host "=========================================" -ForegroundColor Green
Write-Host "  Starting Land Acquisition System (NLAMS) " -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

# Check if database exists, if not, seed it
$DbFile = Join-Path $ProjectDir "land_acquisition.db"
if (-not (Test-Path $DbFile)) {
    Write-Host "Database not found. Seeding initial projects and parcels data..." -ForegroundColor Yellow
    & $PythonExe seed_data.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to seed database. Exiting."
        exit 1
    }
}

# Start Flask Backend API & Frontend static server in background
Write-Host "Starting Flask Server on http://127.0.0.1:5000..." -ForegroundColor Green
$FlaskProcess = Start-Process -FilePath $PythonExe -ArgumentList "app.py" -NoNewWindow -PassThru

# Wait for Flask to boot
Start-Sleep -Seconds 3

# Launch web browser
Write-Host "Opening dashboard in your web browser..." -ForegroundColor Green
Start-Process "http://127.0.0.1:5000/"

Write-Host "Press Ctrl+C in this PowerShell terminal to stop the server." -ForegroundColor Yellow

# Block terminal and wait for termination to clean up process
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "Shutting down Flask Server (PID: $($FlaskProcess.Id))..." -ForegroundColor Yellow
    Stop-Process -Id $FlaskProcess.Id -Force
    Write-Host "System shut down cleanly." -ForegroundColor Green
}
