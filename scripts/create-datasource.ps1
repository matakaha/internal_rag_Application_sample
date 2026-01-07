# AI Searchデータソース作成スクリプト

param(
    [Parameter(Mandatory=$true)]
    [string]$SearchService,
    
    [Parameter(Mandatory=$true)]
    [string]$SearchAdminKey,
    
    [Parameter(Mandatory=$true)]
    [string]$StorageAccountName,
    
    [string]$ContainerName = "rag-documents",
    [string]$DataSourceName = "blob-datasource"
)

$searchEndpoint = "https://$SearchService.search.windows.net"
$apiVersion = "2023-11-01"

Write-Host "Using Managed Identity for authentication" -ForegroundColor Cyan

# Storage AccountのResource IDを構築
$subscriptionId = az account show --query id -o tsv
$resourceGroup = az storage account show --name $StorageAccountName --query resourceGroup -o tsv

$storageResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.Storage/storageAccounts/$StorageAccountName"
$connectionString = "ResourceId=$storageResourceId;"

# データソース定義
$dataSource = @{
    name = $DataSourceName
    type = "azureblob"
    credentials = @{
        connectionString = $connectionString
    }
    container = @{
        name = $ContainerName
        query = ""
    }
    dataChangeDetectionPolicy = @{
        "@odata.type" = "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy"
        highWaterMarkColumnName = "metadata_storage_last_modified"
    }
}

# データソースを作成
$headers = @{
    "Content-Type" = "application/json"
    "api-key" = $SearchAdminKey
}

$uri = "$searchEndpoint/datasources/$DataSourceName`?api-version=$apiVersion"
$body = $dataSource | ConvertTo-Json -Depth 10

Write-Host "Creating data source: $DataSourceName"

try {
    $response = Invoke-RestMethod -Uri $uri -Method Put -Headers $headers -Body $body
    Write-Host "Data source created successfully!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 5
} catch {
    Write-Error "Failed to create data source: $_"
}