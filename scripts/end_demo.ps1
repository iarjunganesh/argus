# Stop ARGUS demo services (PowerShell)
# Usage: Open PowerShell in repo root and run: .\scripts\end_demo.ps1

$ports = @(8000, 8001, 8002, 8003, 8004, 8005, 7860)
$procIds = @()
$selfPid = $PID

foreach ($port in $ports) {
    $lines = netstat -ano | Select-String "LISTENING" | Select-String ":$port"
    foreach ($line in $lines) {
        $parts = ($line.ToString() -split '\s+') | Where-Object { $_ -ne '' }
        if ($parts.Length -ge 5) {
            $procId = $parts[-1]
            if ($procId -match '^\d+$') {
                $intPid = [int]$procId
                if ($intPid -gt 4 -and $intPid -ne $selfPid) {
                    $procIds += $intPid
                }
            }
        }
    }
}

$procIds = $procIds | Sort-Object -Unique

if ($procIds.Count -eq 0) {
    Write-Host "No ARGUS listeners found on ports: $($ports -join ', ')"
    exit 0
}

Write-Host ("Stopping ARGUS processes on ports $($ports -join ', '): " + ($procIds -join ', '))
foreach ($procId in $procIds) {
    try {
        taskkill /PID $procId /F | Out-Null
        Write-Host "Stopped PID $procId"
    } catch {
        Write-Host "Failed to stop PID $procId" -ForegroundColor Yellow
    }
}

Write-Host "ARGUS demo services stop sequence complete."
