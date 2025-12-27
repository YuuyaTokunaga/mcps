# Context7 セットアップ手順（別マシン向け）

このドキュメントは、Context7（`@upstash/context7-mcp`）を **別のマシン**で動かすために必要なものと、環境構築〜セットアップ〜起動までをまとめたものです。

このリポジトリの想定では、Context7 は **HTTP（SSE）** で起動し、gateway からは `http://localhost:7000/context7` として利用します。

---

## 1. 前提（必要なもの）

### 必須

- OS: Linux / macOS / Windows（WSL含む）いずれでも可
- Node.js: **18 以上**
- npm: 依存導入と実行に使用
- Git: リポジトリ取得に使用

### あると便利

- curl: 疎通確認用

---

## 2. リポジトリ取得

任意の作業ディレクトリでクローンします。

```bash
git clone <this-repo-url>
cd <this-repo>/context7
```

このディレクトリ（`context7/`）直下に `package.json` があることを確認してください。

---

## 3. 依存関係のセットアップ（npm）

```bash
npm install
```

ポイント:

- `node_modules/` が作成され、`./node_modules/.bin/context7-mcp` が利用可能になります。

---

## 4. 起動（HTTP / SSE）

例として、ポート `7103` で HTTP トランスポートとして起動します。

```bash
./node_modules/.bin/context7-mcp --transport http --port 7103
```

補足:

- Context7 の HTTP エンドポイントは **`/mcp`** です。
- Context7 は `GET /health` を提供しないため、`/health` を叩くと 404 になるのは正常です。

### API キー（任意）

必要な場合は README に従って `--api-key`（または `CONTEXT7_API_KEY` 環境変数）を指定してください。

---

## 5. 疎通確認（curl）

Context7 は MCP の通信として **SSE（`text/event-stream`）** を要求するため、単純な `curl http://.../mcp` は `406 Not Acceptable` になり得ます。

最低限の疎通確認（ヘッダだけ確認）:

```bash
curl -sS -o /dev/null -D - -H 'Accept: text/event-stream' http://127.0.0.1:7103/mcp
```

`HTTP/1.1 200 OK` と `content-type: text/event-stream` が返れば OK です。

---

## 6. gateway 配下（`/context7`）で使う場合

このリポジトリの gateway は「`/<service>` を upstream に転送」しますが、Context7 の upstream 実体が `/mcp` 固定のため、次の設定が必要です。

### 期待する外部URL

- 外: `http://localhost:7000/context7`
- 内: `http://127.0.0.1:7103/mcp`

### 必要な環境変数（gateway 側）

- `MCP_UPSTREAMS` に `context7=http://127.0.0.1:7103` を追加
- `MCP_STRIP_PREFIXES="context7"`
- `MCP_UPSTREAM_PATH_PREFIXES="context7=/mcp"`

`/mcps/start-servers.sh` を使う構成では、上記はすでに組み込まれています。

---

## 7. PowerShell での疎通確認（参考）

Windows PowerShell では `head` が無い・`curl` が別名の場合があるため、次のように `curl.exe` を使うのがおすすめです。

```powershell
curl.exe -sS -o NUL -D - -H "Accept: text/event-stream" http://127.0.0.1:7000/context7
```

