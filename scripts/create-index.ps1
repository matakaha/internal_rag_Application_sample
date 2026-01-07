# AI Searchインデックス作成スクリプト

param(
    [Parameter(Mandatory=$true)]
    [string]$SearchService,
    
    [Parameter(Mandatory=$true)]
    [string]$SearchAdminKey,
    
    [string]$IndexName = "redlist-index"
)

$searchEndpoint = "https://$SearchService.search.windows.net"
$apiVersion = "2023-11-01"

# インデックススキーマを定義
$indexSchema = @{
    name = $IndexName
    fields = @(
        @{
            name = "id"
            type = "Edm.String"
            key = $true
            searchable = $false
        },
        @{
            name = "title"
            type = "Edm.String"
            searchable = $true
            filterable = $true
            sortable = $true
            analyzer = "ja.lucene"
        },
        @{
            name = "content"
            type = "Edm.String"
            searchable = $true
            analyzer = "ja.lucene"
        },
        @{
            name = "category"
            type = "Edm.String"
            searchable = $true
            filterable = $true
            facetable = $true
        },
        @{
            name = "rank"
            type = "Edm.String"
            searchable = $false
            filterable = $true
            facetable = $true
        },
        @{
            name = "scientific_name"
            type = "Edm.String"
            searchable = $true
            filterable = $true
            sortable = $true
        },
        @{
            name = "japanese_name"
            type = "Edm.String"
            searchable = $true
            filterable = $true
            sortable = $true
            analyzer = "ja.lucene"
        },
        @{
            name = "family"
            type = "Edm.String"
            searchable = $true
            filterable = $true
            facetable = $true
            analyzer = "ja.lucene"
        },
        @{
            name = "url"
            type = "Edm.String"
            searchable = $false
        }
    )
    semantic = @{
        configurations = @(
            @{
                name = "semantic-config"
                prioritizedFields = @{
                    titleField = @{
                        fieldName = "title"
                    }
                    prioritizedContentFields = @(
                        @{
                            fieldName = "content"
                        }
                    )
                    prioritizedKeywordsFields = @(
                        @{
                            fieldName = "category"
                        },
                        @{
                            fieldName = "rank"
                        }
                    )
                }
            }
        )
    }
}

# インデックスを作成
$headers = @{
    "Content-Type" = "application/json"
    "api-key" = $SearchAdminKey
}

$uri = "$searchEndpoint/indexes/$IndexName`?api-version=$apiVersion"
$body = $indexSchema | ConvertTo-Json -Depth 10

Write-Host "Creating index: $IndexName"

try {
    $response = Invoke-RestMethod -Uri $uri -Method Put -Headers $headers -Body $body
    Write-Host "Index created successfully!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 5
} catch {
    Write-Error "Failed to create index: $_"
    Write-Error $_.Exception.Response
}