# 閉域環境でのRAGアプリケーション実装サンプル

環境省のレッドリスト（絶滅危惧種）データを使用した、閉域環境（Private Endpoint）でのRAG（Retrieval-Augmented Generation）チャットアプリケーションの実装サンプルです。初学者がAzure上でRAGアプリケーションを構築・デプロイする方法を段階的に学べるチュートリアルを提供します。

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Azure Functions](https://img.shields.io/badge/Azure%20Functions-Python%203.11-blue)](https://azure.microsoft.com/services/functions/)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://reactjs.org/)
[![Azure OpenAI](https://img.shields.io/badge/Azure%20OpenAI-GPT--4-412991)](https://azure.microsoft.com/products/ai-services/openai-service)

</div>

## 🎯 プロジェクト概要

このリポジトリは、**閉域環境（Private Endpoint）でのRAGアプリケーション開発**を学ぶための実践的なサンプルです。公開データ（環境省レッドリスト）を使用し、初学者でも段階的にRAGの仕組みを理解できるように設計されています。

### 主な特徴

- ✅ **閉域環境対応** - Private Endpointを使用したセキュアな構成
- ✅ **Azure OpenAI On Your Data** - AI Searchとのシームレスな統合
- ✅ **グラウンデッド回答** - AI Searchの検索結果に基づく回答生成
- ✅ **Managed Identity認証** - キーレスなセキュアな認証
- ✅ **GitHub Actions CI/CD** - OIDC認証によるセキュアなデプロイ
- ✅ **段階的チュートリアル** - Step01～04で体系的に学習

### 使用データ

- **データソース**: [e-Govデータポータル - 環境省レッドリスト（第4次）](https://data.e-gov.go.jp/data/dataset/env_20140904_0456)
- **データ件数**: 3,597件（哺乳類、鳥類、爬虫類、両生類、汽水・淡水魚類、昆虫類、貝類、その他無脊椎動物、維管束植物）
- **データ形式**: JSON Lines（Azure AI Search用に前処理済み）

## 🏗️ アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        Azure Virtual Network                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                                                              │ │
│  │  ┌──────────────────┐         ┌──────────────────┐         │ │
│  │  │  Azure Functions │◄────────┤  Azure OpenAI    │         │ │
│  │  │  (Backend API)   │ Private │  (On Your Data)  │         │ │
│  │  │  - Python 3.11   │Endpoint │  - GPT-4         │         │ │
│  │  │  - /api/chat     │         │  - Embedding     │         │ │
│  │  │  - Thin Backend  │         └──────────────────┘         │ │
│  │  └──────────────────┘                   │                   │ │
│  │           ▲                              │ Private           │ │
│  │           │                              │ Endpoint          │ │
│  │           │                              ▼                   │ │
│  │  ┌──────────────────┐         ┌──────────────────┐         │ │
│  │  │  Azure Web Apps  │         │  Azure AI Search │         │ │
│  │  │  (Frontend)      │         │  - redlist-index │         │ │
│  │  │  - React + Vite  │         │  - 3,597 docs    │         │ │
│  │  └──────────────────┘         └──────────────────┘         │ │
│  │                                          │                   │ │
│  │                                          │ Private           │ │
│  │                                          │ Endpoint          │ │
│  │                                          ▼                   │ │
│  │                               ┌──────────────────┐          │ │
│  │                               │  Blob Storage    │          │ │
│  │                               │  - redlist data  │          │ │
│  │                               └──────────────────┘          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │ Self-hosted Runner (GitHub Actions)
                               │
                    ┌──────────────────────┐
                    │  GitHub Repository   │
                    │  - CI/CD Workflows   │
                    └──────────────────────┘
```

## 📁 ディレクトリ構造

```
internal_rag_Application_sample/
├── apps/
│   ├── backend/                    # Azure Functions (Python 3.11)
│   │   ├── function_app.py         # メインAPI実装
│   │   ├── requirements.txt        # Python依存関係
│   │   ├── host.json               # Functions設定
│   │   └── local.settings.json.example
│   └── frontend/                   # React + Vite
│       ├── src/
│       │   ├── App.jsx             # チャットUI
│       │   └── main.jsx
│       ├── index.html
│       ├── package.json
│       └── vite.config.js
├── docs/
│   ├── step01-setup-environment.md # Step 1: 環境準備
│   ├── step02-data-preparation.md  # Step 2: データ準備
│   ├── step03-indexing.md          # Step 3: インデックス作成
│   └── step04-deploy-application.md# Step 4: アプリデプロイ
├── scripts/
│   ├── get-azure-resources.ps1     # Azure情報収集
│   ├── download-redlist-data.ps1   # データダウンロード
│   ├── prepare-redlist-data.py     # データ前処理
│   ├── create-index.ps1            # AI Searchインデックス作成
│   ├── create-datasource.ps1       # データソース作成
│   └── create-indexer.ps1          # インデクサー作成
├── .github/
│   └── workflows/
│       ├── deploy-backend.yml      # Functions自動デプロイ
│       └── deploy-frontend.yml     # Web Apps自動デプロイ
├── .gitignore
├── LICENSE
└── README.md
```

## 🚀 クイックスタート

### 前提条件

このリポジトリを使用する前に、以下が完了している必要があります：

1. **Azureインフラの構築**
   - [internal_rag_step_by_step_bicep](https://github.com/matakaha/internal_rag_step_by_step_bicep) リポジトリでAzureリソースを作成
   - 作成されるリソース: VNet、Azure OpenAI、AI Search、Storage、Functions、Web Apps

2. **必要なツール**
   - Azure CLI (2.50.0以上)
   - Python 3.11以上
   - Node.js 24.11.0
   - Azure Functions Core Tools (4.x以上)
   - Git 2.30以上

### セットアップ手順（4ステップ）

このチュートリアルは4つのステップで構成されています。各ステップのドキュメントに従って進めてください。

#### 📝 [Step 1: 環境準備](docs/step01-setup-environment.md)

```powershell
# リポジトリをクローン
git clone https://github.com/<your-username>/internal_rag_Application_sample.git
cd internal_rag_Application_sample

# Azure情報を自動収集
.\scripts\get-azure-resources.ps1 -ResourceGroup "rg-internal-rag-dev"
```

- GitHubリポジトリのセットアップ
- Azure CLIでのリソース確認
- ローカル開発環境の構築
- Managed Identity権限設定

#### 📊 [Step 2: データ準備](docs/step02-data-preparation.md)

```powershell
# レッドリストデータをダウンロード
.\scripts\download-redlist-data.ps1

# データを前処理（JSONL形式に変換）
python scripts\prepare-redlist-data.py

# Blob Storageにアップロード
az storage blob upload --account-name <storage> --container-name rag-documents --name redlist-documents.jsonl --file data/processed/redlist-documents.jsonl --auth-mode login
```

- e-Govからレッドリストデータ取得
- データの前処理と整形
- Azure Blob Storageへのアップロード

#### 🔍 [Step 3: AI Searchインデックス作成](docs/step03-indexing.md)

```powershell
# インデックス作成
.\scripts\create-index.ps1 -SearchService <search-name> -SearchAdminKey <key>

# データソース作成
.\scripts\create-datasource.ps1 -SearchService <search-name> -SearchAdminKey <key> -StorageAccountName <storage>

# インデクサー作成・実行
.\scripts\create-indexer.ps1 -SearchService <search-name> -SearchAdminKey <key>
```

- AI Searchインデックススキーマ定義
- データソース設定（Blob Storage）
- インデクサー作成と実行
- セマンティック検索設定

#### 🚢 [Step 4: アプリケーションデプロイ](docs/step04-deploy-application.md)

```powershell
# ローカルで動作確認
cd apps/backend && func start
cd apps/frontend && npm install && npm run dev

# GitHub ActionsでデプロイGitHub Actions -> Deploy Backend -> Run workflow
# GitHub Actions -> Deploy Frontend -> Run workflow
```

- Web Apps環境変数設定
- Federated Credentials (OIDC)設定
- ローカル動作確認
- GitHub Actionsによる自動デプロイ

## 💻 技術スタック

### バックエンド
- **Azure Functions** - サーバーレスAPI（Python 3.11）
- **Azure OpenAI** - GPT-4（On Your Data機能）
- **Azure AI Search** - セマンティック検索（3,597ドキュメント）
- **Azure Identity** - Managed Identity認証

### フロントエンド
- **React 18** - UIフレームワーク
- **Vite** - ビルドツール
- **Azure Web Apps** - 静的ファイルホスティング

### インフラ・DevOps
- **Azure Private Endpoint** - 閉域ネットワーク
- **GitHub Actions** - CI/CDパイプライン
- **OIDC認証** - セキュアなAzure接続
- **Self-hosted Runner** - VNet内でのデプロイ実行

## 📖 ドキュメント

詳細なドキュメントは[docs/](docs/)ディレクトリを参照してください：

| ドキュメント | 説明 |
|------------|------|
| [step01-setup-environment.md](docs/step01-setup-environment.md) | 環境準備とAzureリソース設定 |
| [step02-data-preparation.md](docs/step02-data-preparation.md) | レッドリストデータの取得と前処理 |
| [step03-indexing.md](docs/step03-indexing.md) | AI Searchインデックスの作成 |
| [step04-deploy-application.md](docs/step04-deploy-application.md) | アプリケーションのデプロイ |

## 🎓 学習のポイント

このサンプルを通じて、以下を学ぶことができます：

1. **RAGアーキテクチャ** - Retrieval-Augmented Generationの実装パターン
2. **Azure OpenAI On Your Data** - AI SearchとOpenAIの統合方法
3. **閉域環境構築** - Private Endpointを使用したセキュアな構成
4. **Managed Identity** - キーレス認証のベストプラクティス
5. **グラウンデッド回答** - 検索結果に基づく回答生成と引用の扱い
6. **CI/CD** - GitHub ActionsとOIDCを使ったセキュアなデプロイ

## 🔒 セキュリティ

このサンプルは以下のセキュリティベストプラクティスに従っています：

- ✅ **Private Endpoint** - すべてのAzureサービスが閉域ネットワーク内
- ✅ **Managed Identity** - アクセスキーを使用しない認証
- ✅ **OIDC認証** - GitHub ActionsからAzureへの安全な接続
- ✅ **RBAC** - 最小権限の原則に基づくロール割り当て
- ✅ **Application Insights** - 詳細なログとモニタリング

> **注意**: このサンプルは学習目的であり、認証・認可機能は含まれていません。本番環境では適切な認証機能（Azure AD B2C等）を追加してください。
>
> また、Azure OpenAI On Your Data を**閉域RAG**として成立させるには、Functions から Azure OpenAI に到達できるだけでなく、**Azure OpenAI / Foundry から Azure AI Search へもプライベート接続**できる構成が必要です。このリポジトリでは、その前提ネットワークは別のインフラ用リポジトリで構築済みである想定です。

## 🤝 コントリビューション

このプロジェクトは初学者向けの教育目的で作成されています。改善提案やバグ報告は歓迎します！

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙏 謝辞

- **データ提供**: [e-Govデータポータル](https://data.e-gov.go.jp/) - 環境省レッドリスト（第4次）
- **インフラ構築**: [internal_rag_step_by_step_bicep](https://github.com/matakaha/internal_rag_step_by_step_bicep) - Azureリソース構築ガイド

## 📞 サポート

質問やサポートが必要な場合は、以下の方法でお問い合わせください：

- **Issues**: [GitHubのIssuesセクション](https://github.com/<your-username>/internal_rag_Application_sample/issues)で質問や問題を報告
- **ドキュメント**: [docs/](docs/)ディレクトリ内のトラブルシューティングセクションを参照

---

<div align="center">

**初学者が閉域環境でRAGアプリケーションを実装するための包括的なサンプル**

Made with ❤️ for Azure learners

</div>
