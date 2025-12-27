
# mcps プロジェクト概要

このリポジトリ（`/mcps`）は、**1つのコンテナ（または同一実行環境）内で複数のMCP機能を提供**するための作業領域です。

目的は、IDE（主に Cursor）から複数のMCP機能を使えるようにしつつ、**機能ごとの独立性（障害分離）**と、各機能に最適な**接続方式（Transport）の選択自由度**を両立することです。

---

## 要件（重要）

- 複数のMCP機能を提供する（例: `markdownify` / `nornicdb` など）
- **各MCP機能は独立**し、1つの機能がダウンしても他に影響しない構成にする（**プロセス分離**）
- IDE（主に Cursor）からの利用を想定し、各MCP機能は最も適した接続方式を選ぶ
	- `stdio` / `SSE` / `Streamable HTTP`
- IDEからのHTTPアクセスは以下の規約で提供する
	- `http://localhost:PORT/<mcp機能名>`
	- `<mcp機能名>` は基本的にディレクトリ名（例: `/mcps/markdownify` → `/markdownify`）
- 言語は不問
	- 選択肢がある場合の標準は **Python 3.13**（ただし強制ではない）

---

## 推奨アーキテクチャ（障害分離のためのプロセス分離）

### 全体像

- **機能ごとにMCPサーバを別プロセスで起動**します（例: `markdownify` プロセス、`nornicdb` プロセス…）。
- IDEからのHTTPアクセスを統一するため、必要に応じて **HTTPゲートウェイ（リバースプロキシ）**を1つ置き、パスベースで各機能へルーティングします。

この構成により、特定の機能で例外・OOM・無限ループなどが起きてプロセスが落ちても、**他機能のプロセスには波及しません**。

### Transport とアクセス方法の考え方

- `SSE` / `Streamable HTTP`
	- ゲートウェイ配下に `/<mcp機能名>` として公開し、Cursorは `url` で接続します。
- `stdio`
	- Cursorの `command` で直接起動する使い方が自然です。
	- ただし「HTTPでの統一エンドポイントが必要」な場合は、stdioのMCPをHTTPにブリッジするラッパ（別プロセス）を置く方針とします。

---

## ディレクトリと責務

`/mcps/<mcp機能名>/` に、機能ごとの実装・依存関係・起動エントリポイントを配置します。

また、IDE からの HTTP アクセスを `http://localhost:PORT/<mcp機能名>` に統一するために、必要に応じて `gateway/`（パスベースのリバースプロキシ）を併設します。

例:

```
/mcps/
	gateway/              # HTTPゲートウェイ（パスベース・リバースプロキシ）
	markdownify/          # Excel/CSV/PDF → Markdown 変換のMCP機能
	context7/             # Context7（最新ドキュメント取得のMCP機能）
	nornicdb/             # NornicDB（DB + MCP）
	feature-a/            # 将来の機能
	feature-b/            # 将来の機能
	start-servers.sh      # 複数機能を（プロセス分離で）まとめて起動するためのスクリプト
```

---

## Cursor（IDE）側の接続イメージ

### HTTP（SSE / Streamable HTTP）の例

```
http://localhost:PORT/markdownify
http://localhost:PORT/context7
http://localhost:PORT/nornicdb/mcp
```

開発用の最小例（このリポジトリの現状）:

- `./start-servers.sh` を起動すると、
	- gateway: `http://localhost:7000`
	- markdownify: gateway 配下の `http://localhost:7000/markdownify`（upstream は `:7101`）
	- context7: gateway 配下の `http://localhost:7000/context7`（upstream は `:7103` / upstream の実体は `/mcp`）
	- nornicdb: gateway 配下の `http://localhost:7000/nornicdb/mcp`（upstream は `:7102` / base-path は `/nornicdb`）
	を立ち上げます。

ログ（開発用）:

- `/tmp/mcps-markdownify.log`
- `/tmp/mcps-context7.log`
- `/tmp/mcps-nornicdb.log`
- `/tmp/mcps-gateway.log`

Cursor設定例（概念）:

```json
{
	"mcpServers": {
		"markdownify": {
			"url": "http://localhost:PORT/markdownify"
		},
		"context7": {
			"url": "http://localhost:PORT/context7"
		},
		"nornicdb": {
			"url": "http://localhost:PORT/nornicdb/mcp"
		}
	}
}
```

### stdio の例（必要な場合）

```json
{
	"mcpServers": {
		"some-stdio-feature": {
			"command": "uv",
			"args": ["run", "some-stdio-feature"]
		}
	}
}
```

---

## 運用ポリシー（推奨）

- 1機能 = 1プロセス（可能なら 1ポート）
- 公開エンドポイントは `/<mcp機能名>` のスラッシュ配下で独立させる
- 依存関係は機能ディレクトリ内で完結させ、衝突を避ける（可能なら）

