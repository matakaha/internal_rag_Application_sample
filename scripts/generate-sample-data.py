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
