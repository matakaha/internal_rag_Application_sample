# Step 4: アプリケーションデプロイ

このステップでは、RAGチャットアプリケーション（フロントエンド・バックエンド）をAzureにデプロイします。

## 📚 学習目標

このステップを完了すると、以下ができるようになります:

- Azure Web Appsへの環境変数設定
- Federated Credentials (OIDC)を使用したGitHub Actions認証設定
- ローカル環境でのアプリケーション動作確認
- GitHub Actionsを使用したCI/CDパイプライン実行
- デプロイ後の動作確認とトラブルシューティング

## 前提条件

以下が完了していることを確認してください:

- ✅ Step 1（環境準備）が完了している
- ✅ Step 2（データ準備）が完了し、Blob Storageにデータがアップロードされている
- ✅ Step 3（インデックス作成）が完了し、AI Searchインデックスが構築されている
- ✅ Azure Web Apps リソースが作成されている
- ✅ Azure Functions リソースが作成されている
- ✅ GitHub Self-hosted Runner VMが稼働している

## アーキテクチャ概要

```
┌─────────────────┐
│   ユーザー       │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────┐
│  Azure Web Apps (Frontend)      │
│  - React 18 + Vite              │
│  - 静的ファイル配信              │
└────────┬────────────────────────┘
         │ HTTPS API Call
         ▼
┌─────────────────────────────────┐
│  Azure Functions (Backend)      │
│  - Python 3.11                  │
│  - /api/chat (Streaming)        │
│  - /api/health                  │
└────────┬────────────────────────┘
         │ Private Endpoint
         ▼
┌─────────────────────────────────┐
│  Azure OpenAI (On Your Data)   │
│  ├─ GPT-4 Deployment            │
│  └─ AI Search Integration       │
└────────┬────────────────────────┘
         │ Private Endpoint
         ▼
┌─────────────────────────────────┐
│  Azure AI Search                │
│  - redlist-index (3,597 docs)   │
└─────────────────────────────────┘
```

## セットアップ手順

### 1. Web Appsに環境変数を設定

フロントエンドがバックエンドAPIエンドポイントを参照するため、Web Appsに環境変数を設定します。

#### オプションA: Azure Portalで設定

1. [Azure Portal](https://portal.azure.com) を開く
2. Web Appsリソースに移動
3. 左メニューから「構成」→「アプリケーション設定」を選択
4. 「新しいアプリケーション設定」をクリック
5. 以下の設定を追加:

   | 名前 | 値 |
   |------|-----|
   | `VITE_API_ENDPOINT` | `https://<your-functionapp-name>.azurewebsites.net` |

6. 「保存」をクリック

#### オプションB: Azure CLIで設定

```powershell
# 環境変数を設定
$RESOURCE_GROUP = "rg-internal-rag-dev"
$WEBAPP_NAME = "<your-webapp-name>"
$FUNCTIONAPP_NAME = "<your-functionapp-name>"

# Web AppsにAPI Endpoint設定
az webapp config appsettings set `
    --resource-group $RESOURCE_GROUP `
    --name $WEBAPP_NAME `
    --settings VITE_API_ENDPOINT="https://$FUNCTIONAPP_NAME.azurewebsites.net"

# 設定確認
az webapp config appsettings list `
    --resource-group $RESOURCE_GROUP `
    --name $WEBAPP_NAME `
    --query "[?name=='VITE_API_ENDPOINT']" -o table
```

### 2. Federated Credentials (OIDC)の設定

GitHub ActionsからAzureにデプロイするため、OIDC認証を設定します。

#### 2.1 App Registrationの作成

```powershell
# Azure ADにアプリケーション登録
$APP_NAME = "github-actions-rag-app"

az ad app create --display-name $APP_NAME

# Application IDを取得
$APP_ID = az ad app list --display-name $APP_NAME --query "[0].appId" -o tsv
Write-Host "Application (Client) ID: $APP_ID"

# Service Principalを作成
az ad sp create --id $APP_ID

# Service Principal Object IDを取得
$SP_OBJECT_ID = az ad sp list --display-name $APP_NAME --query "[0].id" -o tsv
Write-Host "Service Principal Object ID: $SP_OBJECT_ID"
```

#### 2.2 Federated Credentialの追加

```powershell
# GitHubリポジトリ情報
$GITHUB_ORG = "<your-github-username-or-org>"
$GITHUB_REPO = "internal_rag_Application_sample"

# Federated Credential設定をJSONファイルとして作成
$federatedCredJson = @"
{
  "name": "github-actions-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:$GITHUB_ORG/${GITHUB_REPO}:environment:production",
  "description": "GitHub Actions deployment to production",
  "audiences": [
    "api://AzureADTokenExchange"
  ]
}
"@

# 一時ファイルに保存
$tempFile = New-TemporaryFile
$federatedCredJson | Out-File -FilePath $tempFile.FullName -Encoding UTF8

# Federated Credentialを作成
az ad app federated-credential create `
    --id $APP_ID `
    --parameters "@$($tempFile.FullName)"

# 一時ファイルを削除
Remove-Item $tempFile.FullName

Write-Host "✅ Federated Credential created successfully" -ForegroundColor Green
```

#### 2.3 RBACロールの割り当て

```powershell
# Subscription IDを取得
$SUBSCRIPTION_ID = az account show --query id -o tsv

# Contributorロールを割り当て（リソースグループスコープ）
az role assignment create `
    --assignee $SP_OBJECT_ID `
    --role "Contributor" `
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"

# Web Appsへのデプロイ権限
az role assignment create `
    --assignee $SP_OBJECT_ID `
    --role "Website Contributor" `
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$WEBAPP_NAME"

# Functionsへのデプロイ権限
az role assignment create `
    --assignee $SP_OBJECT_ID `
    --role "Website Contributor" `
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTIONAPP_NAME"

Write-Host "✅ RBAC roles assigned successfully"
```

### 3. GitHub Secretsの設定

GitHub ActionsがAzureリソースにアクセスするために必要なSecretsを設定します。

#### 3.1 必要なSecrets一覧

| Secret名 | 説明 | 取得方法 |
|----------|------|----------|
| `AZURE_CLIENT_ID` | App Registration の Application ID | 上記で取得した`$APP_ID` |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | `az account show --query id -o tsv` |
| `RESOURCE_GROUP` | リソースグループ名 | `rg-internal-rag-dev` |
| `AZURE_WEBAPP_NAME` | Web Apps名 | `scripts/get-azure-resources.ps1`で取得 |
| `AZURE_FUNCTIONAPP_NAME` | Functions App名 | `scripts/get-azure-resources.ps1`で取得 |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI Endpoint | `scripts/get-azure-resources.ps1`で取得 |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI Deployment名 | `scripts/get-azure-resources.ps1`で取得 |
| `AZURE_SEARCH_ENDPOINT` | AI Search Endpoint | `scripts/get-azure-resources.ps1`で取得 |
| `AZURE_SEARCH_INDEX` | AI Search Index名 | `redlist-index` |

#### 3.2 GitHub CLIで設定

```powershell
# GitHub CLIでログイン
gh auth login

# Secretsを設定
gh secret set AZURE_CLIENT_ID -b "$APP_ID"
gh secret set AZURE_TENANT_ID -b "$(az account show --query tenantId -o tsv)"
gh secret set AZURE_SUBSCRIPTION_ID -b "$(az account show --query id -o tsv)"
gh secret set RESOURCE_GROUP -b "$RESOURCE_GROUP"
gh secret set AZURE_WEBAPP_NAME -b "$WEBAPP_NAME"
gh secret set AZURE_FUNCTIONAPP_NAME -b "$FUNCTIONAPP_NAME"

# Azure OpenAI / AI Search設定（.envファイルから取得）
gh secret set AZURE_OPENAI_ENDPOINT -b "<your-openai-endpoint>"
gh secret set AZURE_OPENAI_DEPLOYMENT -b "<your-deployment-name>"
gh secret set AZURE_SEARCH_ENDPOINT -b "<your-search-endpoint>"
gh secret set AZURE_SEARCH_INDEX -b "redlist-index"

# 設定確認
gh secret list
```

> 💡 **ヒント**: `scripts/get-azure-resources.ps1`を実行すると、GitHub Secrets設定コマンドが自動生成されます。

### 4. Self-hosted Runnerの動作確認

GitHub ActionsがSelf-hosted Runner上で実行されることを確認します。

```powershell
# Self-hosted Runner VMにSSH接続（Azure Bastionまたは別の方法）
# または、GitHubリポジトリのSettings → Actions → Runners で確認

# Runner一覧を確認
gh api repos/{owner}/{repo}/actions/runners

# 期待される出力: 
# Status: online
# Labels: self-hosted, Linux, X64
```

### 5. ローカル動作確認

デプロイ前にローカル環境で動作確認を行います。

#### 5.1 バックエンド（Azure Functions）のローカル実行

```powershell
# リポジトリルートから実行
cd apps/backend

# Python仮想環境を作成（初回のみ）
python -m venv .venv

# 仮想環境を有効化
.\.venv\Scripts\Activate.ps1

# 依存関係をインストール
pip install -r requirements.txt

# local.settings.jsonを作成
Copy-Item local.settings.json.example local.settings.json

# local.settings.jsonを編集（.envファイルの値を参照）
code local.settings.json
```

**local.settings.json**の設定例:

```json
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
```

Functionsを起動:

```powershell
# Azure Functions Core Toolsで起動
func start

# 期待される出力:
# Functions:
#   chat: [POST] http://localhost:7071/api/chat
#   health: [GET] http://localhost:7071/api/health
```

別のターミナルでヘルスチェック:

```powershell
# ヘルスチェック
curl http://localhost:7071/api/health

# 期待される出力:
# {"status":"healthy","service":"rag-chat-backend","version":"1.0.0"}
```

#### 5.2 フロントエンド（React）のローカル実行

```powershell
# 新しいターミナルを開く
cd apps/frontend

# Node.js依存関係をインストール
npm install

# 開発サーバーを起動
npm run dev

# 期待される出力:
# VITE ready in XXX ms
# ➜  Local:   http://localhost:5173/
```

ブラウザで `http://localhost:5173` を開き、チャット画面が表示されることを確認します。

#### 5.3 エンドツーエンドテスト

1. フロントエンド（`http://localhost:5173`）にアクセス
2. チャット入力欄に質問を入力（例: 「イリオモテヤマネコについて教えてください」）
3. 送信ボタンをクリック
4. ストリーミング表示でAIの回答が表示されることを確認

### 6. GitHub Actionsワークフローの実行

#### 6.1 バックエンドのデプロイ

1. GitHubリポジトリページを開く
2. `Actions` タブをクリック
3. 左サイドバーから `Deploy Backend (Azure Functions)` を選択
4. `Run workflow` ボタンをクリック
5. ブランチを選択（通常は `main`）
6. `Run workflow` をクリック

ワークフローの進行状況を確認:
- ✅ Checkout code
- ✅ Set up Python 3.11
- ✅ Install dependencies
- ✅ Azure Login (OIDC)
- ✅ Configure Function App settings
- ✅ Deploy to Azure Functions
- ✅ Verify deployment

デプロイ完了後、Functions AppのURLにアクセスして確認:

```powershell
# ヘルスチェック
curl https://<your-functionapp-name>.azurewebsites.net/api/health
```

#### 6.2 フロントエンドのデプロイ

1. GitHubリポジトリページの `Actions` タブ
2. 左サイドバーから `Deploy Frontend (Web Apps)` を選択
3. `Run workflow` ボタンをクリック
4. ブランチを選択（通常は `main`）
5. `Run workflow` をクリック

ワークフローの進行状況を確認:
- ✅ Checkout code
- ✅ Set up Node.js 24
- ✅ Azure Login (OIDC)
- ✅ Get API endpoint from Web App settings
- ✅ Generate config.js
- ✅ Install dependencies
- ✅ Build application
- ✅ Deploy to Azure Web App
- ✅ Verify deployment

デプロイ完了後、Web AppsのURLにアクセスして確認:

```powershell
# ブラウザで開く
start https://<your-webapp-name>.azurewebsites.net
```

### 7. デプロイ後の動作確認

#### 7.1 Web Appsへのアクセス

1. ブラウザで `https://<your-webapp-name>.azurewebsites.net` を開く
2. チャット画面が表示されることを確認
3. 質問を入力して送信
4. AIの回答がストリーミング表示されることを確認

#### 7.2 サンプル質問

以下の質問でテストしてください:

1. **基本的な質問**
   - 「イリオモテヤマネコについて教えてください」
   - 「ライチョウの生息地はどこですか？」

2. **フィルタリング質問**
   - 「絶滅危惧IA類（CR）に指定されている哺乳類を教えてください」
   - 「鳥類で絶滅危惧種に指定されている種を教えてください」

3. **詳細情報の質問**
   - 「アユモドキの個体数はどのくらいですか？」
   - 「コウノトリの野生復帰について教えてください」

#### 7.3 ログの確認

Application Insightsでログを確認:

```powershell
# Application Insightsのリソース名を取得
$APPINSIGHTS_NAME = az monitor app-insights component list `
    --resource-group $RESOURCE_GROUP `
    --query "[0].name" -o tsv

# ログクエリを実行（過去1時間）
az monitor app-insights query `
    --app $APPINSIGHTS_NAME `
    --analytics-query "traces | where timestamp > ago(1h) | order by timestamp desc | take 50" `
    --output table
```

Azure Portalでの確認:
1. Application Insightsリソースを開く
2. 「ログ」→「traces」テーブルをクエリ
3. エラーや詳細ログを確認

## 確認事項

以下をすべて確認してください:

- ✅ Web Appsに環境変数（`VITE_API_ENDPOINT`）が設定されている
- ✅ Federated Credentials (OIDC)が正しく設定されている
- ✅ GitHub Secretsが全て設定されている
- ✅ Self-hosted Runnerが正常に動作している
- ✅ ローカル環境でバックエンド・フロントエンドが動作する
- ✅ GitHub Actionsでバックエンドがデプロイされている
- ✅ GitHub Actionsでフロントエンドがデプロイされている
- ✅ Web Appsにアクセスしてチャットが動作する
- ✅ ストリーミングレスポンスが正常に表示される

## トラブルシューティング

### バックエンドAPI呼び出しエラー

**症状**: フロントエンドからバックエンドAPIへの通信が失敗する

**確認手順**:

1. **CORSの確認**

Functions AppのCORS設定で、Web AppsのURLが許可されているか確認してください。

```powershell
# CORS設定を確認
az functionapp cors show `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME

# 期待される出力に以下が含まれること:
# https://<your-webapp-name>.azurewebsites.net
```

2. **ネットワーク接続の確認**

```powershell
# Functions AppのURLにアクセス
curl https://<your-functionapp-name>.azurewebsites.net/api/health

# エラーの場合、Functions Appのログを確認
az functionapp log tail `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME
```

3. **ブラウザの開発者ツールで確認**

- F12キーで開発者ツールを開く
- 「Network」タブでAPIリクエストのステータスを確認
- 「Console」タブでエラーメッセージを確認

### Azure OpenAI接続エラー

**症状**: バックエンドがAzure OpenAIに接続できない

**確認手順**:

1. **Managed Identityの権限確認**

```powershell
# Functions AppのManaged Identity Object IDを取得
$PRINCIPAL_ID = az functionapp identity show `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME `
    --query principalId -o tsv

# ロール割り当てを確認
az role assignment list `
    --assignee $PRINCIPAL_ID `
    --query "[?roleDefinitionName=='Cognitive Services OpenAI User']" `
    --output table

# ロールが無い場合は割り当て
az role assignment create `
    --assignee $PRINCIPAL_ID `
    --role "Cognitive Services OpenAI User" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/<openai-name>"
```

2. **Application Insightsログの確認**

```powershell
# エラーログを検索
az monitor app-insights query `
    --app $APPINSIGHTS_NAME `
    --analytics-query "traces | where severityLevel >= 3 | where message contains 'OpenAI' | order by timestamp desc | take 10" `
    --output table
```

詳細なエラーメッセージから原因を特定します:
- `401 Unauthorized`: Managed Identityの権限不足
- `429 Too Many Requests`: API制限到達
- `500 Internal Server Error`: Azure OpenAI側の問題

### AI Search接続エラー

**症状**: AI Searchからデータを取得できない

**確認手順**:

1. **Managed Identityの権限確認**

```powershell
# ロール割り当てを確認
az role assignment list `
    --assignee $PRINCIPAL_ID `
    --query "[?roleDefinitionName=='Search Index Data Reader']" `
    --output table

# ロールが無い場合は割り当て
az role assignment create `
    --assignee $PRINCIPAL_ID `
    --role "Search Index Data Reader" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Search/searchServices/<search-name>"
```

2. **インデックスの存在確認**

```powershell
# インデックスを確認
az search index show `
    --resource-group $RESOURCE_GROUP `
    --service-name <search-name> `
    --name redlist-index

# ドキュメント数を確認（Azure Portalで確認推奨）
```

### ストリーミングレスポンスが表示されない

**症状**: チャットの回答が一度に表示される、またはストリーミングが機能しない

**確認手順**:

1. **ブラウザの開発者ツールで確認**

- NetworkタブでAPIリクエストを確認
- Content-Type: `text/event-stream`になっているか確認
- Responseタブでストリーミングデータを確認

2. **バックエンドログの確認**

```powershell
# ストリーミング関連のログを検索
az monitor app-insights query `
    --app $APPINSIGHTS_NAME `
    --analytics-query "traces | where message contains 'Streaming' | order by timestamp desc | take 20" `
    --output table
```

3. **Web Appsのバッファリング設定**

Azure Web AppsでHTTPレスポンスバッファリングが有効になっている場合、ストリーミングが機能しません。

```powershell
# Web Appsの設定確認
az webapp config show `
    --resource-group $RESOURCE_GROUP `
    --name $WEBAPP_NAME `
    --query "httpLoggingEnabled"
```

### GitHub Actions デプロイエラー

**症状**: GitHub Actionsワークフローが失敗する

**確認手順**:

1. **OIDC認証エラー**

エラーメッセージ: `AADSTS700016: Application with identifier was not found in the directory`

→ Federated Credentialの`subject`が正しいか確認:

```
subject: repo:<owner>/<repo>:environment:production
```

2. **権限エラー**

エラーメッセージ: `AuthorizationFailed: The client does not have authorization to perform action`

→ Service PrincipalにContributorロールが割り当てられているか確認

3. **Self-hosted Runner未接続**

エラーメッセージ: `No runner available`

→ Self-hosted Runner VMが起動しているか確認

```powershell
# GitHubでRunner状態を確認
gh api repos/{owner}/{repo}/actions/runners
```

### Private Endpoint疎通エラー

**症状**: ローカルからAzure OpenAI / AI Searchにアクセスできない

**対処法**:

閉域環境のため、ローカル開発はAzure Bastion、Point-to-Site VPN、またはSelf-hosted Runner VM上で行う必要があります。Step 1の「ローカル開発環境のセットアップ」を参照してください。

### Application Insightsログが表示されない

**症状**: ログクエリで結果が返ってこない

**確認手順**:

1. **Application Insightsの有効化確認**

```powershell
# Functions AppのApplication Insights設定を確認
az functionapp config appsettings list `
    --resource-group $RESOURCE_GROUP `
    --name $FUNCTIONAPP_NAME `
    --query "[?name=='APPINSIGHTS_INSTRUMENTATIONKEY']" -o table
```

2. **ログ収集の遅延**

Application Insightsへのログ反映には数分かかる場合があります。少し待ってから再度確認してください。

## 次のステップ

アプリケーションデプロイが完了しました！🎉

### さらなる改善案

- **認証・認可の追加**: Azure AD B2C、Entra IDを使用したユーザー認証
- **チャット履歴の永続化**: Azure Cosmos DBでセッション管理
- **モニタリングの強化**: Azure Monitor、Application Insightsダッシュボード
- **スケーリング**: App Service Planのスケールアップ/スケールアウト
- **CI/CDの自動化**: mainブランチへのpush時に自動デプロイ

### 参考リソース

- [Azure Functions Python developer guide](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- [Azure OpenAI On Your Data](https://learn.microsoft.com/azure/ai-services/openai/concepts/use-your-data)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)
- [GitHub Actions OIDC with Azure](https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure)
