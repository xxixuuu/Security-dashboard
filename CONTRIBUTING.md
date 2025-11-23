# Contributing to SecDash

SecDashへの貢献ありがとうございます！このガイドは、プロジェクトに貢献する際の手順とガイドラインを説明します。

## 目次
- [開発環境のセットアップ](#開発環境のセットアップ)
- [コーディング規約](#コーディング規約)
- [Pull Requestプロセス](#pull-requestプロセス)
- [テスト](#テスト)
- [コミットメッセージ](#コミットメッセージ)
- [問題の報告](#問題の報告)

---

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/Security-dashboard.git
cd Security-dashboard
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集して必要な値を設定
```

### 3. Docker Composeで起動

```bash
docker-compose up -d
```

### 4. 開発用セットアップ

#### バックエンド

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-test.txt
pip install ruff black isort mypy
```

#### フロントエンド

```bash
cd frontend
npm install
```

---

## コーディング規約

### Python (Backend)

#### スタイルガイド
- [PEP 8](https://pep8.org/) に準拠
- Blackでフォーマット（line-length: 100）
- Ruffでリンティング
- isortでインポート整理

#### 実行コマンド

```bash
# フォーマット
black app/

# リンティング
ruff check app/ --fix

# インポート整理
isort app/

# 型チェック
mypy app/
```

#### 命名規則

- **クラス**: PascalCase (`UserService`, `ScanManager`)
- **関数・変数**: snake_case (`get_user`, `scan_id`)
- **定数**: UPPER_SNAKE_CASE (`MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **プライベート**: アンダースコア接頭辞 (`_internal_method`)

#### ドキュメンテーション

```python
def scan_repository(
    repo_id: str,
    scanners: List[str],
    branch: str = "main"
) -> Scan:
    """
    リポジトリをスキャンする

    Args:
        repo_id: リポジトリのUUID
        scanners: 使用するスキャナーのリスト
        branch: スキャン対象ブランチ（デフォルト: main）

    Returns:
        作成されたScanオブジェクト

    Raises:
        ValueError: repo_idが無効な場合
        ScanError: スキャン実行に失敗した場合
    """
    ...
```

### TypeScript (Frontend)

#### スタイルガイド
- TypeScript Strict Mode有効
- ESLint + Prettier使用
- React Hooks規則に準拠

#### 実行コマンド

```bash
# リンティング
npm run lint

# フォーマット
npm run format

# 型チェック
npm run type-check
```

#### 命名規則

- **コンポーネント**: PascalCase (`ScanList`, `VulnerabilityCard`)
- **hooks**: camelCaseで`use`接頭辞 (`useScan`, `useAuth`)
- **関数**: camelCase (`handleSubmit`, `fetchData`)
- **定数**: UPPER_SNAKE_CASE (`API_URL`, `MAX_ITEMS`)

---

## Pull Requestプロセス

### 1. ブランチ作成

```bash
# 機能追加
git checkout -b feature/add-new-scanner

# バグ修正
git checkout -b fix/scan-error-handling

# ドキュメント
git checkout -b docs/update-readme
```

### ブランチ命名規則

- `feature/`: 新機能
- `fix/`: バグ修正
- `docs/`: ドキュメント
- `refactor/`: リファクタリング
- `test/`: テスト追加
- `chore/`: その他の変更

### 2. 変更の実装

1. コードを書く
2. テストを追加/更新
3. ローカルでテスト実行
4. リンティング/フォーマット実行

### 3. コミット

```bash
git add .
git commit -m "feat: Add Gitleaks scanner integration"
```

### 4. プッシュ

```bash
git push origin feature/add-new-scanner
```

### 5. Pull Request作成

GitHub上でPull Requestを作成し、以下を含めてください：

- 変更の概要
- 関連するIssue番号（`Fixes #123`）
- テスト方法
- スクリーンショット（UI変更の場合）

#### Pull Requestテンプレート

```markdown
## 概要
この変更の目的と内容を簡潔に説明してください。

## 変更内容
- [ ] 機能A追加
- [ ] バグB修正
- [ ] テストC追加

## 関連Issue
Fixes #123

## テスト方法
1. ステップ1
2. ステップ2
3. 期待される結果

## チェックリスト
- [ ] テストを追加/更新した
- [ ] ドキュメントを更新した
- [ ] リンティングをパスした
- [ ] 全テストがパスした
```

---

## テスト

### 必須要件

- 新しいコードには必ずテストを追加
- 既存のテストを壊さない
- カバレッジを下げない

### テスト実行

```bash
# Backend
cd backend
pytest --cov=app

# Frontend
cd frontend
npm test
```

詳細は [TESTING.md](docs/TESTING.md) を参照してください。

---

## コミットメッセージ

[Conventional Commits](https://www.conventionalcommits.org/) 形式を使用：

### フォーマット

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメントのみの変更
- `style`: コードの意味に影響しない変更（空白、フォーマットなど）
- `refactor`: バグ修正も機能追加もしないコード変更
- `perf`: パフォーマンス改善
- `test`: テストの追加や修正
- `chore`: ビルドプロセスやツールの変更

### 例

```bash
# 機能追加
git commit -m "feat(scanner): Add Gitleaks scanner integration"

# バグ修正
git commit -m "fix(auth): Fix JWT token expiration handling"

# ドキュメント
git commit -m "docs(api): Update API documentation for scan endpoints"

# Breaking Change
git commit -m "feat(api)!: Change scan API response format

BREAKING CHANGE: Scan API now returns vulnerabilities in a nested object"
```

---

## コード レビュー

### レビュアー向け

- 建設的なフィードバックを提供
- コードの意図を理解する
- セキュリティとパフォーマンスに注目
- スタイルよりロジックを優先

### レビュー対象

- [ ] コードが要件を満たしているか
- [ ] テストが十分か
- [ ] セキュリティ上の問題はないか
- [ ] パフォーマンスへの影響は許容範囲か
- [ ] ドキュメントが更新されているか
- [ ] エラーハンドリングが適切か

---

## 問題の報告

### バグ報告

Issue作成時に以下を含めてください：

- 問題の明確な説明
- 再現手順
- 期待される動作
- 実際の動作
- 環境情報（OS、ブラウザ、バージョンなど）
- スクリーンショットやログ（可能な場合）

### 機能リクエスト

- 機能の説明
- ユースケース
- 提案する実装方法（任意）
- 代替案（任意）

---

## セキュリティ

セキュリティ上の脆弱性を発見した場合：

1. **公開Issueを作成しないでください**
2. security@example.com に非公開で報告してください
3. 詳細な説明と再現手順を含めてください

---

## ライセンス

貢献することで、あなたの貢献がプロジェクトと同じ[MIT License](LICENSE)の下でライセンスされることに同意したものとみなされます。

---

## コミュニティガイドライン

- 尊重と礼儀を持って接する
- 建設的なフィードバックを提供する
- 多様な視点を歓迎する
- コミュニティの成長に貢献する

---

## 質問がありますか？

- GitHub Discussions: コミュニティとの議論
- GitHub Issues: バグ報告や機能リクエスト
- Documentation: [docs/](docs/) フォルダ

---

ご協力ありがとうございます！ 🎉
