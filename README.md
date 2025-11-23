# 🛡️ SecDash - セキュリティダッシュボード

**個人用セキュリティダッシュボード** - GitHub/GitLab上の全リポジトリを自動スキャンし、脆弱性を検出・可視化するセルフホスト型のエンタープライズグレードセキュリティプラットフォーム。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com/)

---

## ✨ 主な機能

### 🔍 包括的なセキュリティスキャン
- **SAST (静的解析)**: Semgrep, Bandit, ESLint
- **依存関係スキャン**: Trivy, OWASP Dependency-Check, npm audit, pip-audit
- **シークレット検出**: Gitleaks
- **コンテナスキャン**: Trivy

### 🤖 AI駆動の分析 (Ollama統合)
- 脆弱性の自動要約生成 (llama3.2)
- 修正コード提案 (codellama, deepseek-coder)
- 影響範囲分析
- 自然言語クエリ対応

### 📊 リアルタイムダッシュボード
- 脆弱性トレンド可視化 (Recharts)
- リポジトリ別ヒートマップ
- CWE Top 10 ランキング
- インタラクティブな詳細ビュー

### 🔔 多様な通知システム
- Slack/Discord Webhook
- Email (SMTP)
- 重要度別フィルタリング
- 週次サマリーレポート

### 🔐 エンタープライズセキュリティ
- JWT認証
- RBAC (Admin/User/Viewer)
- API Key管理
- 監査ログ
- CSRF/XSS保護
- Rate Limiting

---

## 🏗️ アーキテクチャ

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│  Next.js 15 │ ───► │  FastAPI     │ ───► │ PostgreSQL   │
│  (Frontend) │      │  (Backend)   │      │ + TimescaleDB│
└─────────────┘      └──────────────┘      └──────────────┘
                            │
                  ┌─────────┼─────────┐
                  ▼         ▼         ▼
             ┌────────┬─────────┬─────────┐
             │ Redis  │ Celery  │ Ollama  │
             │(Cache) │(Workers)│  (LLM)  │
             └────────┴─────────┴─────────┘
```

### 技術スタック

**フロントエンド**
- Next.js 15 (App Router) + TypeScript
- TailwindCSS + shadcn/ui
- React Query (状態管理)
- Recharts (可視化)
- Zod (バリデーション)

**バックエンド**
- FastAPI (Python 3.12+)
- SQLAlchemy 2.0 + Alembic
- Celery + Redis (非同期ジョブ)
- Ollama (ローカルLLM)

**データベース**
- PostgreSQL 16 + TimescaleDB
- Redis 7

**セキュリティツール**
- Semgrep, Trivy, Gitleaks, Bandit
- OWASP Dependency-Check
- npm audit, pip-audit

**インフラ**
- Docker + Docker Compose
- Nginx (リバースプロキシ)

---

## 🚀 クイックスタート

### 前提条件
- Docker & Docker Compose
- Git
- (オプション) Ollama

### インストール

1. **リポジトリをクローン**
```bash
git clone https://github.com/yourusername/Security-dashboard.git
cd Security-dashboard
```

2. **環境変数を設定**
```bash
cp .env.example .env
# .env ファイルを編集して、シークレットとAPIトークンを設定
```

3. **セットアップスクリプトを実行**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

4. **アクセス**
- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:8000
- API ドキュメント: http://localhost:8000/docs

---

## 📚 ドキュメント

- [セットアップガイド](docs/SETUP.md)
- [APIリファレンス](docs/API.md)
- [アーキテクチャ設計](docs/ARCHITECTURE.md)
- [セキュリティポリシー](docs/SECURITY.md)

---

## 🗂️ プロジェクト構造

```
secdash/
├── frontend/              # Next.js フロントエンド
│   ├── app/              # App Router
│   ├── components/       # Reactコンポーネント
│   ├── lib/              # ユーティリティ
│   └── hooks/            # カスタムフック
├── backend/              # FastAPI バックエンド
│   ├── app/
│   │   ├── api/         # APIルート
│   │   ├── core/        # 設定・セキュリティ
│   │   ├── models/      # SQLAlchemyモデル
│   │   ├── schemas/     # Pydanticスキーマ
│   │   ├── services/    # ビジネスロジック
│   │   └── workers/     # Celeryタスク
│   └── alembic/         # DBマイグレーション
├── scanners/            # スキャナー統合
├── docker/              # Dockerfiles & Nginx設定
├── scripts/             # セットアップスクリプト
└── docs/                # ドキュメント
```

---

## 🔧 開発

### 開発サーバー起動

```bash
# すべてのサービスを起動
docker-compose up

# バックエンドのみ
cd backend && uvicorn app.main:app --reload

# フロントエンドのみ
cd frontend && npm run dev
```

### データベースマイグレーション

```bash
# マイグレーション作成
docker-compose exec backend alembic revision --autogenerate -m "description"

# マイグレーション適用
docker-compose exec backend alembic upgrade head
```

### テスト実行

```bash
# バックエンド
docker-compose exec backend pytest

# フロントエンド
cd frontend && npm test
```

---

## 🌐 CI/CD

GitHub Actions を使用した自動CI/CDパイプライン:

- ✅ 自動テスト (Pytest + Jest)
- ✅ セキュリティスキャン (Semgrep, Trivy, Gitleaks)
- ✅ コード品質チェック
- ✅ Docker イメージビルド & プッシュ
- ✅ 自動デプロイ (オプション)

---

## 🛡️ セキュリティ

セキュリティは最優先事項です：

- ✅ OWASP Top 10 対策実装済み
- ✅ 全データベース接続暗号化
- ✅ シークレット管理 (環境変数 + Vault統合オプション)
- ✅ CSRF/XSS保護
- ✅ Rate Limiting
- ✅ セキュアヘッダー設定
- ✅ 入力バリデーション (Zod/Pydantic)

脆弱性を発見した場合は、[SECURITY.md](docs/SECURITY.md) を参照してください。

---

## 📊 機能ステータス

- [x] プロジェクト構造とDocker環境
- [x] PostgreSQL + Redis + Docker設定
- [x] FastAPIバックエンド基盤
- [x] データベーススキーマ設計
- [x] Next.jsフロントエンド基盤
- [ ] GitHub/GitLab API連携
- [ ] セキュリティスキャナー統合
- [ ] Celery非同期ジョブ
- [ ] Ollama統合
- [ ] ダッシュボード・可視化
- [ ] 通知システム
- [ ] WebSocket実装
- [ ] テストスイート
- [ ] CI/CD設定

---

## 🤝 コントリビューション

コントリビューションを歓迎します！詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

---

## 📝 ライセンス

このプロジェクトは [MIT License](LICENSE) の下でライセンスされています。

---

## 🙏 謝辞

このプロジェクトは以下のオープンソースプロジェクトを使用しています：

- [Next.js](https://nextjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Semgrep](https://semgrep.dev/)
- [Trivy](https://trivy.dev/)
- [Gitleaks](https://gitleaks.io/)
- [Ollama](https://ollama.ai/)
- その他多数

---

**作成者**: Your Name
**ウェブサイト**: https://example.com
**問い合わせ**: security-dashboard@example.com
