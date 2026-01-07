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
        Write-Host " " -ForegroundColor Green
    } catch {
        Write-Host "  エラー: $_" -ForegroundColor Red
    }
}

Write-Host "`nダウンロード完了!" -ForegroundColor Green
Write-Host "保存先: data\raw\" -ForegroundColor Yellow

# ダウンロードファイル一覧を表示
Get-ChildItem -Path "data\raw" -Filter "*.csv" | Format-Table Name, Length, LastWriteTime