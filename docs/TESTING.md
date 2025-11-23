# Testing Guide

SecDashプロジェクトのテスト実行ガイド

## 目次
- [テスト環境のセットアップ](#テスト環境のセットアップ)
- [バックエンドテスト](#バックエンドテスト)
- [フロントエンドテスト](#フロントエンドテスト)
- [統合テスト](#統合テスト)
- [CI/CDパイプライン](#cicdパイプライン)

---

## テスト環境のセットアップ

### バックエンド

```bash
cd backend

# テスト用依存関係のインストール
pip install -r requirements-test.txt

# 環境変数の設定
export DATABASE_URL="sqlite:///./test.db"
export REDIS_URL="redis://localhost:6379/1"
export SECRET_KEY="test-secret-key"
export JWT_SECRET_KEY="test-jwt-secret"
```

### フロントエンド

```bash
cd frontend

# 依存関係のインストール
npm install

# テスト用環境変数
cp .env.example .env.test.local
```

---

## バックエンドテスト

### 全テストの実行

```bash
cd backend
pytest
```

### カバレッジ付きテスト

```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

カバレッジレポートは `htmlcov/index.html` で確認できます。

### 特定のテストファイル実行

```bash
# 認証テストのみ
pytest tests/test_auth.py

# リポジトリテストのみ
pytest tests/test_repositories.py

# スキャンテストのみ
pytest tests/test_scans.py
```

### マーカーによるフィルタリング

```bash
# APIテストのみ
pytest -m api

# ユニットテストのみ
pytest -m unit

# 統合テストのみ
pytest -m integration

# 遅いテストをスキップ
pytest -m "not slow"
```

### 詳細出力

```bash
# Verbose mode
pytest -v

# より詳細な出力
pytest -vv

# 標準出力を表示
pytest -s
```

### 並列実行

```bash
# pytest-xdistを使用
pip install pytest-xdist
pytest -n auto
```

---

## テストデータベース

テストでは自動的にインメモリSQLiteデータベースを使用します。
各テスト関数ごとに新しいデータベースインスタンスが作成され、テスト終了時にクリーンアップされます。

### PostgreSQLでのテスト（オプション）

```bash
# PostgreSQLコンテナ起動
docker run -d --name test-postgres \
  -e POSTGRES_USER=test_user \
  -e POSTGRES_PASSWORD=test_password \
  -e POSTGRES_DB=test_db \
  -p 5433:5432 \
  postgres:16-alpine

# テスト実行
export DATABASE_URL="postgresql://test_user:test_password@localhost:5433/test_db"
pytest

# コンテナ停止と削除
docker stop test-postgres && docker rm test-postgres
```

---

## モックとフィクスチャ

### 利用可能なフィクスチャ

`tests/conftest.py` で定義されている主要なフィクスチャ：

- `db_session`: テスト用データベースセッション
- `client`: FastAPIテストクライアント
- `test_user`: テストユーザー
- `test_admin`: 管理者ユーザー
- `auth_headers`: 認証ヘッダー
- `test_repository`: テストリポジトリ
- `test_scan`: テストスキャン
- `completed_scan`: 完了したスキャン
- `mock_ollama_service`: モック化されたOllamaサービス
- `mock_notification_service`: モック化された通知サービス
- `mock_github_service`: モック化されたGitHubサービス

### 外部サービスのモック

Ollamaや通知サービスなどの外部サービスは自動的にモック化されます：

```python
def test_with_ollama_mock(client, auth_headers, mock_ollama_service):
    # Ollamaサービスがモック化されているため、実際のOllamaサーバーは不要
    response = client.post("/api/ollama/query", ...)
    assert response.status_code == 200
```

---

## コード品質チェック

### Linting

```bash
cd backend

# Ruffでのリンティング
pip install ruff
ruff check app/

# 自動修正
ruff check --fix app/
```

### フォーマット

```bash
# Blackでのフォーマット
pip install black
black app/

# チェックのみ
black --check app/
```

### 型チェック

```bash
# mypyでの型チェック
pip install mypy
mypy app/
```

### インポート順序

```bash
# isortでのインポート整理
pip install isort
isort app/

# チェックのみ
isort --check-only app/
```

---

## セキュリティテスト

### Bandit（セキュリティリンター）

```bash
pip install bandit
bandit -r backend/app/ -f json -o bandit-report.json
```

### Semgrep

```bash
pip install semgrep
semgrep --config auto backend/app/
```

### Trivy（脆弱性スキャン）

```bash
# Dockerイメージスキャン
trivy image secdash-backend:latest

# ファイルシステムスキャン
trivy fs backend/
```

---

## CI/CDパイプライン

GitHub Actionsで自動的に以下が実行されます：

### Pull Request時
1. バックエンドテスト実行
2. コードカバレッジ測定
3. Linting/フォーマットチェック
4. セキュリティスキャン（Trivy, Semgrep, Bandit）
5. 依存関係脆弱性チェック（Snyk）

### Main/Developブランチへのマージ時
上記に加えて：
6. Dockerイメージビルド
7. Docker Hubへのプッシュ

### ワークフロー確認

```bash
# GitHub Actionsの実行状況はGitHubリポジトリで確認
https://github.com/<username>/<repo>/actions
```

---

## トラブルシューティング

### テスト失敗時の対処

#### データベース関連エラー

```bash
# テストデータベースをクリア
rm -f backend/test.db

# Alembicマイグレーションを確認
cd backend
alembic upgrade head
```

#### 依存関係エラー

```bash
# 依存関係を再インストール
cd backend
pip install --upgrade -r requirements-test.txt
```

#### モック関連エラー

フィクスチャが正しくインポートされているか確認：

```python
# test_*.py ファイルで
def test_something(mock_ollama_service):  # フィクスチャを引数に追加
    ...
```

---

## ベストプラクティス

### テスト作成時の推奨事項

1. **AAA パターンを使用**
   ```python
   def test_example():
       # Arrange: テストデータ準備
       user = create_test_user()

       # Act: テスト対象の実行
       result = login(user)

       # Assert: 結果検証
       assert result.success is True
   ```

2. **明確なテスト名**
   ```python
   # Good
   def test_login_with_invalid_password_returns_401():
       ...

   # Bad
   def test_login():
       ...
   ```

3. **独立したテスト**
   - テスト間で状態を共有しない
   - テスト実行順序に依存しない

4. **適切なモック使用**
   - 外部サービスはモック化
   - データベースはテスト用インスタンス使用

---

## 継続的改善

### カバレッジ目標

- 全体: 80%以上
- 重要な機能: 90%以上

### テスト追加の目安

新しい機能追加時は必ず以下を作成：
- ユニットテスト
- 統合テスト（API層）
- エッジケースのテスト

---

## 参考リソース

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://realpython.com/python-testing/)
