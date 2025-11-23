# 🛡️ セキュリティポリシー

## 概要

SecDashはセキュリティツールであるため、プロジェクト自体のセキュリティは最優先事項です。

このドキュメントでは、実装されているセキュリティ対策と、脆弱性を発見した場合の報告方法について説明します。

---

## 🔐 実装されているセキュリティ対策

### 1. 認証とアクセス制御

#### JWT認証
- **アクセストークン**: 30分の有効期限
- **リフレッシュトークン**: 7日間の有効期限
- **HS256アルゴリズム**: セキュアなトークン署名

#### RBAC (Role-Based Access Control)
```
Admin    - 全機能へのアクセス
User     - スキャン実行、レポート閲覧
Viewer   - 読み取り専用
```

#### APIキー管理
- **生成**: `secrets.token_urlsafe(32)` による32バイトランダム文字列
- **保存**: ハッシュ化して保存
- **ローテーション**: 定期的な更新を推奨

### 2. データ保護

#### パスワード
- **ハッシュアルゴリズム**: bcrypt (cost factor: 12)
- **ソルト**: 自動生成
- **検証**: タイミング攻撃耐性

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

#### センシティブデータの暗号化
- **データベース接続**: TLS/SSL強制
- **APIトークン**: 環境変数で管理、データベースに暗号化保存
- **シークレット**: Vault統合オプション

### 3. OWASP Top 10 対策

#### A01: Broken Access Control
✅ **対策**:
- JWT + RBAC による厳格なアクセス制御
- エンドポイントレベルでの権限チェック
- オブジェクトレベル認可

#### A02: Cryptographic Failures
✅ **対策**:
- bcryptによるパスワードハッシュ化
- データベース接続のTLS暗号化
- 機密データのメモリからの安全な削除

#### A03: Injection
✅ **対策**:
- SQLAlchemy ORM (プリペアドステートメント)
- Pydantic/Zodによる入力バリデーション
- コマンド実行の制限とサニタイゼーション

```python
# Bad (脆弱)
query = f"SELECT * FROM users WHERE id = {user_id}"

# Good (安全)
user = db.query(User).filter(User.id == user_id).first()
```

#### A04: Insecure Design
✅ **対策**:
- セキュアデフォルト設定
- 最小権限の原則
- 脅威モデリングに基づく設計

#### A05: Security Misconfiguration
✅ **対策**:
- セキュリティヘッダー強制
- 本番環境でのデバッグモード無効化
- 定期的な依存関係更新

```python
# セキュリティヘッダー
headers = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": "default-src 'self'",
}
```

#### A06: Vulnerable and Outdated Components
✅ **対策**:
- 定期的な依存関係スキャン (Trivy, npm audit)
- 自動更新パイプライン
- SBOMエクスポート

#### A07: Identification and Authentication Failures
✅ **対策**:
- パスワード強度要件
- レートリミッティング
- セッション管理

```python
# レートリミッティング
@limiter.limit("5 per minute")
async def login():
    pass
```

#### A08: Software and Data Integrity Failures
✅ **対策**:
- Docker イメージの署名検証
- 依存関係の整合性チェック
- 監査ログ

#### A09: Security Logging and Monitoring Failures
✅ **対策**:
- 構造化ログ (JSON)
- 監査ログ (全アクセス記録)
- リアルタイムアラート

```python
logger.info({
    "event": "login_success",
    "user_id": user.id,
    "ip_address": request.client.host,
    "timestamp": datetime.utcnow(),
})
```

#### A10: Server-Side Request Forgery (SSRF)
✅ **対策**:
- URLホワイトリスト
- プライベートIPレンジのブロック
- リダイレクト制限

```python
# プライベートIPブロック
import ipaddress

def is_safe_url(url: str) -> bool:
    ip = ipaddress.ip_address(url)
    return not ip.is_private
```

### 4. 入力バリデーション

#### バックエンド (Pydantic)
```python
from pydantic import BaseModel, EmailStr, validator

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
```

#### フロントエンド (Zod)
```typescript
import { z } from 'zod'

const userSchema = z.object({
  email: z.string().email(),
  username: z.string().min(3),
  password: z.string().min(8),
})
```

### 5. レートリミッティング

#### Nginx レベル
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req zone=api_limit burst=10 nodelay;
```

#### アプリケーションレベル
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.get("/api/endpoint", dependencies=[Depends(RateLimiter(times=60, seconds=60))])
```

### 6. CSRF保護

- **SameSite Cookie**: Strict設定
- **CSRFトークン**: 状態変更操作で必須
- **ダブルサブミット**: Cookie + Header検証

### 7. XSS保護

- **コンテンツセキュリティポリシー**: 厳格なCSP
- **自動エスケープ**: テンプレートエンジン
- **DOMPurify**: ユーザー入力のサニタイゼーション

---

## 🚨 脆弱性報告

### セキュリティ脆弱性の報告方法

脆弱性を発見した場合は、**公開Issueを作成せず**、以下の手順に従ってください：

1. **Email送信**: security@secdash.example.com
2. **件名**: `[SECURITY] 脆弱性報告`
3. **内容**:
   - 脆弱性の詳細
   - 再現手順
   - 影響範囲
   - (オプション) 修正案

### 報告のガイドライン

#### 報告すべき内容
- 認証バイパス
- SQLインジェクション
- XSS
- CSRF
- センシティブデータの漏洩
- 権限昇格
- サービス拒否 (DoS)

#### 報告不要な内容
- 既知の脆弱性 (依存関係の古いバージョン等)
- セキュリティベストプラクティスからの逸脱 (軽微)
- 社会工学攻撃

### 対応プロセス

1. **受領確認**: 24時間以内
2. **初期評価**: 3営業日以内
3. **修正計画**: 7営業日以内
4. **パッチリリース**: 重要度に応じて
   - Critical: 24時間以内
   - High: 7日以内
   - Medium: 30日以内
   - Low: 次回リリース
5. **公開**: 修正後30日

---

## 🏆 セキュリティ報奨金 (今後実施予定)

現在、セキュリティ報奨金プログラムは実施していませんが、将来的に導入を検討しています。

---

## 🔒 セキュリティ監査

### 定期監査
- **コードレビュー**: 全PR
- **依存関係スキャン**: 毎週
- **ペネトレーションテスト**: 年1回

### 自動スキャン
```yaml
# .github/workflows/security.yml
- name: Semgrep
  run: semgrep --config=auto
- name: Trivy
  run: trivy fs .
- name: Gitleaks
  run: gitleaks detect
```

---

## 📚 セキュリティチェックリスト

### デプロイ前チェックリスト

- [ ] 全環境変数が適切に設定されている
- [ ] デフォルトパスワードが変更されている
- [ ] DEBUG=false (本番環境)
- [ ] SSL/TLS証明書が有効
- [ ] セキュリティヘッダーが設定されている
- [ ] レートリミッティングが有効
- [ ] ログ監視が設定されている
- [ ] バックアップが設定されている
- [ ] インシデント対応計画が策定されている

### 定期メンテナンスチェックリスト

- [ ] 依存関係の更新
- [ ] セキュリティパッチの適用
- [ ] ログレビュー
- [ ] アクセス権限レビュー
- [ ] バックアップテスト

---

## 📞 連絡先

**セキュリティチーム**: security@secdash.example.com

**PGP公開鍵**: [公開鍵リンク]

---

## 🔄 更新履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|----------|
| 2024-01-XX | 1.0.0 | 初版作成 |

---

**関連ドキュメント**:
- [セットアップガイド](SETUP.md)
- [アーキテクチャ設計](ARCHITECTURE.md)
- [APIリファレンス](API.md)
