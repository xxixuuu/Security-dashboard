# 📦 SecDash セットアップガイド

このガイドでは、SecDashの完全なセットアップ手順を説明します。

---

## 📋 前提条件

### 必須
- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Git**
- **最小システム要件**:
  - CPU: 4コア以上推奨
  - RAM: 8GB以上推奨
  - ディスク: 20GB以上の空き容量

### オプション
- **Ollama** (ローカルLLM用)
- **GitHub/GitLab アカウント** (リポジトリスキャン用)

---

## 🚀 インストール手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/Security-dashboard.git
cd Security-dashboard
```

### 2. 環境変数の設定

```bash
# .env.example をコピー
cp .env.example .env

# .env ファイルを編集
nano .env  # または vim, code など
```

#### 重要な環境変数

```bash
# セキュリティ (必ず変更してください!)
SECRET_KEY=<強力なランダム文字列>
JWT_SECRET_KEY=<別の強力なランダム文字列>

# データベース
POSTGRES_PASSWORD=<セキュアなパスワード>

# Redis
REDIS_PASSWORD=<セキュアなパスワード>

# GitHub (リポジトリスキャン用)
GITHUB_TOKEN=ghp_your_token_here

# GitLab (オプション)
GITLAB_TOKEN=glpat_your_token_here
```

**セキュアなキーの生成方法:**

```bash
# Python を使用
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL を使用
openssl rand -base64 32
```

### 3. 自動セットアップ (推奨)

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

このスクリプトは以下を自動実行します:
- Ollamaモデルのダウンロード (llama3.2, codellama, deepseek-coder)
- 全サービスの起動
- データベースマイグレーション

### 4. 手動セットアップ (詳細制御が必要な場合)

#### 4.1 Ollamaモデルのセットアップ

```bash
# Ollamaコンテナを起動
docker-compose up -d ollama

# モデルをダウンロード
docker exec secdash_ollama ollama pull llama3.2
docker exec secdash_ollama ollama pull codellama
docker exec secdash_ollama ollama pull deepseek-coder
```

#### 4.2 全サービスの起動

```bash
# 開発環境
docker-compose up -d

# 本番環境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### 4.3 データベースマイグレーション

```bash
# 初期マイグレーション作成
docker-compose exec backend alembic revision --autogenerate -m "Initial migration"

# マイグレーション適用
docker-compose exec backend alembic upgrade head
```

#### 4.4 初期管理者ユーザー作成

```bash
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
import uuid

db = SessionLocal()
admin = User(
    id=uuid.uuid4(),
    email='admin@example.com',
    username='admin',
    hashed_password=get_password_hash('admin123'),  # 変更してください!
    role=UserRole.ADMIN,
    is_active=True,
    is_superuser=True
)
db.add(admin)
db.commit()
print('Admin user created!')
"
```

---

## ✅ 動作確認

### ヘルスチェック

```bash
# バックエンドAPI
curl http://localhost:8000/health

# フロントエンド
curl http://localhost:3000/api/health

# Redis
docker-compose exec redis redis-cli -a <REDIS_PASSWORD> ping

# PostgreSQL
docker-compose exec postgres pg_isready
```

### サービスアクセス

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs
- **Ollama**: http://localhost:11434

### ログ確認

```bash
# 全サービスのログ
docker-compose logs -f

# 特定サービスのログ
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery_worker
```

---

## 🔧 トラブルシューティング

### 問題: ポートが既に使用されている

```bash
# 使用中のポートを確認
sudo lsof -i :3000  # フロントエンド
sudo lsof -i :8000  # バックエンド
sudo lsof -i :5432  # PostgreSQL

# .env でポートを変更
FRONTEND_PORT=3001
BACKEND_PORT=8001
POSTGRES_PORT=5433
```

### 問題: データベース接続エラー

```bash
# PostgreSQL の状態確認
docker-compose ps postgres

# PostgreSQL のログ確認
docker-compose logs postgres

# データベースに直接接続してテスト
docker-compose exec postgres psql -U secdash_user -d secdash
```

### 問題: Ollama が利用できない

```bash
# Ollama の状態確認
docker-compose ps ollama

# モデルがダウンロードされているか確認
docker exec secdash_ollama ollama list

# Ollama を無効化する場合 (.env)
OLLAMA_ENABLED=false
```

### 問題: Celery ワーカーが起動しない

```bash
# Celery ワーカーのログ確認
docker-compose logs celery_worker

# Redis 接続確認
docker-compose exec celery_worker python -c "
import redis
r = redis.from_url('redis://:password@redis:6379/0')
print(r.ping())
"
```

---

## 🔄 アップデート

```bash
# 最新コードを取得
git pull origin main

# コンテナを再ビルド
docker-compose build

# サービスを再起動
docker-compose up -d

# データベースマイグレーション
docker-compose exec backend alembic upgrade head
```

---

## 🗑️ アンインストール

```bash
# サービスを停止して削除
docker-compose down

# ボリュームも削除 (データが失われます!)
docker-compose down -v

# プロジェクトディレクトリを削除
cd ..
rm -rf Security-dashboard
```

---

## 📊 パフォーマンスチューニング

### PostgreSQL

```yaml
# docker-compose.yml の postgres サービスに追加
environment:
  - POSTGRES_MAX_CONNECTIONS=100
  - POSTGRES_SHARED_BUFFERS=256MB
  - POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
```

### Redis

```yaml
# docker-compose.yml の redis サービスに追加
command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

### Celery Workers

```yaml
# docker-compose.yml の celery_worker サービス
command: celery -A app.workers.celery_app worker --concurrency=8 --max-tasks-per-child=1000
```

---

## 🌐 本番環境デプロイ

### SSL/TLS設定

1. **SSL証明書の取得**

```bash
# Let's Encrypt (Certbot)
sudo certbot certonly --standalone -d yourdomain.com
```

2. **Nginx設定の更新**

```bash
# docker/nginx/nginx.prod.conf を編集
# SSL証明書のパスを設定

volumes:
  - ./docker/nginx/ssl:/etc/nginx/ssl:ro
  - /etc/letsencrypt:/etc/letsencrypt:ro
```

3. **本番環境で起動**

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 環境変数の本番環境設定

```bash
# .env (本番環境)
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<超強力なランダム文字列>
POSTGRES_PASSWORD=<超強力なパスワード>
REDIS_PASSWORD=<超強力なパスワード>
```

---

## 📞 サポート

問題が解決しない場合:

1. [GitHub Issues](https://github.com/yourusername/Security-dashboard/issues)
2. [ドキュメント](https://github.com/yourusername/Security-dashboard/tree/main/docs)
3. Email: security-dashboard@example.com

---

**次へ**: [APIリファレンス](API.md) | [アーキテクチャ設計](ARCHITECTURE.md)
