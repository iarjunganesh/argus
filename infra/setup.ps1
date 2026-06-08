# ============================================================
# ARGUS — Azure Infrastructure Setup Script (PowerShell)
# Microsoft Agents League Hackathon 2026
#
# Usage:
#   cd c:\ws\argus
#   .\infra\setup.ps1
#
# Prerequisites:
#   - Azure CLI installed: winget install Microsoft.AzureCLI
#   - Logged in: az login
#   - Azure OpenAI access approved: https://aka.ms/oai/access
# ============================================================

param(
    [string]$ResourceGroup = "argus-rg",
    [string]$Location      = "swedencentral",
    [string]$Prefix        = "argus"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       ARGUS — Azure Infrastructure Setup            ║" -ForegroundColor Cyan
Write-Host "║       Microsoft Agents League Hackathon 2026        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Verify Azure CLI login ─────────────────────────────────────────
Write-Host "[1/7] Checking Azure CLI login..." -ForegroundColor Yellow
$account = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Not logged in. Running az login..." -ForegroundColor Yellow
    az login
}
$subscriptionId = (az account show --query id -o tsv)
$tenantId       = (az account show --query tenantId -o tsv)
Write-Host "  ✅ Logged in. Subscription: $subscriptionId" -ForegroundColor Green

# ── Step 2: Create Resource Group ──────────────────────────────────────────
Write-Host "[2/7] Creating resource group '$ResourceGroup' in '$Location'..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location --output none
Write-Host "  ✅ Resource group ready." -ForegroundColor Green

# ── Step 3: Deploy Bicep ────────────────────────────────────────────────────
Write-Host "[3/7] Deploying Azure resources (this takes 5-10 minutes)..." -ForegroundColor Yellow
Write-Host "       Provisioning: AI Foundry, OpenAI (GPT-4o), AI Search, Cosmos DB, Doc Intelligence" -ForegroundColor Gray

$deployOutput = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file "$PSScriptRoot\main.bicep" `
    --parameters prefix=$Prefix location=$Location `
    --query properties.outputs `
    --output json

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Deployment failed. Common issues:" -ForegroundColor Red
    Write-Host "     - Azure OpenAI access not approved: https://aka.ms/oai/access" -ForegroundColor Red
    Write-Host "     - Cosmos DB free tier already used in this subscription" -ForegroundColor Red
    Write-Host "     - AI Search service already exists in this subscription" -ForegroundColor Red
    Write-Host "  Raw error:" -ForegroundColor Red
    Write-Host $deployOutput -ForegroundColor Red
    exit 1
}

$outputs = $deployOutput | ConvertFrom-Json
Write-Host "  ✅ All Azure resources deployed." -ForegroundColor Green

# ── Step 4: Get API Keys ────────────────────────────────────────────────────
Write-Host "[4/7] Retrieving API keys..." -ForegroundColor Yellow

$openaiEndpoint = $outputs.AZURE_OPENAI_ENDPOINT.value
$searchEndpoint = $outputs.AZURE_SEARCH_ENDPOINT.value
$cosmosEndpoint = $outputs.COSMOS_ENDPOINT.value
$docAiEndpoint  = $outputs.DOC_INTELLIGENCE_ENDPOINT.value
$projectName    = $outputs.AI_PROJECT_NAME.value

# Get resource names from outputs to fetch keys
$openaiName   = ($openaiEndpoint -replace 'https://', '' -replace '\.openai\.azure\.com.*', '')
$searchName   = ($searchEndpoint -replace 'https://', '' -replace '\.search\.windows\.net', '')
$cosmosName   = ($cosmosEndpoint -replace 'https://', '' -replace '\.documents\.azure\.com.*', '')
$docAiName    = ($docAiEndpoint -replace 'https://', '' -replace '\.cognitiveservices\.azure\.com.*', '')

$openaiKey    = (az cognitiveservices account keys list --name $openaiName --resource-group $ResourceGroup --query key1 -o tsv)
$searchKey    = (az search service admin-key list --search-service-name $searchName --resource-group $ResourceGroup --query primaryKey -o tsv)
$cosmosKey    = (az cosmosdb keys list --name $cosmosName --resource-group $ResourceGroup --query primaryMasterKey -o tsv)
$docAiKey     = (az cognitiveservices account keys list --name $docAiName --resource-group $ResourceGroup --query key1 -o tsv)

# Get Foundry Project endpoint
$foundryEndpoint = (az ml workspace show --name $projectName --resource-group $ResourceGroup --query discovery_url -o tsv 2>$null)
if (-not $foundryEndpoint) {
    # Fallback format if az ml not available
    $foundryEndpoint = "https://$projectName.api.azureml.ms"
    Write-Host "  ⚠️  Could not auto-detect Foundry endpoint. Check Azure portal." -ForegroundColor Yellow
    Write-Host "     Go to: AI Foundry Portal → $projectName → Settings → Project details" -ForegroundColor Yellow
}

Write-Host "  ✅ API keys retrieved." -ForegroundColor Green

# ── Step 5: Generate .env file ──────────────────────────────────────────────
Write-Host "[5/7] Writing .env file..." -ForegroundColor Yellow

$envContent = @"
# ─────────────────────────────────────────────
# ARGUS — Environment Variables
# Generated by infra/setup.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm')
# DO NOT COMMIT THIS FILE TO GIT
# ─────────────────────────────────────────────

# ── Azure AI Foundry ──────────────────────────
FOUNDRY_ENDPOINT=$foundryEndpoint
FOUNDRY_PROJECT_NAME=$projectName
AZURE_SUBSCRIPTION_ID=$subscriptionId
AZURE_RESOURCE_GROUP=$ResourceGroup

# ── Azure OpenAI ──────────────────────────────
AZURE_OPENAI_ENDPOINT=$openaiEndpoint
AZURE_OPENAI_API_KEY=$openaiKey
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# ── GitHub Models (dev fallback — set true to skip Azure OpenAI) ──
GITHUB_TOKEN=<your-github-pat>
USE_GITHUB_MODELS=false

# ── Azure AI Search (Foundry IQ backing store) ──
AZURE_SEARCH_ENDPOINT=$searchEndpoint
AZURE_SEARCH_API_KEY=$searchKey

# ── Foundry IQ Knowledge Base Index Names ────
FOUNDRY_IQ_KB_REGULATIONS=argus-kb-regulations
FOUNDRY_IQ_KB_SANCTIONS=argus-kb-sanctions
FOUNDRY_IQ_KB_ADVERSEMEDIA=argus-kb-adversemedia

# ── Azure Cosmos DB ───────────────────────────
COSMOS_ENDPOINT=$cosmosEndpoint
COSMOS_KEY=$cosmosKey
COSMOS_DATABASE=argus-db

# ── Azure Document Intelligence (OCR) ────────
DOC_INTELLIGENCE_ENDPOINT=$docAiEndpoint
DOC_INTELLIGENCE_KEY=$docAiKey

# ── Agent A2A Endpoints ───────────────────────
IDENTITY_AGENT_URL=http://localhost:8001
SCREENING_AGENT_URL=http://localhost:8002
CORPORATE_AGENT_URL=http://localhost:8003
TRANSACTION_AGENT_URL=http://localhost:8004
COMPLIANCE_AGENT_URL=http://localhost:8005

# ── API ───────────────────────────────────────
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
"@

$envContent | Out-File -FilePath "$PSScriptRoot\..\\.env" -Encoding utf8
Write-Host "  ✅ .env written to project root." -ForegroundColor Green

# ── Step 6: Create Cosmos DB Database and Containers ───────────────────────
Write-Host "[6/7] Creating Cosmos DB database and containers..." -ForegroundColor Yellow
python "$PSScriptRoot\create_cosmos_db.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠️  Cosmos DB setup had warnings — check output above." -ForegroundColor Yellow
} else {
    Write-Host "  ✅ Cosmos DB database and containers created." -ForegroundColor Green
}

# ── Step 7: Create Foundry IQ Search Indexes ───────────────────────────────
Write-Host "[7/7] Creating Foundry IQ (AI Search) knowledge base indexes..." -ForegroundColor Yellow
python "$PSScriptRoot\create_search_indexes.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠️  Search index setup had warnings — check output above." -ForegroundColor Yellow
} else {
    Write-Host "  ✅ Foundry IQ knowledge base indexes created." -ForegroundColor Green
}

# ── Done ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ✅  Azure setup complete!                          ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. make generate-data       # generate synthetic datasets" -ForegroundColor White
Write-Host "  2. make upload-data         # upload to Cosmos DB" -ForegroundColor White
Write-Host "  3. make index-knowledge-bases  # index into Foundry IQ" -ForegroundColor White
Write-Host "  4. make run-all             # start all agents + API + UI" -ForegroundColor White
Write-Host ""
Write-Host "Azure Portal: https://portal.azure.com/#resource/subscriptions/$subscriptionId/resourceGroups/$ResourceGroup" -ForegroundColor Gray
Write-Host "AI Foundry:   https://ai.azure.com/resource/overview" -ForegroundColor Gray
Write-Host ""
