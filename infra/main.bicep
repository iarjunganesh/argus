// ============================================================
// ARGUS — Azure Infrastructure
// Microsoft Agents League Hackathon 2026
//
// Provisions:
//   • Azure AI Foundry (Hub + Project)
//   • Azure OpenAI (GPT-4o)
//   • Azure AI Search (Basic tier — backs Foundry IQ)
//   • Azure Cosmos DB (Free tier)
//   • Azure Document Intelligence (F0 — free)
//   • Azure Storage + Key Vault (required by AI Hub)
// ============================================================

targetScope = 'resourceGroup'

@description('Location for all resources. Use eastus or swedencentral for best GPT-4o availability.')
param location string = 'swedencentral'

@description('Short prefix for resource names.')
param prefix string = 'argus'

@description('GPT-4o model version to deploy.')
param gpt4oVersion string = '2024-11-20'

@description('TPM capacity for GPT-4o deployment (in thousands). Free accounts may be limited to 10-30k.')
param gpt4oCapacity int = 10

var suffix = take(uniqueString(resourceGroup().id), 6)

// ────────────────────────────────────────────────────────────
// Storage Account (required by AI Hub)
// ────────────────────────────────────────────────────────────
resource storage 'Microsoft.Storage/storageAccounts@2023-04-01' = {
  name: '${prefix}st${suffix}'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// ────────────────────────────────────────────────────────────
// Key Vault (required by AI Hub)
// ────────────────────────────────────────────────────────────
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${prefix}-kv-${suffix}'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// ────────────────────────────────────────────────────────────
// Azure OpenAI
// NOTE: New free accounts may need to request Azure OpenAI access first.
// Apply at: https://aka.ms/oai/access
// ────────────────────────────────────────────────────────────
resource openai 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${prefix}-openai-${suffix}'
  location: location
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: '${prefix}-openai-${suffix}'
    publicNetworkAccess: 'enabled'
    disableLocalAuth: false
  }
}

resource gpt4o 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openai
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: gpt4oCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: gpt4oVersion
    }
    raiPolicyName: 'Microsoft.Default'
  }
}

// ────────────────────────────────────────────────────────────
// Azure AI Foundry Hub
// ────────────────────────────────────────────────────────────
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: '${prefix}-hub'
  location: location
  kind: 'Hub'
  identity: { type: 'SystemAssigned' }
  sku: { name: 'Basic', tier: 'Basic' }
  properties: {
    friendlyName: 'ARGUS AI Hub'
    storageAccount: storage.id
    keyVault: kv.id
    publicNetworkAccess: 'enabled'
  }
}

// OpenAI connection on the Hub (needed for Foundry Agents)
resource openaiConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-10-01' = {
  parent: aiHub
  name: 'azure-openai-connection'
  properties: {
    category: 'AzureOpenAI'
    target: openai.properties.endpoint
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: openai.listKeys().key1
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: openai.id
      ApiVersion: '2024-08-01-preview'
      DeploymentApiVersion: '2023-10-01-preview'
    }
  }
}

// ────────────────────────────────────────────────────────────
// Azure AI Foundry Project
// ────────────────────────────────────────────────────────────
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: '${prefix}-project'
  location: location
  kind: 'Project'
  identity: { type: 'SystemAssigned' }
  sku: { name: 'Basic', tier: 'Basic' }
  properties: {
    friendlyName: 'ARGUS Project'
    hubResourceId: aiHub.id
    publicNetworkAccess: 'enabled'
  }
}

// ────────────────────────────────────────────────────────────
// Azure AI Search — backs Foundry IQ knowledge bases
// NOTE: Basic tier provides vector capacity and enough storage for the demo.
// Semantic Search can remain enabled for grounded retrieval.
// ────────────────────────────────────────────────────────────
resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: '${prefix}-search-${suffix}'
  location: location
  sku: { name: 'basic' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    publicNetworkAccess: 'enabled'
    semanticSearch: 'free'
  }
}

// ────────────────────────────────────────────────────────────
// Azure Cosmos DB — stores synthetic entity/transaction data
// Free tier: 1,000 RU/s + 25 GB — no cost if one per subscription
// ────────────────────────────────────────────────────────────
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-02-15-preview' = {
  name: '${prefix}-cosmos-${suffix}'
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableFreeTier: true
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Local'
      }
    }
  }
}

// ────────────────────────────────────────────────────────────
// Azure Document Intelligence — OCR for identity documents
// F0 (Free): 500 pages/month, 1 request/sec — fine for demo
// ────────────────────────────────────────────────────────────
resource docIntelligence 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${prefix}-docai-${suffix}'
  location: location
  kind: 'FormRecognizer'
  sku: { name: 'F0' }
  properties: {
    customSubDomainName: '${prefix}-docai-${suffix}'
    publicNetworkAccess: 'enabled'
    disableLocalAuth: false
  }
}

// ────────────────────────────────────────────────────────────
// OUTPUTS — captured by setup.ps1 to generate .env
// ────────────────────────────────────────────────────────────
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output AZURE_OPENAI_ENDPOINT string = openai.properties.endpoint
output AZURE_OPENAI_DEPLOYMENT string = gpt4o.name
output AZURE_SEARCH_ENDPOINT string = 'https://${search.name}.search.windows.net'
output COSMOS_ENDPOINT string = cosmos.properties.documentEndpoint
output DOC_INTELLIGENCE_ENDPOINT string = docIntelligence.properties.endpoint
output AI_HUB_NAME string = aiHub.name
output AI_PROJECT_NAME string = aiProject.name
// Note: FOUNDRY_ENDPOINT is derived by setup.ps1 via 'az ml workspace show'
