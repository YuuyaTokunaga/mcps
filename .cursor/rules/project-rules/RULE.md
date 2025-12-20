---
alwaysApply: true
---
## 環境構成
host: macbook pro(m3)
container: ubuntu25.04
docker-network: rancher-network

## 使用言語
python3.13.3

## コンテナユーザー
mcp-user(一般ユーザ)
管理者権限が必要なコマンドを実行する場合(インストールなど)はユーザに実行してほしいコマンド共に依頼してください。
パッケージ管理には apt を使用します。

## 作業ディレクトリ
/mcps/ # drwxr-xr-x   3 mcp-user mcp-user
├── feature-a/          # 機能A用のMCPサーバー
│   ├── server.py       # FastMCPまたはMCP SDK使用
│   └── requirements.txt
├── feature-b/          # 機能B用のMCPサーバー
│   ├── server.py
│   └── requirements.txt
└── start-servers.sh    # 全MCPサーバーを起動するスクリプト

## このコンテナの役割
このコンテナはIDEなどを通して、他のコンテナおよびホストから接続されAIエージェントが柔軟にタスクを実行できるようにするためのMCP用のコンテナです。
1つの機能ではなく複数の機能を提供します。

## 禁止事項
- ユーザから指示がない限りREADMEや説明資料の作成は禁止