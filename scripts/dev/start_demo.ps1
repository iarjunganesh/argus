# Start the ARGUS demo: the API, which runs every agent in-process, and the web UI.
# Usage: Open PowerShell in repo root and run: .\scripts\dev\start_demo.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Resolve-Path (Join-Path $scriptDir "../..")
Set-Location $repoRoot.Path

# Use the uv-managed environment created by `uv sync`.
$pythonExe = Join-Path $repoRoot.Path ".venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
	Write-Error "No .venv found. Run uv sync in the repository root first."
	exit 1
}
if (-not (Test-Path (Join-Path $repoRoot.Path "web/node_modules"))) {
	Write-Error "The web UI is not installed. Run npm ci --prefix web in the repository root first."
	exit 1
}

$ports = @(8000, 3000)
$procIds = @()

foreach ($port in $ports) {
	$lines = netstat -ano | Select-String ":$port"
	foreach ($line in $lines) {
		if ($line -notmatch "LISTENING") {
			continue
		}
		$parts = ($line.ToString() -split '\s+') | Where-Object { $_ -ne '' }
		if ($parts.Length -ge 5) {
			$procId = $parts[-1]
			if ($procId -match '^\d+$' -and [int]$procId -gt 4 -and [int]$procId -ne $PID) {
				$procIds += [int]$procId
			}
		}
	}
}

$procIds = $procIds | Sort-Object -Unique

if ($procIds.Count -gt 0) {
	Write-Host ("Killing existing processes on ARGUS ports: " + ($procIds -join ', '))
	foreach ($procId in $procIds) {
		try {
			taskkill /PID $procId /F | Out-Null
		} catch {
			Write-Host "Could not kill PID $procId" -ForegroundColor Yellow
		}
	}
} else {
	Write-Host "No existing listeners on ARGUS ports."
}

# The web UI calls the API from the browser, so the API must allow its origin.
$env:ARGUS_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
Write-Host "Starting ARGUS API (uvicorn) on port 8000..."
Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn argus.api.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $repoRoot.Path -NoNewWindow

Start-Sleep -Seconds 2
Write-Host "Starting the web UI (Next.js) on port 3000..."
Start-Process -FilePath "npm.cmd" -ArgumentList "--prefix web run dev" -WorkingDirectory $repoRoot.Path -NoNewWindow

Write-Host "Started the ARGUS API and web UI. Open http://localhost:3000."