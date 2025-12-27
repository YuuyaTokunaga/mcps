
# Markdownify セットアップ手順（別マシン向け）

このドキュメントは、Markdownify（Streamable HTTP / `/markdownify`）を**別のマシン**で動かすために必要なものと、環境構築〜セットアップ〜起動までをまとめたものです。

## 1. 前提（必要なもの）

### 必須

- OS: Linux / macOS / Windows（WSL含む）いずれでも可
- Python: **3.13 以上**（本プロジェクトは `requires-python = ">=3.13"`）
- uv: Python依存管理・実行に **uv** を使用
- Git: リポジトリ取得に使用

### あると便利

- curl: ヘルスチェック用

### Linuxでビルド依存が必要になる場合（目安）

基本的には多くの依存はホイールで入りますが、環境によっては `lxml` 等でビルドが必要になることがあります。
その場合は OS の管理者権限で以下のようなパッケージが必要になることがあります（Ubuntu例）。

```bash
sudo apt update
sudo apt install -y build-essential python3-dev libxml2-dev libxslt1-dev
```

※ `sudo` が必要なので、実行できない場合は管理者に依頼してください。

## 2. uv のインストール

uv は複数のインストール方法があります。ここでは一般的な方法を2つ載せます。

### 方法A: 公式インストーラ（推奨）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

インストール後に、`uv --version` で確認してください。

### 方法B: pipx を使う（pipxがある場合）

```bash
pipx install uv
```

## 3. リポジトリ取得

任意の作業ディレクトリでクローンします。

```bash
git clone <this-repo-url>
cd <this-repo>/markdownify
```

このディレクトリ（`markdownify/`）直下に `pyproject.toml` があるのを確認してください。

## 4. 依存関係のセットアップ（uv）

以下で仮想環境（`.venv/`）作成と依存導入を行います。

```bash
uv sync
```

ポイント:

- `uv run ...` を使うと、仮想環境を activate せずにコマンドを実行できます。
- ロックファイル運用をしている場合は `uv.lock` に従って再現性高く入ります。

## 5. 起動（Streamable HTTP）

例として、ポート `7000` / パス `/markdownify` で起動します。

```bash
uv run markdownify-gateway --port 7000 --path /markdownify --transport streamable-http
```

起動したら、別ターミナルでヘルスチェック:

```bash
curl http://localhost:7000/health
```

`{"status":"ok"}` が返れば起動確認OKです。

> 注意: `/markdownify` 本体は MCP クライアント前提です。
> `curl` で直接叩くと、Accept/Session ヘッダーが無く 400/406 になるのは正常です。

## 6. Cursor 側設定（参考）

Streamable HTTP の場合、Cursor 側はURLを指定します。

```json
{
	"mcpServers": {
		"markdownify": {
			"url": "http://localhost:7000/markdownify"
		}
	}
}
```

※ 実際のキー名や配置場所は Cursor の設定に従ってください。

## 7. テスト（pytest）

テストは以下で実行できます。

```bash
uv run python -m pytest -q
```

> 注意: 環境によっては `uv run pytest` が、仮想環境内 `pytest` スクリプトのシバン不整合で失敗する場合があります。
> その場合は上記の通り `python -m pytest` を使ってください。

## 8. Lint（Ruff）

```bash
uv run ruff check
```

自動修正:

```bash
uv run ruff check --fix
```

## 9. よく使うワンライナー

セットアップ + Lint + テスト:

```bash
uv sync && uv run ruff check && uv run python -m pytest -q
```
