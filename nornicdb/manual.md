
# nornicdb セットアップ手順（別マシン用）

この手順は、`/mcps` を別マシンに持っていった際に、NornicDB（nornicdb）を **Dockerなし**でビルドし、gateway 配下で MCP 接続できる状態にするためのメモです。

前提:

- 実行環境は Linux（このリポジトリの dev container 想定）
- gateway は `http://localhost:7000/<service>/...` で統一
- nornicdb の MCP エンドポイントは **`/mcp`**（例: `http://localhost:7000/nornicdb/mcp`）

---

## 1. 依存のインストール

管理者権限が必要です（必要ならこのコマンドはホスト側で実行してください）。

```bash
sudo apt update
sudo apt install -y git build-essential cmake pkg-config curl
```

Go が未インストールの場合は Go 1.21 以上を入れてください（NornicDBの要件）。

---

## 2. NornicDB ソースの用意

`/mcps/nornicdb/repo` が存在しない場合は clone します。

```bash
cd /mcps/nornicdb
git clone https://github.com/orneryd/nornicdb.git repo
```

すでに存在する場合は必要に応じて更新してください。

```bash
cd /mcps/nornicdb/repo
git pull
```

---

## 3. llama.cpp（ローカル埋め込み用）をビルド

```bash
cd /mcps/nornicdb/repo
./scripts/build-llama.sh
```

生成物は `repo/lib/llama/` 配下に作られます（Gitには入れない想定です）。

---

## 4. nornicdb を headless でビルド

UI（`ui/dist/*`）なしでビルドするため `-tags noui` を使います。

```bash
cd /mcps/nornicdb/repo
go build -tags noui -o ./nornicdb ./cmd/nornicdb
./nornicdb version
```

---

## 5. 起動（まとめて起動）

このリポジトリでは、`/mcps/start-servers.sh` が以下をまとめて起動します。

- markdownify（:7101）
- nornicdb（:7102 / base-path `/nornicdb`）
- gateway（:7000）

```bash
cd /mcps
./start-servers.sh
```

ログ:

- `/tmp/mcps-markdownify.log`
- `/tmp/mcps-nornicdb.log`
- `/tmp/mcps-gateway.log`

---

## 6. 疎通確認

### health

```bash
curl -fsS http://127.0.0.1:7000/health
curl -fsS http://127.0.0.1:7000/nornicdb/health
curl -fsS http://127.0.0.1:7000/markdownify/health
```

### MCP エンドポイント（重要）

Cursor の接続先は **`/nornicdb/mcp`** です。

- 正しい: `http://localhost:7000/nornicdb/mcp`
- 間違い: `http://localhost:7000/nornicdb`（これは Neo4j互換の “サーバ情報JSON” を返すだけで、MCPではありません）

MCP が応答するかの簡易確認（initialize をPOST）:

```bash
curl -sS -X POST http://127.0.0.1:7000/nornicdb/mcp \
	-H 'content-type: application/json' \
	-d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
```

---

## 7. Cursor 設定例

`~/.cursor/mcp.json` の例（概念）:

```json
{
	"mcpServers": {
		"nornicdb": {
			"url": "http://localhost:7000/nornicdb/mcp"
		}
	}
}
```

