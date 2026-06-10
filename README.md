# coding-interview

企業（Company）とカテゴリ（Category）の CRUD API を提供する Django REST Framework 製の API サーバーです。

## 技術スタック

- Python 3.11 / Django 4.2 / Django REST Framework 3.14
- PostgreSQL
- pipenv（依存管理）
- Docker Compose（ローカル実行環境）
- ruff（lint / format）・mypy（型チェック）
- GitHub Actions（CI: format / lint / 型 / migration 整合 / テスト）

## セットアップ（Docker Compose）

```bash
docker compose build
docker compose run --rm web python manage.py migrate
docker compose up -d
```

起動後、`http://localhost:8000/api/` で API ルートを確認できます。

### Docker を使わない場合

PostgreSQL（接続情報は `config/settings.py` の環境変数を参照）と libpq を用意した上で:

```bash
pipenv install --deploy --dev
pipenv run python manage.py migrate
pipenv run python manage.py runserver
```

## テスト

```bash
docker compose run --rm web python manage.py test api
```

## 品質チェック

```bash
docker compose run --rm web ruff format --check .
docker compose run --rm web ruff check .
docker compose run --rm web mypy .
```

## API 概要

認証は不要です。一覧 API はページネーションなしで全件を返します。

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/api/companies/` | 会社の一覧 |
| POST | `/api/companies/` | 会社の作成 |
| GET | `/api/companies/{id}/` | 会社の取得 |
| PUT / PATCH | `/api/companies/{id}/` | 会社の更新 |
| DELETE | `/api/companies/{id}/` | 会社の削除（配下のカテゴリも削除される） |
| GET | `/api/categories/` | カテゴリの一覧 |
| POST | `/api/categories/` | カテゴリの作成 |
| GET | `/api/categories/{id}/` | カテゴリの取得 |
| PUT / PATCH | `/api/categories/{id}/` | カテゴリの更新 |
| DELETE | `/api/categories/{id}/` | カテゴリの削除（子カテゴリの親は null になる） |

### Category のバリデーション仕様

- `company`（会社の UUID をリクエストボディで指定）・`name` は必須。`name` は最大 255 文字
- 同一会社内で同名のカテゴリは作成・変更できない（400）
- `parent_category` は省略可能（null 許容）。指定する場合は **同一会社** のカテゴリのみ
- 自分自身や子孫を親に指定する（循環参照になる）変更はできない（400）
- 所属会社（`company`）は作成後に変更できない（400）
- PUT / PATCH ともに、リクエストに含めなかった省略可能フィールド（`parent_category`）は既存の値が維持される。null にしたい場合は明示的に `null` を指定する

### リクエスト例

```bash
# 会社を作成
curl -s -X POST http://localhost:8000/api/companies/ \
  -H "Content-Type: application/json" \
  -d '{"name": "サンプル株式会社"}'

# カテゴリを作成（company には上記レスポンスの id を指定）
curl -s -X POST http://localhost:8000/api/categories/ \
  -H "Content-Type: application/json" \
  -d '{"company": "<company-id>", "name": "食品"}'
```
