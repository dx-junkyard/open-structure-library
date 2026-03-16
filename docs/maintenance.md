# OSL Pipeline — 管理者向けマニュアル

## 概要

`scripts/deploy_isom.py` は、`incoming/` ディレクトリに投稿された `.isom` ファイルを検証・正規化し、`library/by-domain/[domain]/corpus/` へ自動配置するスクリプトです。

---

## 手動実行

### 前提条件

- Python 3.8 以上
- 追加パッケージのインストール不要（標準ライブラリのみ使用）

### 実行方法

リポジトリルートで以下を実行します：

```bash
python scripts/deploy_isom.py
```

スクリプトは `incoming/` 内のすべての `.isom` ファイルを処理します。

### 終了コード

| コード | 意味 |
|--------|------|
| `0` | すべてのファイルが正常に配置された（または処理対象なし） |
| `1` | バリデーションエラーまたは重複エラーが発生した |

---

## バリデーション項目

### YAML ヘッダー

各 `.isom` ファイルは `---` で囲まれた YAML ヘッダーを持ち、以下の必須フィールドを含む必要があります：

| フィールド | 説明 | 例 |
|------------|------|----|
| `source_id` | 文献識別子（DOI 等） | `10.1234/example.2024` |
| `domain` | 学問領域 | `Cognitive Psychology` |
| `year` | 発行年 | `2024` |
| `title` | 構造タイトル | `Feedback Loop in Decision Making` |

### DSL ノード型

DSL 本体に含まれるノード型（`(名前:Type:型名)` 形式）は、以下の 4 種類に限定されます：

- `Agent`
- `Event`
- `Resource`
- `Intentional Moment`

---

## ファイル名の正規化ルール

入力ファイルは以下の形式にリネームされます：

```
YYYY-[Hash]-[ShortTitle].isom
```

- **YYYY**: `year` フィールドの値
- **Hash**: `source_id` の SHA-256 ハッシュの先頭 8 文字
- **ShortTitle**: `title` の先頭 3 単語をハイフン繋ぎにした slug

### 配置先

```
library/by-domain/[domain-slug]/corpus/
```

`domain` は小文字・ハイフン繋ぎに変換されます（例: `Cognitive Psychology` → `cognitive-psychology`）。

---

## 重複排除

移動先ディレクトリに同一の `source_id` を持つファイルが既に存在する場合、エラーとなり処理は中断されます。

---

## GitHub Actions による自動実行

`.github/workflows/deploy-isom.yml` により、`incoming/` 内のファイルを変更する Pull Request が作成されると、自動的にバリデーションが実行されます。

- バリデーション成功時: ファイルが `library/` へ配置され、コミットされます。
- バリデーション失敗時: CI が Failure となり、PR のマージがブロックされます。

---

## トラブルシューティング

### 「YAMLヘッダーが見つかりません」

ファイルが `---` で始まる YAML フロントマターを持っていることを確認してください。

### 「必須フィールド 'xxx' が欠落しています」

YAML ヘッダーに該当フィールドを追加してください。

### 「無効なノード型」

DSL 内のノード型が `Agent`, `Event`, `Resource`, `Intentional Moment` のいずれかであることを確認してください。

### 「重複エラー」

同じ `source_id` のファイルが既に `library/` に存在します。既存ファイルの更新が必要な場合は、手動で既存ファイルを削除してから再実行してください。
