# Start full ARGUS demo stack (agents + API + Gradio) in one command.
# Usage: Open PowerShell in repo root and run: .\scripts\start_demo.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$env:PYTHONPATH = $repoRoot.Path
Set-Location $repoRoot.Path

# Use the uv-managed environment created by `uv sync`.
$pythonExe = Join-Path $repoRoot.Path ".venv/Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
	Write-Error "No .venv found. Run uv sync in the repository root first."{nl}	exit 1{nl}}}

$ports = @(8000, 8001, 8002, 8003, 8004, 8005, 7860)
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

Write-Host "Starting Identity agent on 8001..."
Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn argus.agents.identity.agent:app --host 127.0.0.1 --port 8001" -WorkingDirectory $repoRoot.Path -NoNewWindow

Write-Host "Starting Screening agent on 8002..."
Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn argus.agents.screening.agent:app --host 127.0.0.1 --port 8002" -WorkingDirectory $repoRoot.Path -NoNewWindow

Write-Host "Starting Corporate agent on 8003..."
Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn argus.agents.corporate.agent:app --host 127.0.0.1 --port 8003" -WorkingDirectory $repoRoot.Path -NoNewWindow

Write-Host "Starting Transaction agent on 8004..."
Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn argus.agents.transaction.agent:app --host 127.0.0.1 --port 8004" -WorkingDirectory $repoRoot.Path -NoNewWindow

Write-Host "Starting Compliance agent on 8005..."
Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn argus.agents.compliance.agent:app --host 127.0.0.1 --port 8005" -WorkingDirectory $repoRoot.Path -NoNewWindow

Start-Sleep -Seconds 2
Write-Host "Starting ARGUS API (uvicorn) on port 8000..."
Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn argus.api.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $repoRoot.Path -NoNewWindow

Start-Sleep -Seconds 2
Write-Host "Starting Gradio UI (argus.ui.gradio_app)..."
Start-Process -FilePath $pythonExe -ArgumentList "-m argus.ui.gradio_app" -WorkingDirectory $repoRoot.Path -NoNewWindow

Write-Host "Started ARGUS agents, API, and UI. Open http://localhost:7860 for Gradio."