# Step 3: AI Searchインデックス作成

このステップでは、Azure CLIを使用してAI Searchのインデックスを作成し、Blob Storageのデータをインデクシングします。

> 📝 **初学者向け: AI Searchの基本概念**
> 
> **AI Searchとは？**
> - Googleのような「検索エンジン」をあなた専用に作れるサービス
> - データを登録すると、高速に検索できるようになる
> 
> **3つの重要な要素**:
> 
> 1. **インデックス (Index)**
>    - データを格納する「本棚」のようなもの
>    - どんな情報(フィールド)を保存するか定義
>    - 例: 「タイトル」「本文」「URL」など
> 
> 2. **データソース (Data Source)**
>    - データの「元ネタ」を指定
>    - このプロジェクトではBlob Storageを使用
>    - AI Searchに「ここからデータを読み込んで」と伝える
> 
> 3. **インデクサー (Indexer)**
>    - データを自動的に取り込む「お掃除ロボット」
>    - データソースから定期的にデータを読み込んでインデックスに登録
>    - スケジュール設定で自動更新も可能
> 
> **流れ**:
> ```
> Blob Storage → データソース → インデクサー → インデックス → 検索可能!
>    (元データ)   (接続設定)    (取り込み)    (検索エンジン)
> ```
> 
> **RAGとの関係**:
> - AI Searchでユーザーの質問に関連するドキュメントを検索
> - 見つかったドキュメントをAzure OpenAIに渡す
> - Azure OpenAIが検索結果を基に回答を生成

## 📚 学習目標

このステップを完了すると、以下ができるようになります:

- Azure AI Searchインデックスの作成
- データソースの構成
- インデクサーの作成と実行
- ベクトル検索の設定
- インデックスの動作確認

## 前提条件

- Step 1, 2が完了していること
- Blob Storageにデータがアップロード済みであること
- AI Search サービスが作成済みであること

## インデックス作成手順

### 1. AI Search接続情報の取得

```powershell
# 環境変数を設定
$RESOURCE_GROUP = "rg-internal-rag-dev"
$SEARCH_SERVICE = "<your-search-service-name>"

# AI Search管理キーを取得(設定用)
$SEARCH_ADMIN_KEY = az search admin-key show `
    --resource-group $RESOURCE_GROUP `
    --service-name $SEARCH_SERVICE `
    --query primaryKey -o tsv

# エンドポイントURL
$SEARCH_ENDPOINT = "https://$SEARCH_SERVICE.search.windows.net"

Write-Host "Search Endpoint: $SEARCH_ENDPOINT"
```

### 2. インデックススキーマの作成

#### スクリプトファイルの作成

以下のコマンドでスクリプトファイルを作成します:

```powershell
# スクリプトを作成(VS Codeで開く)
New-Item -ItemType File -Path "scripts\create-index.ps1" -Force
code scripts\create-index.ps1
```

作成した `scripts/create-index.ps1` に以下の内容を貼り付けて保存します:

**ファイル内容** (`scripts/create-index.ps1`):

```powershell
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
```

実行:

```powershell
.\scripts\create-index.ps1 `
    -SearchService $SEARCH_SERVICE `
    -SearchAdminKey $SEARCH_ADMIN_KEY `
    -IndexName "redlist-index"
```

### 3. データソースの作成

Blob Storageをデータソースとして登録します。

> 💡 **認証方法**: AI SearchからStorage Accountへのアクセスには**Managed Identity**を使用します。これはセキュリティ上最も安全で、キーのローテーションが不要です。

**前提条件**: Step 1でAI SearchのManaged Identityが有効化され、Storage Accountへの権限が付与されていること。

#### スクリプトファイルの作成

以下のコマンドでスクリプトファイルを作成します:

```powershell
# スクリプトを作成(VS Codeで開く)
New-Item -ItemType File -Path "scripts\create-datasource.ps1" -Force
code scripts\create-datasource.ps1
```

作成した `scripts/create-datasource.ps1` に以下の内容を貼り付けて保存します:

**ファイル内容** (`scripts/create-datasource.ps1`):

```powershell
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
```

実行:

```powershell
.\scripts\create-datasource.ps1 `
    -SearchService $SEARCH_SERVICE `
    -SearchAdminKey $SEARCH_ADMIN_KEY `
    -StorageAccountName $STORAGE_ACCOUNT `
    -ContainerName "rag-documents"
```

### 4. インデクサーの作成

データソースからインデックスにデータを取り込むインデクサーを作成します。

#### スクリプトファイルの作成

以下のコマンドでスクリプトファイルを作成します:

```powershell
# スクリプトを作成(VS Codeで開く)
New-Item -ItemType File -Path "scripts\create-indexer.ps1" -Force
code scripts\create-indexer.ps1
```

作成した `scripts/create-indexer.ps1` に以下の内容を貼り付けて保存します:

**ファイル内容** (`scripts/create-indexer.ps1`):

```powershell
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
```

実行:

```powershell
.\scripts\create-indexer.ps1 `
    -SearchService $SEARCH_SERVICE `
    -SearchAdminKey $SEARCH_ADMIN_KEY
```

### 5. インデクサーの実行とステータス確認

> ⚠️ **重要**: Azure CLIでは現時点でインデクサーのステータス確認コマンドがサポートされていません。ステータス確認はREST APIまたはAzure Portalを使用してください。

#### Azure CLI でインデクサーを実行

```powershell
# インデクサーを実行
az search indexer run `
    --resource-group $RESOURCE_GROUP `
    --service-name $SEARCH_SERVICE `
    --name blob-indexer

Write-Host "Indexer started. Processing..." -ForegroundColor Yellow
Write-Host "ステータスはAzure PortalまたはREST APIで確認してください" -ForegroundColor Cyan
```

#### REST APIでステータス確認(Private Endpoint環境では不可)

```powershell
# インデクサーを手動実行
$IndexerName = "blob-indexer"
$uri = "$SEARCH_ENDPOINT/indexers/$IndexerName/run?api-version=2023-11-01"
$headers = @{
    "api-key" = $SEARCH_ADMIN_KEY
}

try {
    Invoke-RestMethod -Uri $uri -Method Post -Headers $headers
    Write-Host "Indexer started. Waiting for completion..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    # インデクサーのステータス確認
    $statusUri = "$SEARCH_ENDPOINT/indexers/$IndexerName/status?api-version=2023-11-01"
    $status = Invoke-RestMethod -Uri $statusUri -Headers $headers
    $status.lastResult | Format-List
} catch {
    Write-Host "Error: Private Endpoint環境ではローカルからアクセスできません" -ForegroundColor Yellow
    Write-Host "Azure Portalでインデクサーのステータスを確認してください" -ForegroundColor Cyan
}
```

#### Azure Portalでステータス確認(推奨)

1. Azure Portal (https://portal.azure.com) を開く
2. AI Search リソースに移動
3. 左メニューから「インデクサー」を選択
4. `blob-indexer` をクリック
5. 実行履歴とステータスを確認

### 6. インデックスの確認

#### Azure Portal で確認(推奨)

1. Azure Portal (https://portal.azure.com) を開く
2. AI Search リソースに移動
3. 「インデックス」→ `redlist-index` を選択
4. ドキュメント数と統計情報を確認

#### Azure CLI で確認

```powershell
# インデックス情報を確認
az search index show `
    --resource-group $RESOURCE_GROUP `
    --service-name $SEARCH_SERVICE `
    --name redlist-index `
    --query "{name:name, fields:fields[].{name:name, type:type}}" -o json
```

> 💡 **ヒント**: ドキュメント数などの統計情報は、Azure Portal の「インデックス」画面で確認できます。

### 7. 検索テスト

#### Azure Portal で検索テスト(推奨)

Private Endpoint環境では、Azure Portalの「検索エクスプローラー」を使用します:

1. Azure Portal で AI Search リソースを開く
2. 「検索エクスプローラー」を選択
3. インデックス: `redlist-index` を選択
4. 検索ボックスに `イリオモテヤマネコ` と入力して検索

#### REST API で検索する場合(Public Access有効時のみ)

```powershell
# シンプルな検索テスト
$searchUri = "$SEARCH_ENDPOINT/indexes/redlist-index/docs/search?api-version=2023-11-01"
$headers = @{
    "Content-Type" = "application/json"
    "api-key" = $SEARCH_ADMIN_KEY
}

$searchQuery = @{
    search = "イリオモテヤマネコ"
    top = 3
    select = "title,content,url"
} | ConvertTo-Json

try {
    $results = Invoke-RestMethod -Uri $searchUri -Method Post -Headers $headers -Body $searchQuery
    
    Write-Host "`nSearch Results:" -ForegroundColor Cyan
    $results.value | ForEach-Object {
        Write-Host "`nTitle: $($_.title)" -ForegroundColor Yellow
        Write-Host "Content: $($_.content.Substring(0, [Math]::Min(100, $_.content.Length)))..."
        Write-Host "URL: $($_.url)"
        Write-Host "---"
    }
} catch {
    Write-Host "Error: Private Endpoint環境ではAzure Portalの検索エクスプローラーを使用してください" -ForegroundColor Yellow
}
```

## Azure CLIを使用した簡易作成

上記のREST APIの代わりに、Azure CLIでも作成できます。

```powershell
# インデックスを作成(JSON定義ファイルを使用)
az search index create `
    --resource-group $RESOURCE_GROUP `
    --service-name $SEARCH_SERVICE `
    --name redlist-index `
    --fields "@data/schema/index-schema.json"

# データソースを作成
az search data-source create `
    --resource-group $RESOURCE_GROUP `
    --service-name $SEARCH_SERVICE `
    --name blob-datasource `
    --type azureblob `
    --connection-string "DefaultEndpointsProtocol=https;AccountName=$STORAGE_ACCOUNT;AccountKey=$STORAGE_KEY" `
    --container rag-documents

# インデクサーを作成
az search indexer create `
    --resource-group $RESOURCE_GROUP `
    --service-name $SEARCH_SERVICE `
    --name blob-indexer `
    --data-source-name blob-datasource `
    --target-index-name redlist-index

# インデクサーを実行
az search indexer run `
    --resource-group $RESOURCE_GROUP `
    --service-name $SEARCH_SERVICE `
    --name blob-indexer
```

## 確認事項

以下をすべて確認してください:

- ✅ AI Searchインデックスが作成されている
- ✅ データソースが作成されている
- ✅ インデクサーが作成されている
- ✅ インデクサーが正常に実行されている
- ✅ ドキュメントがインデックスに登録されている
- ✅ 検索テストが成功している

## トラブルシューティング

### インデクサー実行に失敗する

**症状**: インデクサーのステータスがエラー

**対処法**:
```powershell
# エラー詳細を確認
$statusUri = "$SEARCH_ENDPOINT/indexers/blob-indexer/status?api-version=2023-11-01"
$status = Invoke-RestMethod -Uri $statusUri -Headers @{"api-key" = $SEARCH_ADMIN_KEY}

$status.lastResult.errors | Format-List

# よくある原因:
# 1. Blob StorageのアクセスキーMicrosoft Azure Search を許可していない
# 2. JSONLフォーマットが不正
# 3. フィールドマッピングが間違っている
```

### ドキュメント数が0

**症状**: インデックスは作成されたがドキュメントが0件

**対処法**:
- Blob Storageにファイルが存在するか確認
- インデクサーのparsingModeが`jsonLines`になっているか確認
- Blob Storageへのアクセス権限を確認

### 検索結果が返らない

**症状**: 検索クエリを実行しても結果が0件

**対処法**:
- インデックスにドキュメントが登録されているか確認
- 検索フィールドが`searchable: true`になっているか確認
- 検索クエリのスペルミスを確認

## 次のステップ

AI Searchインデックス作成が完了したら、次は **[Step 4: アプリケーションデプロイ](step04-deploy-app.md)** に進みましょう。

GitHubを使用してアプリケーションをAzure Functionsにデプロイします。
