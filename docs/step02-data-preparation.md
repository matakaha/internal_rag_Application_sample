# Step 2: データ準備

このステップでは、RAGシステムで使用するデータを準備します。e-Govデータポータルのレッドリスト/レッドデータブック(第4次レッドリスト)をダウンロードし、Azure Blob Storageにアップロードします。

## 📚 学習目標

このステップを完了すると、以下ができるようになります:

- e-Govデータポータルからのデータ取得方法
- CSVデータの確認と前処理
- Azure Blob Storageへのデータアップロード
- データ格納の確認

## データソース

環境省が公開しているレッドリスト(絶滅危惧種)のデータを使用します:

**データセットURL**: https://data.e-gov.go.jp/data/dataset/env_20140904_0456

このデータセットには、以下のカテゴリのCSVファイルが含まれています:
- 哺乳類
- 鳥類
- 爬虫類
- 両生類
- 汽水・淡水魚類
- 昆虫類
- 貝類
- その他無脊椎動物
- 植物Ⅰ(維管束植物)
- 植物Ⅱ(藻類、蘚苔類、地衣類、菌類)

各カテゴリには、学名、和名、絶滅危惧ランクなどの情報が含まれています。

## データ準備手順

### 1. データセットのダウンロード

#### e-Govデータポータルからダウンロード

以下のURLから各カテゴリのCSVファイルをダウンロードします。

**ダウンロードスクリプト** (`scripts/download-redlist-data.ps1`):

```powershell
# レッドリストデータダウンロードスクリプト

# データ保存ディレクトリを作成
New-Item -ItemType Directory -Force -Path "data\raw" | Out-Null

# ダウンロードするCSVファイルのURL一覧
$datasets = @{
    "哺乳類" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_honyurui.csv"
    "鳥類" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_tyorui.csv"
    "爬虫類" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_hachurui.csv"
    "両生類" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_ryouseirui.csv"
    "汽水淡水魚類" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_tansuigyorui.csv"
    "昆虫類" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_kontyurui_2.csv"
    "貝類" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_kairui_1.csv"
    "その他無脊椎動物" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_invertebrate_1.csv"
    "維管束植物" = "https://ikilog.biodic.go.jp/rdbdata/files/rl2012/redList2012_ikansoku.csv"
}

Write-Host "レッドリストデータをダウンロードしています..." -ForegroundColor Cyan

foreach ($category in $datasets.Keys) {
    $url = $datasets[$category]
    $filename = Split-Path $url -Leaf
    $outputPath = "data\raw\$filename"
    
    Write-Host "  - $category ($filename)..." -NoNewline
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $outputPath
        Write-Host " ✓" -ForegroundColor Green
    } catch {
        Write-Host " ✗ エラー: $_" -ForegroundColor Red
    }
}

Write-Host "`nダウンロード完了!" -ForegroundColor Green
Write-Host "保存先: data\raw\" -ForegroundColor Yellow

# ダウンロードファイル一覧を表示
Get-ChildItem -Path "data\raw" -Filter "*.csv" | Format-Table Name, Length, LastWriteTime
```

このスクリプトを保存して実行:

```powershell
.\scripts\download-redlist-data.ps1
```

### 2. データの確認と前処理

ダウンロードしたCSVファイルの内容を確認します。

```powershell
# CSVファイルの確認(最初の数行を表示)
# Shift-JISエンコーディングで読み込む
Get-Content data\raw\redList2012_honyurui.csv -Encoding Default | Select-Object -First 10

# または、Pythonで確認
python
```

期待される出力:
```
カテゴリー,分類群,和名,学名
絶滅（EX）,哺乳類,オキナワオオコウモリ,Pteropus loochoensis
絶滅（EX）,哺乳類,ミヤココキクガシラコウモリ,Rhinolophus pumilus miyakonis
絶滅（EX）,哺乳類,オガサワラアブラコウモリ,Pipistrellus sturdeei
絶滅（EX）,哺乳類,エゾオオカミ,Canis lupus hattai
絶滅（EX）,哺乳類,ニホンオオカミ,Canis lupus hodophilax
絶滅（EX）,哺乳類,ニホンカワウソ（本州以南亜種）,Lutra lutra nippon
絶滅（EX）,哺乳類,ニホンカワウソ（北海道亜種）,Lutra lutra whiteleyi
絶滅危惧ⅠA類（CR）,哺乳類,センカクモグラ,Mogera uchidai
絶滅危惧ⅠA類（CR）,哺乳類,ダイトウオオコウモリ,Pteropus dasymallus daitoensis
```

Pythonでデータを確認する場合:

```powershell
# venv環境を有効化
.\venv\Scripts\Activate.ps1

# Pythonを起動
python
```

```python
import pandas as pd

# CSVファイルを読み込み(CP932エンコーディング)
df = pd.read_csv('data/raw/redList2012_honyurui.csv', encoding='cp932')

# データの概要を表示
print(f"行数: {len(df)}")
print(f"列名: {df.columns.tolist()}")
print("\n最初の5行:")
print(df.head())

# カテゴリ(絶滅危惧ランク)の分布を確認
print("\n絶滅危惧ランク分布:")
print(df.iloc[:, 0].value_counts())  # 1列目がカテゴリー

# Pythonを終了
exit()
```

期待される出力:
```
行数: 72
列名: ['カテゴリー', '分類群', '和名', '学名']

最初の5行:
           カテゴリー  分類群                  和名                      学名
0       絶滅（EX）  哺乳類        オキナワオオコウモリ    Pteropus loochoensis
1       絶滅（EX）  哺乳類  ミヤココキクガシラコウモリ  Rhinolophus pumilus ...
2       絶滅（EX）  哺乳類    オガサワラアブラコウモリ   Pipistrellus sturdeei
3       絶滅（EX）  哺乳類            エゾオオカミ       Canis lupus hattai
4       絶滅（EX）  哺乳類           ニホンオオカミ     Canis lupus hodophilax

絶滅危惧ランク分布:
絶滅危惧Ⅱ類（VU）      31
絶滅危惧ⅠB類（EN）      15
絶滅（EX）            10
絶滅危惧ⅠA類（CR）       9
準絶滅危惧（NT）         7
```

> 📝 **Note**: ガイドに記載されているコードブロックは説明用のサンプルです。Python対話モードでは、一度に1つのコマンドを実行してください。

#### データ形式の例

レッドリストCSVの典型的な形式:

```csv
学名,和名,カテゴリー,科名,備考
Pteropus dasymallus,オガサワラオオコウモリ,CR,オオコウモリ科,小笠原諸島
Mogera imaizumii,アズミモグラ,NT,モグラ科,中部地方
```

#### データの前処理と統合

複数のCSVを統合してRAG用のJSON Lines形式に変換します。

**前処理スクリプト** (`scripts/prepare-redlist-data.py`):

```python
import pandas as pd
import json
import os
from pathlib import Path

# 入力・出力ディレクトリ
input_dir = Path('data/raw')
output_dir = Path('data/processed')
output_dir.mkdir(parents=True, exist_ok=True)

# カテゴリマッピング
category_names = {
    'redList2012_honyurui.csv': '哺乳類',
    'redList2012_tyorui.csv': '鳥類',
    'redList2012_hachurui.csv': '爬虫類',
    'redList2012_ryouseirui.csv': '両生類',
    'redList2012_tansuigyorui.csv': '汽水・淡水魚類',
    'redList2012_kontyurui_2.csv': '昆虫類',
    'redList2012_kairui_1.csv': '貝類',
    'redList2012_invertebrate_1.csv': 'その他無脊椎動物',
    'redList2012_ikansoku.csv': '維管束植物',
}

all_documents = []
doc_id = 1

for filename, category in category_names.items():
    file_path = input_dir / filename
    
    if not file_path.exists():
        print(f"⚠️ ファイルが見つかりません: {filename}")
        continue
    
    print(f"処理中: {category} ({filename})")
    
    try:
        # CP932(Windows-31J)で読み込み
        df = pd.read_csv(file_path, encoding='cp932')
        
        # 列名を確認（ファイルによって異なる場合がある）
        print(f"  列: {df.columns.tolist()}")
        
        # 各行をドキュメント化
        for idx, row in df.iterrows():
            # CSVの列構造に応じて調整
            scientific_name = row.iloc[0] if len(row) > 0 else ""
            japanese_name = row.iloc[1] if len(row) > 1 else ""
            rank = row.iloc[2] if len(row) > 2 else ""
            family = row.iloc[3] if len(row) > 3 else ""
            
            # タイトルとコンテンツを構築
            title = f"{japanese_name} ({scientific_name})"
            content = f"""
分類: {category}
和名: {japanese_name}
学名: {scientific_name}
絶滅危惧ランク: {rank}
科名: {family}

この種は環境省のレッドリスト（第4次）において{rank}に分類されています。
""".strip()
            
            # JSONドキュメント作成
            document = {
                'id': str(doc_id),
                'title': title,
                'content': content,
                'category': category,
                'rank': rank,
                'url': 'https://data.e-gov.go.jp/data/dataset/env_20140904_0456',
                'scientific_name': scientific_name,
                'japanese_name': japanese_name,
                'family': family
            }
            
            all_documents.append(document)
            doc_id += 1
    
    except Exception as e:
        print(f"  ✗ エラー: {e}")

print(f"\n処理完了: {len(all_documents)}件のドキュメント")

# JSON Lines形式で保存
output_file = output_dir / 'redlist-documents.jsonl'
with open(output_file, 'w', encoding='utf-8') as f:
    for doc in all_documents:
        f.write(json.dumps(doc, ensure_ascii=False) + '\n')

print(f"保存先: {output_file}")

# サマリー表示
print("\nカテゴリ別件数:")
category_counts = {}
for doc in all_documents:
    cat = doc['category']
    category_counts[cat] = category_counts.get(cat, 0) + 1

for cat, count in sorted(category_counts.items()):
    print(f"  {cat}: {count}件")
```

実行:

```powershell
python scripts\prepare-redlist-data.py
```

期待される出力:
```
処理中: 哺乳類 (redList2012_honyurui.csv)
  列: ['カテゴリー', '分類群', '和名', '学名']
処理中: 鳥類 (redList2012_tyorui.csv)
  列: ['カテゴリー', '分類群', '和名', '学名']
処理中: 爬虫類 (redList2012_hachurui.csv)
  列: ['カテゴリー', '分類群', '和名', '学名']
...
処理完了: 3597件のドキュメント
保存先: data\processed\redlist-documents.jsonl

カテゴリ別件数:
  その他無脊椎動物: 56件
  汽水・淡水魚類: 189件
  哺乳類: 72件
  両生類: 49件
  昆虫類: 357件
  維管束植物: 2083件
  貝類: 563件
  爬虫類: 40件
  鳥類: 188件
```

### 3. サンプルデータの生成(テスト用)

実際のレッドリストデータを使用する前に、動作確認用のサンプルデータを作成します。

> 📝 **Note**: このスクリプトはCSVファイルを読み込まず、コード内でサンプルデータを生成するため、エンコーディングの問題は発生しません。

**サンプルデータ生成スクリプト** (`scripts/generate-sample-data.py`):

```python
import json
import os
from pathlib import Path

# 出力ディレクトリ
output_dir = Path('data/processed')
output_dir.mkdir(parents=True, exist_ok=True)

# サンプルデータ(絶滅危惧種の例)
sample_documents = [
    {
        'id': '1',
        'title': 'イリオモテヤマネコ (Prionailurus bengalensis iriomotensis)',
        'content': '''分類: 哺乳類
和名: イリオモテヤマネコ
学名: Prionailurus bengalensis iriomotensis
絶滅危惧ランク: CR (絶滅危惧IA類)
科名: ネコ科

この種は環境省のレッドリスト(第4次)においてCRに分類されています。
沖縄県西表島のみに生息する日本固有の亜種です。森林の減少や交通事故により個体数が減少しています。
推定個体数は100頭程度とされています。''',
        'category': '哺乳類',
        'rank': 'CR',
        'url': 'https://data.e-gov.go.jp/data/dataset/env_20140904_0456',
        'scientific_name': 'Prionailurus bengalensis iriomotensis',
        'japanese_name': 'イリオモテヤマネコ',
        'family': 'ネコ科'
    },
    {
        'id': '2',
        'title': 'ライチョウ (Lagopus muta japonica)',
        'content': '''分類: 鳥類
和名: ライチョウ
学名: Lagopus muta japonica
絶滅危惧ランク: VU (絶滅危惧II類)
科名: キジ科

この種は環境省のレッドリスト(第4次)においてVUに分類されています。
日本アルプスの高山帯に生息する天然記念物です。気候変動による生息環境の変化が懸念されています。
推定個体数は約3,000羽とされています。''',
        'category': '鳥類',
        'rank': 'VU',
        'url': 'https://data.e-gov.go.jp/data/dataset/env_20140904_0456',
        'scientific_name': 'Lagopus muta japonica',
        'japanese_name': 'ライチョウ',
        'family': 'キジ科'
    },
    {
        'id': '3',
        'title': 'アユモドキ (Leptobotia curta)',
        'content': '''分類: 汽水・淡水魚類
和名: アユモドキ
学名: Leptobotia curta
絶滅危惧ランク: CR (絶滅危惧IA類)
科名: ドジョウ科

この種は環境省のレッドリスト(第4次)においてCRに分類されています。
岡山県と京都府のみに生息する希少な淡水魚です。河川改修や水質汚濁により生息地が減少しています。''',
        'category': '汽水・淡水魚類',
        'rank': 'CR',
        'url': 'https://data.e-gov.go.jp/data/dataset/env_20140904_0456',
        'scientific_name': 'Leptobotia curta',
        'japanese_name': 'アユモドキ',
        'family': 'ドジョウ科'
    },
    {
        'id': '4',
        'title': 'オオタカ (Accipiter gentilis fujiyamae)',
        'content': '''分類: 鳥類
和名: オオタカ
学名: Accipiter gentilis fujiyamae
絶滅危惧ランク: NT (準絶滅危惧)
科名: タカ科

この種は環境省のレッドリスト(第4次)においてNTに分類されています。
森林に生息する猛禽類で、開発による生息地の減少が課題です。近年は個体数が回復傾向にあります。''',
        'category': '鳥類',
        'rank': 'NT',
        'url': 'https://data.e-gov.go.jp/data/dataset/env_20140904_0456',
        'scientific_name': 'Accipiter gentilis fujiyamae',
        'japanese_name': 'オオタカ',
        'family': 'タカ科'
    },
    {
        'id': '5',
        'title': 'コウノトリ (Ciconia boyciana)',
        'content': '''分類: 鳥類
和名: コウノトリ
学名: Ciconia boyciana
絶滅危惧ランク: CR (絶滅危惧IA類)
科名: コウノトリ科

この種は環境省のレッドリスト(第4次)においてCRに分類されています。
かつて日本全国に生息していましたが、1971年に野生絶滅しました。現在は人工繁殖と放鳥により野生復帰が進められています。
兵庫県豊岡市を中心に約300羽が野外で生息しています。''',
        'category': '鳥類',
        'rank': 'CR',
        'url': 'https://data.e-gov.go.jp/data/dataset/env_20140904_0456',
        'scientific_name': 'Ciconia boyciana',
        'japanese_name': 'コウノトリ',
        'family': 'コウノトリ科'
    }
]

# JSON Lines形式で保存
output_file = output_dir / 'sample-documents.jsonl'
with open(output_file, 'w', encoding='utf-8') as f:
    for doc in sample_documents:
        f.write(json.dumps(doc, ensure_ascii=False) + '\n')

print(f"サンプルデータを生成しました: {output_file}")
print(f"ドキュメント数: {len(sample_documents)}")
```

実行:

```powershell
python scripts\generate-sample-data.py
```

これで以下のファイルが生成されます:
- `data/processed/sample-documents.jsonl` - テスト用サンプルデータ(5件の絶滅危惧種)

### 4. Azure Blob Storageへのアップロード

#### Blob Storageの準備

```powershell
# 環境変数を設定
$RESOURCE_GROUP = "rg-internal-rag-dev"
$STORAGE_ACCOUNT = "<your-storage-account-name>"
$CONTAINER_NAME = "rag-documents"

# コンテナを作成(まだ存在しない場合)
az storage container create `
    --account-name $STORAGE_ACCOUNT `
    --name $CONTAINER_NAME `
    --auth-mode login

# 作成確認
az storage container show `
    --account-name $STORAGE_ACCOUNT `
    --name $CONTAINER_NAME `
    --auth-mode login
```

#### データファイルのアップロード

> 💡 **推奨**: 最初は**テスト用サンプルデータ(5件)**から始めることをお勧めします。動作確認後、必要に応じて実データ(3597件)に切り替えます。

**オプション1: テスト用サンプルデータをアップロード(推奨)**

```powershell
# テスト用サンプルデータ(5件)をアップロード
az storage blob upload `
    --account-name $STORAGE_ACCOUNT `
    --container-name $CONTAINER_NAME `
    --name "sample-documents.jsonl" `
    --file "data/processed/sample-documents.jsonl" `
    --auth-mode login `
    --overwrite
```

**オプション2: 実データをアップロード**

```powershell
# 実データ(全3597件)をアップロード
az storage blob upload `
    --account-name $STORAGE_ACCOUNT `
    --container-name $CONTAINER_NAME `
    --name "redlist-documents.jsonl" `
    --file "data/processed/redlist-documents.jsonl" `
    --auth-mode login `
    --overwrite
```

**オプション3: 両方アップロード(並行テスト用)**

```powershell
# 両方のファイルをアップロード
az storage blob upload `
    --account-name $STORAGE_ACCOUNT `
    --container-name $CONTAINER_NAME `
    --name "sample-documents.jsonl" `
    --file "data/processed/sample-documents.jsonl" `
    --auth-mode login `
    --overwrite

az storage blob upload `
    --account-name $STORAGE_ACCOUNT `
    --container-name $CONTAINER_NAME `
    --name "redlist-documents.jsonl" `
    --file "data/processed/redlist-documents.jsonl" `
    --auth-mode login `
    --overwrite
```

**アップロード確認:**

```powershell
az storage blob list `
    --account-name $STORAGE_ACCOUNT `
    --container-name $CONTAINER_NAME `
    --auth-mode login `
    --output table
```

#### 複数ファイルのアップロード

```powershell
# dataディレクトリ内のすべてのJSONLファイルをアップロード
Get-ChildItem -Path "data/processed" -Filter "*.jsonl" | ForEach-Object {
    $fileName = $_.Name
    Write-Host "Uploading $fileName..."
    
    az storage blob upload `
        --account-name $STORAGE_ACCOUNT `
        --container-name $CONTAINER_NAME `
        --name $fileName `
        --file $_.FullName `
        --auth-mode login `
        --overwrite
}

Write-Host "アップロード完了"
```

### 4. データの検証

アップロードされたデータを確認します。

```powershell
# Blobの一覧を表示
az storage blob list `
    --account-name $STORAGE_ACCOUNT `
    --container-name $CONTAINER_NAME `
    --auth-mode login `
    --query "[].{Name:name, Size:properties.contentLength, LastModified:properties.lastModified}" `
    --output table

# 特定のBlobをダウンロードして確認(実データの場合)
az storage blob download `
    --account-name $STORAGE_ACCOUNT `
    --container-name $CONTAINER_NAME `
    --name "redlist-documents.jsonl" `
    --file "verify-download.jsonl" `
    --auth-mode login

# ダウンロードしたファイルを確認(UTF-8エンコーディング)
Get-Content verify-download.jsonl -Encoding UTF8 | Select-Object -First 5
```

期待される出力:
```json
{"id": "1", "title": "オキナワオオコウモリ (絶滅（EX）)", "content": "分類: 哺乳類\n和名: オキナワオオコウモリ\n学名: Pteropus loochoensis\n絶滅危惧ランク: 絶滅（EX）\n科名: 哺乳類\n\nこの種は環境省のレッドリスト（第4次）において絶滅（EX）に分類されています。", "category": "哺乳類", "rank": "絶滅（EX）", "url": "https://data.e-gov.go.jp/data/dataset/env_20140904_0456", "scientific_name": "Pteropus loochoensis", "japanese_name": "オキナワオオコウモリ", "family": "哺乳類"}
```

> 📝 **Note**: JSONLファイルはUTF-8で保存されているため、`-Encoding UTF8`を指定します。CSVファイル(CP932)とは異なります。

### 5. データスキーマの定義

AI Searchでインデックスを作成するために、レッドリストデータに適したスキーマを定義します。

#### スキーマファイルの作成

以下のコマンドでディレクトリとファイルを作成します:

```powershell
# スキーマ保存ディレクトリを作成
New-Item -ItemType Directory -Force -Path "data\schema" | Out-Null

# スキーマファイルを作成(VS Codeで開く)
New-Item -ItemType File -Path "data\schema\index-schema.json" -Force
code data\schema\index-schema.json
```

作成した `data/schema/index-schema.json` に以下の内容を貼り付けて保存します:

**ファイル内容** (`data/schema/index-schema.json`):

```json
{
  "name": "redlist-index",
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "key": true,
      "searchable": false
    },
    {
      "name": "title",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "sortable": true,
      "analyzer": "ja.lucene"
    },
    {
      "name": "content",
      "type": "Edm.String",
      "searchable": true,
      "analyzer": "ja.lucene"
    },
    {
      "name": "category",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "facetable": true
    },
    {
      "name": "rank",
      "type": "Edm.String",
      "searchable": false,
      "filterable": true,
      "facetable": true
    },
    {
      "name": "scientific_name",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "sortable": true
    },
    {
      "name": "japanese_name",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "sortable": true,
      "analyzer": "ja.lucene"
    },
    {
      "name": "family",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "facetable": true,
      "analyzer": "ja.lucene"
    },
    {
      "name": "url",
      "type": "Edm.String",
      "searchable": false
    },
    {
      "name": "content_vector",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "dimensions": 1536,
      "vectorSearchProfile": "vector-profile"
    }
  ],
  "vectorSearch": {
    "profiles": [
      {
        "name": "vector-profile",
        "algorithm": "hnsw-config"
      }
    ],
    "algorithms": [
      {
        "name": "hnsw-config",
        "kind": "hnsw",
        "hnswParameters": {
          "m": 4,
          "efConstruction": 400,
          "efSearch": 500,
          "metric": "cosine"
        }
      }
    ]
  },
  "semantic": {
    "configurations": [
      {
        "name": "semantic-config",
        "prioritizedFields": {
          "titleField": {
            "fieldName": "title"
          },
          "prioritizedContentFields": [
            {
              "fieldName": "content"
            }
          ],
          "prioritizedKeywordsFields": [
            {
              "fieldName": "category"
            },
            {
              "fieldName": "rank"
            }
          ]
        }
      }
    ]
  }
}
```

**スキーマの主なポイント**:

- **日本語アナライザー** (`ja.lucene`): `title`, `content`, `japanese_name`, `family`に適用し、日本語検索を最適化
- **フィルタリング・ファセット**: `category`(分類), `rank`(絶滅危惧ランク)でフィルタリング可能
- **ベクトル検索**: `content_vector`フィールドで1536次元のベクトル検索をサポート(text-embedding-ada-002モデル用)
- **セマンティック検索**: タイトル、コンテンツ、カテゴリ、ランクを優先フィールドとして設定

## 確認事項

以下をすべて確認してください:

- ✅ e-Govレッドリストデータをダウンロードした(9種類のCSV)
- ✅ データの前処理を実施した
- ✅ JSONL形式に変換した
- ✅ Blob Storageコンテナを作成した
- ✅ データファイルをアップロードした
- ✅ アップロードを確認した
- ✅ データスキーマを定義した

## トラブルシューティング

### CSVの文字コードが正しくない

**症状**: Pandasで読み込み時に文字化けする

**対処法**:
```python
# e-Govレッドリストデータの正しいエンコーディングはCP932です
df = pd.read_csv('data.csv', encoding='cp932')

# 他のCSVファイルの場合は以下も試してください
# df = pd.read_csv('data.csv', encoding='shift-jis')
# df = pd.read_csv('data.csv', encoding='utf-8')
```

### Blob Storageアップロードに失敗

**症状**: `az storage blob upload` がエラーになる

**対処法**:
```powershell
# ストレージアカウントへのアクセス権限を確認
az role assignment list `
    --assignee "<your-email>" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

# 「Storage Blob Data Contributor」ロールを付与
az role assignment create `
    --assignee "<your-email>" `
    --role "Storage Blob Data Contributor" `
    --scope "/subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"
```

### データサイズが大きすぎる

**症状**: ファイルサイズが大きくアップロードに時間がかかる

**対処法**:
- データを分割してアップロード
- 不要なカラムを削除
- 圧縮してアップロード

## 次のステップ

データ準備が完了したら、次は **[Step 3: AI Searchインデックス作成](step03-indexing.md)** に進みましょう。

Azure CLIを使用して、アップロードしたデータからAI Searchインデックスを作成します。
