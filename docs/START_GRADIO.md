# Start ARGUS Demo (Gradio + Full Stack)

Use this guide to start and stop the full ARGUS demo stack from PowerShell.

Prerequisites
- Python 3.14 installed and available on PATH
- Dependencies installed from `requirements.txt`

Start (one command)
1. From repo root run:

   ```powershell
   .\scripts\start_demo.ps1
   ```

2. This script first frees ARGUS ports (`8000-8005`, `7860`) and then starts:
- Identity agent (`8001`)
- Screening agent (`8002`)
- Corporate agent (`8003`)
- Transaction agent (`8004`)
- Compliance agent (`8005`)
- API gateway (`8000`)
- Gradio UI (`7860`)

3. Open `http://localhost:7860`.

Stop (one command)

```powershell
.\scripts\end_demo.ps1
```

Notes
- `start_demo.ps1` sets `PYTHONPATH` to the repository root before launching services.
- If Azure env vars are not set (`COSMOS_ENDPOINT`, `FOUNDRY_ENDPOINT`, `AZURE_SEARCH_ENDPOINT`), ARGUS uses mock fallbacks for local demo continuity.
