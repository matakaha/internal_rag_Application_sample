# Step 1: 環境準備

このステップでは、閉域RAGアプリケーション開発に必要な環境を準備します。

## 📚 学習目標

このステップを完了すると、以下ができるようになります:

- GitHubリポジトリのフォークとクローン
- 必要な環境変数の設定
- Azure CLIでのリソース確認
- ローカル開発環境のセットアップ

## 前提条件

以下が完了していることを確認してください:

### 1. 前提リポジトリの完了

✅ **[internal_rag_step_by_step_bicep](https://github.com/matakaha/internal_rag_step_by_step_bicep)** が完了していること

作成されているリソース:
- Virtual Network (vNet)
- Microsoft Foundry (Private Endpoint付き)
- Azure AI Search (Private Endpoint付き)
- Azure Storage Account
- Azure Functions (AppServicePlan B1共有、vNet統合済み)
- App Service Plan (B1) - フロントエンド/バックエンド共有
- GitHub Self-hosted Runner VM

### 2. ツールのインストール

```powershell
# Azure CLIバージョン確認
az --version
# 必要: 2.50.0以上

# az mlコマンドを使用するため、拡張機能のインストール
az extension add --name ml

# Pythonバージョン確認
python --version
# 必要: 3.11以上

# Azure Functions Core Toolsバージョン確認
func --version
# 必要: 4.x以上
# 未インストールの場合:
# winget install Microsoft.Azure.FunctionsCoreTools

# Gitバージョン確認
git --version
# 必要: 2.30以上
```

## セットアップ手順

### 1. GitHubリポジトリの準備

#### オプションA: このリポジトリをフォーク(推奨)

1. GitHubでこのリポジトリをフォーク
2. フォークしたリポジトリをクローン

```powershell
# 自分のアカウントのリポジトリをクローン
git clone https://github.com/<your-github-username>/internal_rag_Application_sample_repo.git
cd internal_rag_Application_sample_repo
```

#### オプションB: 新規リポジトリとして作成

```powershell
# 新規GitHubリポジトリを作成
gh repo create <your-org>/internal-rag-app --private

# ローカルに初期化
git init
git remote add origin https://github.com/<your-org>/internal-rag-app.git

# このリポジトリの内容をコピー
# (別途ダウンロードして配置)
```

### 2. Azure リソース情報の収集

前提リポジトリで作成したAzureリソースの情報を収集します。

#### 自動収集スクリプトの実行(推奨)

```powershell
# リソース情報を自動取得し、.envファイルを生成
.\scripts\get-azure-resources.ps1

# 特定のリソースグループを指定する場合
.\scripts\get-azure-resources.ps1 -ResourceGroup "rg-internal-rag-dev"

# サブスクリプションIDも指定する場合
.\scripts\get-azure-resources.ps1 -ResourceGroup "rg-internal-rag-dev" -SubscriptionId "your-subscription-id"
```

**スクリプトの動作**:
- Azure CLIを使用してリソース情報を取得
- `.env` ファイルを自動生成
- 環境変数の設定例を表示

#### 手動でリソース情報を収集

```powershell
# リソースグループ名を設定
$RESOURCE_GROUP = "rg-internal-rag-dev"

# OpenAI情報を取得
az cognitiveservices account show `
    --resource-group $RESOURCE_GROUP `
    --name <your-openai-name> `
    --query "{endpoint:properties.endpoint, name:name}" -o table

# AI Search情報を取得
az search service show `
    --resource-group $RESOURCE_GROUP `
    --name <your-search-name> `
    --query "{endpoint:properties.endpoint, name:name}" -o table

# Storage Account情報を取得
az storage account show `
    --resource-group $RESOURCE_GROUP `
    --name <your-storage-name> `
    --query "{name:name, primaryEndpoints:primaryEndpoints}" -o json

# Functions App情報を取得
az functionapp show `
    --resource-group $RESOURCE_GROUP `
    --name <your-functionapp-name> `
    --query "{name:name, defaultHostName:defaultHostName}" -o table
```

### 3. ローカル開発環境のセットアップ

#### Python仮想環境の作成

```powershell
# Python 3.11以上を使用
python --version

# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化(Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 仮想環境を有効化(Windows CMD)
# venv\Scripts\activate.bat

# 仮想環境を有効化(Linux/Mac)
# source venv/bin/activate
```

#### 依存関係のインストール

```powershell
# 仮想環境が有効化されていることを確認
# プロンプトに (venv) が表示される

# pipをアップグレード
python -m pip install --upgrade pip

# 依存パッケージをインストール
pip install -r requirements.txt

# インストール確認
pip list
```

### 4. 環境変数の設定

#### .envファイルの作成

プロジェクトルートに `.env` ファイルを作成します:

```powershell
# .envファイルのテンプレート
@"
# Azure リソース情報
AZURE_SUBSCRIPTION_ID=your-subscription-id
RESOURCE_GROUP=rg-internal-rag-dev

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_INDEX=redlist-index

# Azure Storage
AZURE_STORAGE_ACCOUNT=yourstorageaccount
AZURE_STORAGE_CONTAINER=rag-documents

# Azure Functions
AZURE_FUNCTIONS_NAME=func-internal-rag-dev
"@ | Out-File -FilePath .env -Encoding UTF8
```

#### local.settings.jsonの作成(Azure Functions用)

```powershell
# local.settings.jsonのテンプレート
@"
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsFeatureFlags": "EnableWorkerIndexing",
    "AZURE_OPENAI_ENDPOINT": "https://your-openai.openai.azure.com/",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
    "AZURE_SEARCH_ENDPOINT": "https://your-search.search.windows.net",
    "AZURE_SEARCH_INDEX": "redlist-index"
  }
}
"@ | Out-File -FilePath local.settings.json -Encoding UTF8
```

> ⚠️ **重要**: `.env` と `local.settings.json` は `.gitignore` に含まれているため、Gitにコミットされません。これらのファイルには機密情報が含まれるため、絶対にGitHubにプッシュしないでください。

### 5. Azure接続テスト

#### Azureにログイン

```powershell
# Azure CLIでログイン
az login

# サブスクリプションを設定
az account set --subscription "your-subscription-id"

# 現在のアカウント情報を確認
az account show
```

#### リソースへのアクセス確認

```powershell
# リソースグループの存在確認
az group show --name rg-internal-rag-dev

# OpenAIリソースの確認
az cognitiveservices account show `
    --resource-group rg-internal-rag-dev `
    --name <your-openai-name>

# AI Searchリソースの確認
az search service show `
    --resource-group rg-internal-rag-dev `
    --name <your-search-name>

# Storage Accountの確認
az storage account show `
    --resource-group rg-internal-rag-dev `
    --name <your-storage-name>
```

### 6. ローカル開発用の権限設定

開発マシンから閉域リソースにアクセスするには、以下の方法があります:

#### オプション1: Azure Bastionを使用(推奨)

```powershell
# Azure Bastionを使用してVNet内のVMに接続
# Azure Portalからリソース → Bastion → 接続
```

#### オプション2: Point-to-Site VPN

```powershell
# VPN証明書を生成してインストール
# Azure PortalからVirtual Network Gateway → Point-to-site configuration
```

#### オプション3: ローカル開発時のManaged Identity

ローカル開発では、Azure CLIでログインしたユーザーの認証情報を使用します。

```powershell
# 現在のユーザーにRBACロールを付与
$CURRENT_USER_ID = (az ad signed-in-user show --query id -o tsv)

# Cognitive Services OpenAI ユーザー
az role assignment create `
    --assignee $CURRENT_USER_ID `
    --role "Cognitive Services OpenAI User" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/rg-internal-rag-dev/providers/Microsoft.CognitiveServices/accounts/<openai-name>"

# Search Index Data Reader
az role assignment create `
    --assignee $CURRENT_USER_ID `
    --role "Search Index Data Reader" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/rg-internal-rag-dev/providers/Microsoft.Search/searchServices/<search-name>"

# Storage Blob Data Contributor
az role assignment create `
    --assignee $CURRENT_USER_ID `
    --role "Storage Blob Data Contributor" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/rg-internal-rag-dev/providers/Microsoft.Storage/storageAccounts/<storage-name>"
```

### 7. Azure Functions ローカル実行テスト

```powershell
# 仮想環境が有効化されていることを確認
# プロンプトに (venv) が表示される

# Azure Functions Core Toolsで起動
func start

# 別のターミナルでテスト
curl http://localhost:7071/api/health
```

ブラウザで `http://localhost:7071` にアクセスして、チャットUIが表示されることを確認します。

### 8. Azure接続テストスクリプトの実行

```powershell
# Azure接続テストスクリプトを実行
python scripts/test-azure-connection.py

# 期待される出力:
# ✅ Azure OpenAI接続成功
# ✅ Azure AI Search接続成功
# ✅ Azure Storage接続成功
```

### 9. GitHub Secretsの設定

GitHub ActionsでCI/CDを実行するために、以下のSecretsを設定します。

#### GitHub CLIを使用

```powershell
# GitHub CLIでログイン
gh auth login

# Secretsを設定
gh secret set AZURE_CLIENT_ID --body "your-client-id"
gh secret set AZURE_TENANT_ID --body "your-tenant-id"
gh secret set AZURE_SUBSCRIPTION_ID --body "your-subscription-id"
gh secret set AZURE_OPENAI_ENDPOINT --body "https://your-openai.openai.azure.com/"
gh secret set AZURE_OPENAI_DEPLOYMENT --body "gpt-4"
gh secret set AZURE_SEARCH_ENDPOINT --body "https://your-search.search.windows.net"
gh secret set AZURE_SEARCH_INDEX --body "redlist-index"

# 設定確認
gh secret list
```

#### Azure Portalを使用

1. GitHubリポジトリページを開く
2. `Settings` → `Secrets and variables` → `Actions`
3. `New repository secret` をクリック
4. 以下のSecretsを追加:
   - `AZURE_CLIENT_ID`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `AZURE_SEARCH_ENDPOINT`
   - `AZURE_SEARCH_INDEX`

### 10. Azure Functions環境変数の設定

```powershell
$RESOURCE_GROUP = "rg-internal-rag-dev"
$FUNCTIONAPP_NAME = "func-internal-rag-dev"

# Azure Functions環境変数を設定
az functionapp config appsettings set `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME `
    --settings `
        AZURE_OPENAI_ENDPOINT="https://your-openai.openai.azure.com/" `
        AZURE_OPENAI_DEPLOYMENT="gpt-4" `
        AZURE_SEARCH_ENDPOINT="https://your-search.search.windows.net" `
        AZURE_SEARCH_INDEX="redlist-index" `
        AzureWebJobsFeatureFlags="EnableWorkerIndexing" `
        FUNCTIONS_WORKER_RUNTIME="python"

# 設定確認
az functionapp config appsettings list `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME `
    --output table
```

### 11. Azure Functions Managed Identityの権限設定

```powershell
# Functions AppのManaged Identityを有効化
az functionapp identity assign `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME

# Managed IdentityのPrincipal IDを取得
$PRINCIPAL_ID = az functionapp identity show `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME `
    --query principalId -o tsv

Write-Host "Principal ID: $PRINCIPAL_ID"

# Cognitive Services OpenAI ユーザー
az role assignment create `
    --assignee $PRINCIPAL_ID `
    --role "Cognitive Services OpenAI User" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/rg-internal-rag-dev/providers/Microsoft.CognitiveServices/accounts/<openai-name>"

# Search Index Data Reader
az role assignment create `
    --assignee $PRINCIPAL_ID `
    --role "Search Index Data Reader" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/rg-internal-rag-dev/providers/Microsoft.Search/searchServices/<search-name>"

# Storage Blob Data Reader
az role assignment create `
    --assignee $PRINCIPAL_ID `
    --role "Storage Blob Data Reader" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/rg-internal-rag-dev/providers/Microsoft.Storage/storageAccounts/<storage-name>"
```

### 12. AI Search Managed Identityの権限設定

AI SearchがBlob Storageからデータを読み取るために、Managed Identityに権限を付与します。

```powershell
# AI SearchのManaged Identityを有効化
az search service update `
    --resource-group $RESOURCE_GROUP `
    --name <your-search-name> `
    --identity-type SystemAssigned

# AI SearchのPrincipal IDを取得
$SEARCH_PRINCIPAL_ID = az search service show `
    --resource-group $RESOURCE_GROUP `
    --name <your-search-name> `
    --query identity.principalId -o tsv

Write-Host "AI Search Principal ID: $SEARCH_PRINCIPAL_ID"

# Storage Blob Data Reader権限を付与
az role assignment create `
    --assignee $SEARCH_PRINCIPAL_ID `
    --role "Storage Blob Data Reader" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/rg-internal-rag-dev/providers/Microsoft.Storage/storageAccounts/<storage-name>"
```

### 13. 権限設定の確認

```powershell
# Functions Appの権限を確認
Write-Host "`nFunctions App ロール割り当て:" -ForegroundColor Cyan
az role assignment list --all --query "[?principalId=='$PRINCIPAL_ID'].{Role:roleDefinitionName, Scope:scope}" -o table

# AI Searchの権限を確認
Write-Host "`nAI Search ロール割り当て:" -ForegroundColor Cyan
az role assignment list --all --query "[?principalId=='$SEARCH_PRINCIPAL_ID'].{Role:roleDefinitionName, Scope:scope}" -o table
```

## 確認事項

以下をすべて確認してください:

- ✅ GitHubリポジトリがフォーク/作成されている
- ✅ ローカルにクローンされている
- ✅ Python仮想環境が作成されている
- ✅ 依存関係がインストールされている
- ✅ `.env` ファイルが作成され、設定されている
- ✅ Azureリソース情報が収集されている
- ✅ ローカル開発用の権限が付与されている
- ✅ Azure接続テストが成功している
- ✅ GitHub Secretsが設定されている
- ✅ Azure Functionsの環境変数が設定されている
- ✅ Azure Functions Managed Identityの権限が付与されている

> 📝 **GitHub Self-hosted Runner について**
> 
> GitHub ActionsでCI/CDを実行するためのSelf-hosted Runnerは、**[internal_rag_Application_deployment_step_by_step](https://github.com/matakaha/internal_rag_Application_deployment_step_by_step)** リポジトリで構築します。
> 
> deployment_step_by_stepの **Step 02: VMベースRunner構築** で以下が自動セットアップされます:
> - ✅ Ubuntu 22.04 LTS VM
> - ✅ Azure CLI インストール済み
> - ✅ GitHub Actions Runner インストール・登録済み
> - ✅ vNet統合によるPrivate Endpointアクセス可能
> - ✅ NAT Gateway経由でインターネットアクセス可能
> 
> このリポジトリでは、deployment_step_by_stepで構築されたVMベースRunnerを使用します。
> Runnerの構築・管理はdeployment_step_by_stepで完結するため、このリポジトリでは特別な設定は不要です。


## トラブルシューティング

### Python仮想環境が作成できない

**症状**: `python -m venv venv` がエラーになる

**対処法**:
```powershell
# Pythonのバージョンを確認
python --version

# 3.11以上であることを確認
# 古い場合は最新版をインストール
```

### Azure CLIでログインできない

**症状**: `az login` がエラーになる

**対処法**:
```powershell
# Azure CLIを最新版に更新
az upgrade

# ブラウザベースのログインを試す
az login --use-device-code
```

### Private Endpointリソースに接続できない

**症状**: ローカルからAzure OpenAI/AI Searchに接続できない

**対処法**:
1. Azure Bastionを使用してVNet内のVMに接続
2. Point-to-Site VPNを設定
3. または、deployment_step_by_stepで構築したVMを使用

### Managed Identity権限エラー

**症状**: Functions AppからAzure OpenAI/AI Searchにアクセスできない

**対処法**:
```powershell
# Managed Identityが有効化されているか確認
az functionapp identity show `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME

# ロール割り当てを確認
az role assignment list --all --query "[?principalId=='$PRINCIPAL_ID']" -o table

# 必要に応じてロールを再割り当て
```

## 次のステップ

環境準備が完了したら、次は **[Step 2: データ準備](step02-data-preparation.md)** に進みましょう。

e-Govデータポータルからレッドリストデータをダウンロードし、Azure Blob Storageにアップロードします。
