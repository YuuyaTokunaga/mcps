#!/usr/bin/env bash
set -euo pipefail

GATEWAY_HOST="${GATEWAY_HOST:-0.0.0.0}"
GATEWAY_PORT="${GATEWAY_PORT:-7000}"

MARKDOWNIFY_HOST="${MARKDOWNIFY_HOST:-127.0.0.1}"
MARKDOWNIFY_PORT="${MARKDOWNIFY_PORT:-7101}"
MARKDOWNIFY_PATH="${MARKDOWNIFY_PATH:-/markdownify}"
MARKDOWNIFY_TRANSPORT="${MARKDOWNIFY_TRANSPORT:-streamable-http}"

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

echo "Starting gateway on ${GATEWAY_HOST}:${GATEWAY_PORT} ..."
pushd /mcps/gateway >/dev/null
HOST="$GATEWAY_HOST" PORT="$GATEWAY_PORT" \
MCP_UPSTREAMS="markdownify=http://${MARKDOWNIFY_HOST}:${MARKDOWNIFY_PORT}" \
uv run mcps-gateway \
  --host "$GATEWAY_HOST" \
  --port "$GATEWAY_PORT" \
  >/tmp/mcps-gateway.log 2>&1 &
pids+=("$!")
popd >/dev/null

echo "Started. Logs: /tmp/mcps-markdownify.log , /tmp/mcps-gateway.log"

# Wait forever (until a signal arrives)
wait
