# Azure Resource Information Retrieval Script
param(
    [string]$ResourceGroup = "rg-internal-rag-dev",
    [string]$SubscriptionId
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Azure Resource Information Retrieval" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check Azure login
try {
    $null = az account show 2>$null
} catch {
    Write-Host "Please login to Azure" -ForegroundColor Yellow
    az login
}

# Set subscription
if ($SubscriptionId) {
    az account set --subscription $SubscriptionId
}

$currentSub = az account show -o json | ConvertFrom-Json
Write-Host "Subscription: $($currentSub.name)" -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroup" -ForegroundColor Cyan
Write-Host ""

# Check resource group exists
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -eq "false") {
    Write-Host "ERROR: Resource group not found" -ForegroundColor Red
    exit 1
}

# Store environment variables
$envVars = @{}

# Get Azure AI Services / OpenAI
Write-Host "1. Getting Azure AI Services (Foundry)..." -ForegroundColor Yellow
$cognitiveJson = az cognitiveservices account list --resource-group $ResourceGroup -o json
$cognitiveList = $cognitiveJson | ConvertFrom-Json
$aiService = $cognitiveList | Where-Object { $_.kind -eq 'AIServices' -or $_.kind -eq 'OpenAI' } | Select-Object -First 1

if ($aiService) {
    Write-Host "   AI Service Name: $($aiService.name)" -ForegroundColor Green
    $envVars.AZURE_AI_SERVICE_NAME = $aiService.name
    
    # Get resource-specific endpoint
    $aiServiceDetailJson = az cognitiveservices account show --resource-group $ResourceGroup --name $aiService.name -o json
    $aiServiceDetail = $aiServiceDetailJson | ConvertFrom-Json
    $envVars.AZURE_AI_ENDPOINT = $aiServiceDetail.properties.endpoint
    Write-Host "   Endpoint: $($envVars.AZURE_AI_ENDPOINT)" -ForegroundColor Green
    
    # Get Foundry projects within this AI Service
    Write-Host "1b. Getting Foundry Projects..." -ForegroundColor Yellow
    $projectsJson = az rest --method get --url "$($aiServiceDetail.id)/projects?api-version=2024-04-01-preview" 2>$null
    if ($projectsJson) {
        $projects = $projectsJson | ConvertFrom-Json
        if ($projects.value -and $projects.value.Count -gt 0) {
            $project = $projects.value[0]
            $projectName = $project.name
            Write-Host "   Project Name: $projectName" -ForegroundColor Green
            $envVars.AZURE_AI_PROJECT_NAME = $projectName
        }
    }
    
    # Get deployments
    $depJson = az cognitiveservices account deployment list --resource-group $ResourceGroup --name $aiService.name -o json
    $deployments = $depJson | ConvertFrom-Json
    if ($deployments) {
        $gpt4 = $deployments | Where-Object { $_.properties.model.name -like "gpt-4*" } | Select-Object -First 1
        if ($gpt4) {
            $envVars.AZURE_OPENAI_DEPLOYMENT = $gpt4.name
            Write-Host "   Chat Model: $($gpt4.name) ($($gpt4.properties.model.name))" -ForegroundColor Green
        }
        
        # Get embedding model
        $embedding = $deployments | Where-Object { $_.properties.model.name -like "*embedding*" } | Select-Object -First 1
        if ($embedding) {
            $envVars.AZURE_OPENAI_EMBEDDING_DEPLOYMENT = $embedding.name
            Write-Host "   Embedding Model: $($embedding.name) ($($embedding.properties.model.name))" -ForegroundColor Green
        }
    }
}

# Get AI Search
Write-Host "2. Getting AI Search..." -ForegroundColor Yellow
$searchJson = az search service list --resource-group $ResourceGroup -o json
$searchList = $searchJson | ConvertFrom-Json
$search = $searchList | Select-Object -First 1

if ($search) {
    Write-Host "   Name: $($search.name)" -ForegroundColor Green
    $envVars.AZURE_SEARCH_SERVICE_NAME = $search.name
    $envVars.AZURE_SEARCH_ENDPOINT = "https://$($search.name).search.windows.net"
    $envVars.AZURE_SEARCH_INDEX = "redlist-index"
}

# Get Storage Account
Write-Host "3. Getting Storage Account..." -ForegroundColor Yellow
$storageJson = az storage account list --resource-group $ResourceGroup -o json
$storageList = $storageJson | ConvertFrom-Json
$storage = $storageList | Select-Object -First 1

if ($storage) {
    Write-Host "   Name: $($storage.name)" -ForegroundColor Green
    $envVars.AZURE_STORAGE_ACCOUNT_NAME = $storage.name
    $envVars.AZURE_STORAGE_CONTAINER = "redlist-data"
}

# Get App Service (if exists)
Write-Host "4. Getting App Service..." -ForegroundColor Yellow
$webappJson = az webapp list --resource-group $ResourceGroup -o json
$webappList = $webappJson | ConvertFrom-Json
$webapp = $webappList | Select-Object -First 1

if ($webapp) {
    Write-Host "   Name: $($webapp.name)" -ForegroundColor Green
    $envVars.AZURE_WEBAPP_NAME = $webapp.name
    $envVars.AZURE_WEBAPP_URL = "https://$($webapp.defaultHostName)"
}

# Get Functions App
Write-Host "4b. Getting Azure Functions..." -ForegroundColor Yellow
$funcappJson = az functionapp list --resource-group $ResourceGroup -o json
$funcappList = $funcappJson | ConvertFrom-Json
$funcapp = $funcappList | Select-Object -First 1

if ($funcapp) {
    Write-Host "   Name: $($funcapp.name)" -ForegroundColor Green
    $envVars.AZURE_FUNCTIONAPP_NAME = $funcapp.name
    $envVars.AZURE_FUNCTIONAPP_URL = "https://$($funcapp.defaultHostName)"
}

# Get Key Vault
Write-Host "5. Getting Key Vault..." -ForegroundColor Yellow
$kvJson = az keyvault list --resource-group $ResourceGroup -o json
$kvList = $kvJson | ConvertFrom-Json
$kv = $kvList | Select-Object -First 1

if ($kv) {
    Write-Host "   Name: $($kv.name)" -ForegroundColor Green
    $envVars.AZURE_KEYVAULT_NAME = $kv.name
    $envVars.AZURE_KEYVAULT_URI = $kv.properties.vaultUri
}

# Get VNet
Write-Host "6. Getting Virtual Network..." -ForegroundColor Yellow
$vnetJson = az network vnet list --resource-group $ResourceGroup -o json
$vnetList = $vnetJson | ConvertFrom-Json
$vnet = $vnetList | Select-Object -First 1

if ($vnet) {
    Write-Host "   Name: $($vnet.name)" -ForegroundColor Green
    $envVars.AZURE_VNET_NAME = $vnet.name
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Creating .env file" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Create .env file
$envPath = Join-Path (Get-Location) ".env"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$content = @"
# Azure Resource Information
# Generated: $timestamp
# Resource Group: $ResourceGroup

# Azure AI Foundry Settings
AZURE_AI_SERVICE_NAME=$($envVars.AZURE_AI_SERVICE_NAME)
AZURE_AI_ENDPOINT=$($envVars.AZURE_AI_ENDPOINT)
AZURE_AI_PROJECT_NAME=$($envVars.AZURE_AI_PROJECT_NAME)

# Azure OpenAI Settings (via Foundry)
AZURE_OPENAI_ENDPOINT=$($envVars.AZURE_AI_ENDPOINT)
AZURE_OPENAI_DEPLOYMENT=$($envVars.AZURE_OPENAI_DEPLOYMENT)
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=$($envVars.AZURE_OPENAI_EMBEDDING_DEPLOYMENT)

# Azure AI Search Settings
AZURE_SEARCH_SERVICE_NAME=$($envVars.AZURE_SEARCH_SERVICE_NAME)
AZURE_SEARCH_ENDPOINT=$($envVars.AZURE_SEARCH_ENDPOINT)
AZURE_SEARCH_INDEX=$($envVars.AZURE_SEARCH_INDEX)

# Azure Storage Settings
AZURE_STORAGE_ACCOUNT_NAME=$($envVars.AZURE_STORAGE_ACCOUNT_NAME)
AZURE_STORAGE_CONTAINER=$($envVars.AZURE_STORAGE_CONTAINER)

# App Service Settings (Legacy)
AZURE_WEBAPP_NAME=$($envVars.AZURE_WEBAPP_NAME)
AZURE_WEBAPP_URL=$($envVars.AZURE_WEBAPP_URL)

# Azure Functions Settings
AZURE_FUNCTIONAPP_NAME=$($envVars.AZURE_FUNCTIONAPP_NAME)
AZURE_FUNCTIONAPP_URL=$($envVars.AZURE_FUNCTIONAPP_URL)

# Virtual Network Settings
AZURE_VNET_NAME=$($envVars.AZURE_VNET_NAME)

# Application Settings
RESOURCE_GROUP=$ResourceGroup
"@

$content | Out-File -FilePath $envPath -Encoding UTF8 -Force
Write-Host "Created: $envPath" -ForegroundColor Green
Write-Host ""

# Generate local.settings.json for Azure Functions
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Creating local.settings.json for Azure Functions" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$localSettingsPath = Join-Path (Get-Location) "apps\backend\local.settings.json"
$localSettingsContent = @"
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsFeatureFlags": "EnableWorkerIndexing",
    "AZURE_OPENAI_ENDPOINT": "$($envVars.AZURE_AI_ENDPOINT)",
    "AZURE_OPENAI_DEPLOYMENT": "$($envVars.AZURE_OPENAI_DEPLOYMENT)",
    "AZURE_SEARCH_ENDPOINT": "$($envVars.AZURE_SEARCH_ENDPOINT)",
    "AZURE_SEARCH_INDEX": "$($envVars.AZURE_SEARCH_INDEX)"
  }
}
"@

$localSettingsContent | Out-File -FilePath $localSettingsPath -Encoding UTF8 -Force
Write-Host "Created: $localSettingsPath" -ForegroundColor Green
Write-Host ""

# Show GitHub Secrets commands
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "GitHub Secrets Setup Commands" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Run these commands to configure GitHub Secrets for CI/CD:" -ForegroundColor Yellow
Write-Host ""

# Core Azure settings
Write-Host "# Core Azure Settings" -ForegroundColor Cyan
$subscriptionId = az account show --query id -o tsv
$tenantId = az account show --query tenantId -o tsv
Write-Host "  gh secret set AZURE_SUBSCRIPTION_ID -b `"$subscriptionId`"" -ForegroundColor Gray
Write-Host "  gh secret set AZURE_TENANT_ID -b `"$tenantId`"" -ForegroundColor Gray
Write-Host "  gh secret set RESOURCE_GROUP -b `"$ResourceGroup`"" -ForegroundColor Gray
Write-Host ""

# App Service settings
Write-Host "# App Service Settings" -ForegroundColor Cyan
if ($envVars.AZURE_WEBAPP_NAME) {
    Write-Host "  gh secret set AZURE_WEBAPP_NAME -b `"$($envVars.AZURE_WEBAPP_NAME)`"" -ForegroundColor Gray
}
if ($envVars.AZURE_FUNCTIONAPP_NAME) {
    Write-Host "  gh secret set AZURE_FUNCTIONAPP_NAME -b `"$($envVars.AZURE_FUNCTIONAPP_NAME)`"" -ForegroundColor Gray
}
Write-Host ""

# Azure AI settings
Write-Host "# Azure AI Settings" -ForegroundColor Cyan
if ($envVars.AZURE_AI_ENDPOINT) {
    Write-Host "  gh secret set AZURE_OPENAI_ENDPOINT -b `"$($envVars.AZURE_AI_ENDPOINT)`"" -ForegroundColor Gray
}
if ($envVars.AZURE_OPENAI_DEPLOYMENT) {
    Write-Host "  gh secret set AZURE_OPENAI_DEPLOYMENT -b `"$($envVars.AZURE_OPENAI_DEPLOYMENT)`"" -ForegroundColor Gray
}
if ($envVars.AZURE_SEARCH_ENDPOINT) {
    Write-Host "  gh secret set AZURE_SEARCH_ENDPOINT -b `"$($envVars.AZURE_SEARCH_ENDPOINT)`"" -ForegroundColor Gray
}
if ($envVars.AZURE_SEARCH_INDEX) {
    Write-Host "  gh secret set AZURE_SEARCH_INDEX -b `"$($envVars.AZURE_SEARCH_INDEX)`"" -ForegroundColor Gray
}
Write-Host ""

# OIDC settings (manual setup required)
Write-Host "# OIDC Authentication (Setup App Registration first)" -ForegroundColor Cyan
Write-Host "  # See docs/step04-deploy-application.md for App Registration setup" -ForegroundColor Yellow
Write-Host "  gh secret set AZURE_CLIENT_ID -b `"<your-app-registration-client-id>`"" -ForegroundColor Gray
Write-Host ""

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
