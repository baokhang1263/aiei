
# Setup script for Windows PowerShell
# Usage: Right-click -> Run with PowerShell (or run inside PowerShell from project folder)

Write-Host "=== Internal Chat Setup (Windows) ==="

# Ensure we're in project folder (user should run this inside project).
# 1) Activate venv
if (!(Test-Path ".venv")) {
    Write-Host "Creating virtual environment .venv ..."
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create venv"; exit 1 }
}

Write-Host "Activating .venv ..."
. ".\.venv\Scripts\Activate.ps1"

# 2) Install requirements
Write-Host "Installing requirements ..."
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }

# 3) Set FLASK_APP
$env:FLASK_APP = "app.py"
Write-Host "FLASK_APP set to app.py"

# 4) Initialize DB
Write-Host "Initializing database ..."
python -m flask init-db
if ($LASTEXITCODE -ne 0) { Write-Error "flask init-db failed"; exit 1 }

# 5) Create first user
Write-Host "Creating first user ..."
python -m flask create-user
if ($LASTEXITCODE -ne 0) { Write-Error "flask create-user failed"; exit 1 }

Write-Host "`nAll good! Now run:"
Write-Host "    $env:SECRET_KEY='a-very-long-secret' ; python app.py"
Write-Host "Then open http://localhost:5000"
