#!/usr/bin/env bash
set -euo pipefail

GATEWAY_HOST="${GATEWAY_HOST:-0.0.0.0}"
GATEWAY_PORT="${GATEWAY_PORT:-7000}"

MARKDOWNIFY_HOST="${MARKDOWNIFY_HOST:-127.0.0.1}"
MARKDOWNIFY_PORT="${MARKDOWNIFY_PORT:-7101}"
MARKDOWNIFY_PATH="${MARKDOWNIFY_PATH:-/markdownify}"
MARKDOWNIFY_TRANSPORT="${MARKDOWNIFY_TRANSPORT:-streamable-http}"

NORNICDB_HOST="${NORNICDB_HOST:-127.0.0.1}"
NORNICDB_HTTP_PORT="${NORNICDB_HTTP_PORT:-7102}"
NORNICDB_BOLT_PORT="${NORNICDB_BOLT_PORT:-7688}"
NORNICDB_BASE_PATH="${NORNICDB_BASE_PATH:-/nornicdb}"
NORNICDB_DATA_DIR="${NORNICDB_DATA_DIR:-/mcps/nornicdb/data}"
NORNICDB_BIN="${NORNICDB_BIN:-/mcps/nornicdb/repo/nornicdb}"

pids=()

cleanup() {
  for pid in "${pids[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done

  # Wait for clean shutdown
  for pid in "${pids[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
}

trap cleanup EXIT INT TERM

echo "Starting markdownify on ${MARKDOWNIFY_HOST}:${MARKDOWNIFY_PORT}${MARKDOWNIFY_PATH} ..."
pushd /mcps/markdownify >/dev/null
uv run markdownify-gateway \
  --host "$MARKDOWNIFY_HOST" \
  --port "$MARKDOWNIFY_PORT" \
  --path "$MARKDOWNIFY_PATH" \
  --transport "$MARKDOWNIFY_TRANSPORT" \
  >/tmp/mcps-markdownify.log 2>&1 &
pids+=("$!")
popd >/dev/null

if [[ ! -x "$NORNICDB_BIN" ]]; then
  echo "ERROR: nornicdb binary not found or not executable: $NORNICDB_BIN" >&2
  echo "Build it first: cd /mcps/nornicdb/repo && go build -tags noui -o ./nornicdb ./cmd/nornicdb" >&2
  exit 1
fi

mkdir -p "$NORNICDB_DATA_DIR"

echo "Starting nornicdb on ${NORNICDB_HOST}:${NORNICDB_HTTP_PORT}${NORNICDB_BASE_PATH} ..."
"$NORNICDB_BIN" serve \
  --address "$NORNICDB_HOST" \
  --http-port "$NORNICDB_HTTP_PORT" \
  --bolt-port "$NORNICDB_BOLT_PORT" \
  --base-path "$NORNICDB_BASE_PATH" \
  --data-dir "$NORNICDB_DATA_DIR" \
  --headless \
  --no-auth \
  >/tmp/mcps-nornicdb.log 2>&1 &
pids+=("$!")

echo "Starting gateway on ${GATEWAY_HOST}:${GATEWAY_PORT} ..."
pushd /mcps/gateway >/dev/null
HOST="$GATEWAY_HOST" PORT="$GATEWAY_PORT" \
MCP_UPSTREAMS="markdownify=http://${MARKDOWNIFY_HOST}:${MARKDOWNIFY_PORT},nornicdb=http://${NORNICDB_HOST}:${NORNICDB_HTTP_PORT}" \
uv run mcps-gateway \
  --host "$GATEWAY_HOST" \
  --port "$GATEWAY_PORT" \
  >/tmp/mcps-gateway.log 2>&1 &
pids+=("$!")
popd >/dev/null

echo "Started. Logs: /tmp/mcps-markdownify.log , /tmp/mcps-nornicdb.log , /tmp/mcps-gateway.log"

# Wait forever (until a signal arrives)
wait
