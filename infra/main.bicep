// ARGUS on Azure, as chosen in decision D1 (docs/ARCHITECTURE.md, "Hosting").
//
// One resource group holds everything, so deleting it removes the deployment
// (infra/teardown.py also purges what Azure keeps soft-deleted):
//   - Log Analytics with a daily ingestion cap and the free 30-day retention
//   - a Container Apps environment (workload profiles, the API on its Consumption profile) and the
//     API app, 0 to 1 replicas, pulling the public image from GitHub Container Registry
//   - Azure AI Search, Free tier: the three Foundry IQ knowledge bases and their indexes
//   - Cosmos DB, free tier: entities, ownership graph, transactions, PEPs and reports, sharing
//     one 1000 RU/s database budget (all the free tier covers)
//   - a Foundry (AI Services) account with one Data Zone Standard model deployment
//   - Document Intelligence, F0
//
// Nothing here stores a key. The API signs in to Cosmos DB, Azure OpenAI and Document
// Intelligence with its managed identity, and local authentication is off on all three. AI
// Search is the one exception: Free has no keyless access, so the API gets a query key (read
// only) as a Container Apps secret, read from the service at deployment time.
//
// Deploy: see docs/DEPLOYMENT.md. Fill the data plane afterwards with infra/populate.py.

targetScope = 'resourceGroup'

@description('Region for every resource but AI Search. Sweden Central has every other service and model used here.')
param location string = resourceGroup().location

// Microsoft's region list (learn.microsoft.com/azure/search/search-region-support, checked
// 2026-10-04) marks Sweden Central as too much in demand for new search services. France Central
// is in the EU and has agentic retrieval and the semantic ranker on the Free tier.
@description('Region for AI Search: one that accepts new services and runs agentic retrieval on the Free tier.')
param searchLocation string = 'francecentral'

@description('Short prefix for resource names.')
@minLength(3)
@maxLength(10)
param prefix string = 'argus'

@description('The API image, for example ghcr.io/iarjunganesh/argus:sha-0123abc. The package must be public.')
param image string

@description('Browser origins allowed to call the API, comma-separated: the web UI.')
param corsOrigins string = 'https://argus.arjunganesh.dev'

@description('The chat model that writes the explanation, and its version.')
param chatModel string = 'gpt-5.4-mini'
param chatModelVersion string = '2026-03-17'

@description('Deployment type of the chat model. DataZoneStandard keeps processing in the EU data zone.')
param chatSku string = 'DataZoneStandard'

@description('Chat model capacity in thousands of tokens per minute. Billing is per token; the capacity caps the rate, and so the most a flood of requests to the public API can spend.')
@minValue(1)
param chatCapacity int = 10

@description('Use the Cosmos DB free tier. Only one account per subscription can have it.')
param cosmosFreeTier bool = true

@description('Daily Log Analytics ingestion cap in GB, as a string (Bicep has no decimal literals).')
param logDailyCapGb string = '0.1'

@description('Tags on every resource, for cost tracking.')
param tags object = { workload: 'argus' }

var suffix = take(uniqueString(resourceGroup().id), 6)
var databaseName = 'argus-db'

// Partition keys name a field every uploaded record has (data/synthetic/upload_to_cosmos.py);
// tests/test_data_plane_azure.py checks them against the synthetic records. Reports expire 24 hours
// after their last change (REPORT_RETENTION_SECONDS in src/argus/data_plane/base.py).
type cosmosContainer = { name: string, partitionKey: string, defaultTtl: int? }
var cosmosContainers cosmosContainer[] = [
  { name: 'entities', partitionKey: '/entity_type' }
  { name: 'corporate_graph', partitionKey: '/parent_entity' }
  { name: 'transactions', partitionKey: '/entity_name' }
  { name: 'kyc_reports', partitionKey: '/report_id', defaultTtl: 86400 }
]

// Built-in role definition IDs.
var cognitiveServicesOpenAIUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var cognitiveServicesUser = 'a97b65f3-24c7-4388-baec-2e87135dc908'
var cosmosDataContributor = '00000000-0000-0000-0000-000000000002'

// ── Logs ─────────────────────────────────────────────────────────────────────

resource logs 'Microsoft.OperationalInsights/workspaces@2025-02-01' = {
  name: '${prefix}-logs-${suffix}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: json(logDailyCapGb) }
  }
}

// ── Search: Foundry IQ knowledge bases ──────────────────────────────────────

resource search 'Microsoft.Search/searchServices@2025-05-01' = {
  name: '${prefix}-search-${suffix}'
  location: searchLocation
  tags: tags
  sku: { name: 'free' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'Default'
    publicNetworkAccess: 'enabled'
  }
}

// ── Cosmos DB: entities and reports ─────────────────────────────────────────

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2025-04-15' = {
  name: '${prefix}-cosmos-${suffix}'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  identity: { type: 'SystemAssigned' } // holds no roles yet; ready for keyless outbound access
  properties: {
    databaseAccountOfferType: 'Standard'
    enableFreeTier: cosmosFreeTier
    disableLocalAuth: true
    minimalTlsVersion: 'Tls12'
    locations: [{ locationName: location, failoverPriority: 0, isZoneRedundant: false }]
    consistencyPolicy: { defaultConsistencyLevel: 'Session' }
    // Point-in-time restore over 7 days; this tier stores its backups at no charge.
    backupPolicy: { type: 'Continuous', continuousModeProperties: { tier: 'Continuous7Days' } }
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2025-04-15' = {
  parent: cosmos
  name: databaseName
  properties: {
    resource: { id: databaseName }
    options: { throughput: 1000 } // shared by every container: the free tier's whole allowance
  }
}

resource containers 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2025-04-15' = [
  for c in cosmosContainers: {
    parent: database
    name: c.name
    properties: {
      resource: union(
        { id: c.name, partitionKey: { paths: [c.partitionKey], kind: 'Hash' } },
        c.?defaultTtl == null ? {} : { defaultTtl: c.?defaultTtl }
      )
    }
  }
]

// ── Models: Foundry account with one chat deployment ────────────────────────

resource ai 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: '${prefix}-ai-${suffix}'
  location: location
  tags: tags
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' } // holds no roles yet; ready for keyless outbound access
  properties: {
    customSubDomainName: '${prefix}-ai-${suffix}'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource chat 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: ai
  name: chatModel
  sku: { name: chatSku, capacity: chatCapacity }
  properties: {
    model: { format: 'OpenAI', name: chatModel, version: chatModelVersion }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

// ── Document Intelligence (OCR) ──────────────────────────────────────────────

resource ocr 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: '${prefix}-ocr-${suffix}'
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: { name: 'F0' }
  identity: { type: 'SystemAssigned' } // holds no roles yet; ready for keyless outbound access
  properties: {
    customSubDomainName: '${prefix}-ocr-${suffix}'
    disableLocalAuth: true
    // Closed until the API accepts documents: nothing calls it yet (CHANGELOG "Known issues").
    publicNetworkAccess: 'Disabled'
  }
}

// ── The API on Container Apps ────────────────────────────────────────────────

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: '${prefix}-env-${suffix}'
  location: location
  tags: tags
  properties: {
    // Every workload profiles environment has this profile; it bills per use and scales to zero.
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource api 'Microsoft.App/containerApps@2025-01-01' = {
  name: '${prefix}-api'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        { name: 'search-query-key', value: search.listQueryKeys().value[0].key }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: image
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'ARGUS_DATA_BACKEND', value: 'azure' }
            { name: 'ARGUS_MODEL_PROVIDER', value: 'azure-openai' }
            { name: 'ARGUS_CORS_ORIGINS', value: corsOrigins }
            { name: 'ARGUS_DEMO_ONLY', value: 'true' } // a public API runs only the synthetic cases
            { name: 'AZURE_OPENAI_ENDPOINT', value: 'https://${ai.properties.customSubDomainName}.openai.azure.com' }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: chat.name }
            { name: 'AZURE_SEARCH_ENDPOINT', value: 'https://${search.name}.search.windows.net' }
            { name: 'AZURE_SEARCH_API_KEY', secretRef: 'search-query-key' }
            { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
            { name: 'COSMOS_DATABASE', value: database.name }
            { name: 'DOC_INTELLIGENCE_ENDPOINT', value: ocr.properties.endpoint }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: { path: '/health', port: 8000 }
              periodSeconds: 2
              failureThreshold: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8000 }
              periodSeconds: 10
            }
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8000 }
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
        rules: [{ name: 'http', http: { metadata: { concurrentRequests: '20' } } }]
      }
    }
  }
}

// ── What the API's managed identity may do ───────────────────────────────────

resource apiUsesModel 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: ai
  name: guid(ai.id, api.id, cognitiveServicesOpenAIUser)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUser)
    principalId: api.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource apiUsesOcr 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: ocr
  name: guid(ocr.id, api.id, cognitiveServicesUser)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUser)
    principalId: api.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource apiUsesCosmos 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2025-04-15' = {
  parent: cosmos
  name: guid(cosmos.id, api.id, cosmosDataContributor)
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributor}'
    principalId: api.identity.principalId
    scope: '${cosmos.id}/dbs/${database.name}'
  }
}

output apiUrl string = 'https://${api.properties.configuration.ingress.fqdn}'
output apiName string = api.name
output searchName string = search.name
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosAccount string = cosmos.name
output cosmosDatabase string = database.name
