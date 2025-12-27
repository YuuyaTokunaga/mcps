
# mcps gateway

`/mcps/gateway` は、複数のMCP機能を **1つの公開ポート**（例: `:7000`）にまとめ、
`http://localhost:PORT/<mcp機能名>` で IDE（主にCursor）からアクセスできるようにするための **パスベース・リバースプロキシ**です。

重要:

- **各MCP機能は別プロセスで起動**します（プロセス分離）。
- gateway は **HTTPを中継するだけ**に徹し、機能実装（変換処理・DB操作など）を内包しません。
- ある upstream（MCP機能）が落ちても、gatewayはその経路だけ `502` を返し、他の経路は継続します。

---

## 役割と前提

### 何を解決するか

- IDEからのアクセスURLを `/<機能名>` で統一する
- 複数MCP機能を同居させても、プロセス分離で障害を波及させない
- 機能ごとに最適なTransport（Streamable HTTP / SSE / stdio）を選べるようにする

### gateway がやらないこと（方針）

- stdio MCPをgatewayプロセス内で直接起動・中継しない
	- stdio は将来も「**別プロセスのブリッジ**」としてHTTP化し、gatewayはHTTP upstreamとして扱います。
- 機能ごとの認証・認可・レート制限・キャッシュなどを勝手に追加しない

---

## ルーティング仕様（重要）

gateway は次のルールで転送します。

### 1) ヘルスチェック

- gateway自身: `GET /health` → `200 {"status":"ok"}`
- upstream確認: `GET /<service>/health`
	- `/<service>/health` は upstream の `GET /health` を叩きにいき、結果をそのまま返します。
	- 例: `GET /markdownify/health` → `http://127.0.0.1:7101/health`

### 2) 通常の転送

次のどちらの方式でも運用できます。機能追加時に「どっちで統一するか」を必ず決めてください。

#### A. prefix維持方式（デフォルト）

外部 `/<service>/...` を、内部でも `/<service>/...` のまま転送します。

- 外: `http://localhost:7000/markdownify/<rest>`
- 内: `http://127.0.0.1:7101/markdownify/<rest>`

この方式は、既存の `markdownify-gateway --path /markdownify` のように、upstreamがサブパス配下で公開する前提のときに安全です。

#### B. prefix剥がし方式（将来の選択肢）

外部 `/<service>/...` を、内部では `/...` にして転送します。

- 外: `http://localhost:7000/nornicdb/<rest>`
- 内: `http://127.0.0.1:7102/<rest>`

この方式は「upstreamは常に `/` で提供」に寄せたいときに便利です。
gateway側の設定 `MCP_STRIP_PREFIXES` にサービス名を列挙することで有効化できます。

---

## 設定（環境変数）

gateway は環境変数で upstream を定義します。

### 必須に近いもの

- `HOST`（デフォルト: `0.0.0.0`）
- `PORT`（デフォルト: `7000`）

### upstream 定義

- `MCP_UPSTREAMS`
	- 形式: `name=url[,name=url,...]`
	- デフォルト: `markdownify=http://127.0.0.1:7101`
	- 例:
		- `MCP_UPSTREAMS="markdownify=http://127.0.0.1:7101,nornicdb=http://127.0.0.1:7102"`

### prefix剥がしの指定（任意）

- `MCP_STRIP_PREFIXES`
	- 形式: `name[,name,...]`
	- 指定したサービスは「prefix剥がし方式（B）」になります。
	- 例:
		- `MCP_STRIP_PREFIXES="nornicdb"`

### upstream 側のパス prefix（任意）

upstream が「ルート `/` ではなく、`/mcp` のような固定サブパス」でMCPを提供している場合に使います。

- `MCP_UPSTREAM_PATH_PREFIXES`
	- 形式: `name=/path[,name=/path,...]`
	- 指定したサービスは、転送先パスの先頭に `/path` を前置します。
	- 例:
		- `MCP_UPSTREAM_PATH_PREFIXES="context7=/mcp"`

補足:

- `MCP_STRIP_PREFIXES` と `MCP_UPSTREAM_PATH_PREFIXES` は併用できます。
	- 例: Context7 は upstream 側が `/mcp` 固定なので、
		- 外: `http://localhost:7000/context7`
		- 内: `http://127.0.0.1:7103/mcp`
		のようにしたい場合、`MCP_STRIP_PREFIXES="context7"` と `MCP_UPSTREAM_PATH_PREFIXES="context7=/mcp"` を指定します。

---

## 起動方法（開発用）

ルートのスクリプトを使うのが基本です。

### まとめて起動（推奨）

`/mcps/start-servers.sh` は、

- 内部: markdownify（別プロセス）を `:7101` で起動
- 外部: gateway（別プロセス）を `:7000` で起動

までをまとめて行います。

例:

```bash
cd /mcps
./start-servers.sh
```

ログ:

- `/tmp/mcps-markdownify.log`
- `/tmp/mcps-gateway.log`

---

## MCP機能の追加ガイドライン

新しいMCP機能（例: `/mcps/nornicdb`）を追加するときは、以下の「チェックリスト」を順に満たしてください。

### 1) upstream を別プロセスとして起動できること

- 1機能=1プロセス（可能なら1ポート）
- その機能が落ちても、他機能が巻き添えで落ちない

### 2) upstream の公開パス方針を決める（A or B）

- **A（prefix維持）**: 内部も `/<service>` で提供する
	- gateway設定は不要（デフォルト）
	- upstream例: `--path /nornicdb`
- **B（prefix剥がし）**: 内部は `/` で提供する
	- gateway側 `MCP_STRIP_PREFIXES` に `service` を追加
	- upstream例: root `/` で提供

※最初は A（prefix維持）に寄せると事故りにくいです。

### 3) ポート割り当てを決める

- 既存機能と衝突しない内部ポートを割り当てる（例: `7102`, `7103`, ...）
- `start-servers.sh` に起動コマンドを追加する
- gateway の `MCP_UPSTREAMS` に `service=http://127.0.0.1:PORT` を追加する

### 4) ヘルスチェックを用意する

gateway の `/<service>/health` は upstream の `/health` を呼びます。
したがって、upstream側で `GET /health` を提供するのが推奨です。

もし upstream が `/health` を提供できない場合は、

- upstream側に `/health` を追加する（推奨）
- または gateway 側の実装を拡張して `serviceごとにhealthパスを変えられる設定` を追加する

のどちらかを選んでください。

---

## stdio MCP を使いたい場合（重要）

stdio MCP は「プロセスが標準入出力で喋る」ため、HTTPゲートウェイから直接中継するのが難しく、
また gateway プロセス内に組み込むと **障害分離（プロセス分離）** が崩れやすくなります。

このプロジェクトでは、stdio MCP を使う場合に次のどちらかを推奨します。

### 方式1: Cursor から `command` で直接起動（最も単純）

- gateway は使わない
- Cursor 設定で `command` / `args` を指定する
- ただし URL 統一（`http://localhost:PORT/<name>`）という要件がある場合は方式2へ

### 方式2: stdio→HTTP ブリッジを「別プロセス」で立てて gateway にぶら下げる（推奨）

- 新機能（stdio MCP）を起動する **ブリッジプロセス**を別途用意する
	- ブリッジは stdio でMCPと接続しつつ、外向けに Streamable HTTP / SSE 等を公開
- gateway から見ると、ブリッジはただのHTTP upstream（`MCP_UPSTREAMS` に登録）

メリット:

- stdio MCP を使いながらも URL 統一とプロセス分離を維持できる
- stdio 側が落ちてもブリッジプロセス単位で隔離される

---

## トラブルシュート

### 1) `/:7000` に繋がらない

- gateway のログ `/tmp/mcps-gateway.log` を確認
- ポート競合（すでに7000が使用中）を疑う

### 2) `/<service>/health` が 502 になる

- upstream プロセスが起動しているか（ポートが開いているか）
- `MCP_UPSTREAMS` のURLが正しいか
- upstream が `GET /health` を返しているか

※ upstream が `GET /health` を提供していない場合、`/<service>/health` は upstream のレスポンス（例: 404）をそのまま返します。

### 3) `/<service>/...` が 404 になる

- gateway 側で service 名が未登録（`MCP_UPSTREAMS`）
- prefix方式（A/B）が意図と違う（`MCP_STRIP_PREFIXES` の設定）

