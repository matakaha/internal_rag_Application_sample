# AI Searchインデクサー作成スクリプト

param(
    [Parameter(Mandatory=$true)]
    [string]$SearchService,
    
    [Parameter(Mandatory=$true)]
    [string]$SearchAdminKey,
    
    [string]$IndexerName = "blob-indexer",
    [string]$DataSourceName = "blob-datasource",
    [string]$IndexName = "redlist-index"
)

$searchEndpoint = "https://$SearchService.search.windows.net"
$apiVersion = "2023-11-01"

# インデクサー定義
$indexer = @{
    name = $IndexerName
    dataSourceName = $DataSourceName
    targetIndexName = $IndexName
    schedule = @{
        interval = "PT2H"  # 2時間ごと
    }
    parameters = @{
        batchSize = 50
        maxFailedItems = 10
        maxFailedItemsPerBatch = 5
        configuration = @{
            dataToExtract = "contentAndMetadata"
            parsingMode = "jsonLines"
        }
    }
    fieldMappings = @(
        @{
            sourceFieldName = "id"
            targetFieldName = "id"
        },
        @{
            sourceFieldName = "title"
            targetFieldName = "title"
        },
        @{
            sourceFieldName = "content"
            targetFieldName = "content"
        },
        @{
            sourceFieldName = "category"
            targetFieldName = "category"
        },
        @{
            sourceFieldName = "rank"
            targetFieldName = "rank"
        },
        @{
            sourceFieldName = "scientific_name"
            targetFieldName = "scientific_name"
        },
        @{
            sourceFieldName = "japanese_name"
            targetFieldName = "japanese_name"
        },
        @{
            sourceFieldName = "family"
            targetFieldName = "family"
        },
        @{
            sourceFieldName = "url"
            targetFieldName = "url"
        }
    )
}

# インデクサーを作成
$headers = @{
    "Content-Type" = "application/json"
    "api-key" = $SearchAdminKey
}

$uri = "$searchEndpoint/indexers/$IndexerName`?api-version=$apiVersion"
$body = $indexer | ConvertTo-Json -Depth 10

Write-Host "Creating indexer: $IndexerName"

try {
    $response = Invoke-RestMethod -Uri $uri -Method Put -Headers $headers -Body $body
    Write-Host "Indexer created successfully!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 5
} catch {
    Write-Error "Failed to create indexer: $_"
}