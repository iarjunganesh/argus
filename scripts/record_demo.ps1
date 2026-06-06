<#
ARGUS Demo Recording Helper

Run this script while recording your screen. It executes the sequence used in the demo
with reasonable pauses. Adjust Sleep durations if you want slower/faster recording.

Usage: Open PowerShell and run:
  .\scripts\record_demo.ps1
#>

Write-Output "1) Show infra outputs (Bicep deployment outputs)"
Write-Output "   (If you didn't save outputs earlier, skip this step.)"
Start-Sleep -Seconds 2

Write-Output "2) Start API gateway"
Start-Process -NoNewWindow -FilePath "C:\Users\arjunganesh\AppData\Local\Python\pythoncore-3.14-64\python.exe" -ArgumentList '-m uvicorn api.main:app --port 8000 --reload'
Start-Sleep -Seconds 4

Write-Output "3) Start agents (each in separate terminals during the live demo)"
Start-Process -NoNewWindow -FilePath "C:\Users\arjunganesh\AppData\Local\Python\pythoncore-3.14-64\python.exe" -ArgumentList '-m uvicorn agents.identity.agent:app --port 8001 --reload'
Start-Process -NoNewWindow -FilePath "C:\Users\arjunganesh\AppData\Local\Python\pythoncore-3.14-64\python.exe" -ArgumentList '-m uvicorn agents.screening.agent:app --port 8002 --reload'
Start-Process -NoNewWindow -FilePath "C:\Users\arjunganesh\AppData\Local\Python\pythoncore-3.14-64\python.exe" -ArgumentList '-m uvicorn agents.corporate.agent:app --port 8003 --reload'
Start-Process -NoNewWindow -FilePath "C:\Users\arjunganesh\AppData\Local\Python\pythoncore-3.14-64\python.exe" -ArgumentList '-m uvicorn agents.compliance.agent:app --port 8004 --reload'
Start-Process -NoNewWindow -FilePath "C:\Users\arjunganesh\AppData\Local\Python\pythoncore-3.14-64\python.exe" -ArgumentList '-m uvicorn agents.transaction.agent:app --port 8005 --reload'
Start-Sleep -Seconds 6

Write-Output "4) Launch UI"
Start-Process -NoNewWindow -FilePath "C:\Users\arjunganesh\AppData\Local\Python\pythoncore-3.14-64\python.exe" -ArgumentList 'ui/gradio_app.py'
Start-Sleep -Seconds 3

Write-Output "5) Submit a KYC request via API (example)"
$body = @{ entity_name='Demo Co'; entity_type='corporate'; jurisdiction='SE'; include_transaction_analysis=$true } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/kyc/assess -Method Post -Body $body -ContentType 'application/json'
Start-Sleep -Seconds 4

Write-Output "6) Show the generated report via API (poll or fetch)"
Write-Output "Use: Invoke-RestMethod http://127.0.0.1:8000/api/v1/kyc/report/<report_id>"

Write-Output "Demo helper finished. Close the demo when recording is complete."
