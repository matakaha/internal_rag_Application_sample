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
        print(f"⚠️  ファイルが見つかりません: {filename}")
        continue
    
    print(f"処理中: {category} ({filename})")
    
    try:
        # CP932(Windows-31J)で読み込み
        df = pd.read_csv(file_path, encoding='cp932')
        
        # 列名を確認(ファイルによって異なる場合がある)
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

この種は環境省のレッドリスト(第4次)において{rank}に分類されています。
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
