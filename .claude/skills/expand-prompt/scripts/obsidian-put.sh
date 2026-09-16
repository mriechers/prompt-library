#!/usr/bin/env bash
# obsidian-put.sh — write a note into the Obsidian vault via the Local REST API.
#
#   obsidian-put.sh --probe               is the vault reachable and authenticated?
#   obsidian-put.sh <vault-path> <file>   PUT <file> to <vault-path> (vault-relative)
#
# WHY THIS EXISTS: the vault used to be addressed by an absolute filesystem path
# baked into the skill. That path is true on exactly one machine — in a cloud
# session, on a second Mac, or after a vault move, the skill would either fail or
# (worse) create a stray directory and report success. The Local REST API is
# vault-relative, so no host path appears anywhere here.
#
# GRACEFUL SKIP IS THE POINT: --probe exits 1 with a one-line reason whenever the
# vault is not available. A caller is expected to treat that as "skip the vault
# step", not as an error to work around. Nothing here falls back to writing a
# filesystem path.
#
# Config (all optional; defaults match a stock Local REST API install):
#   OBSIDIAN_REST_URL   default https://127.0.0.1:27124  (plugin's HTTPS port)
#   OBSIDIAN_REST_URL_FALLBACK  default http://127.0.0.1:27123  (plugin's HTTP port)
#   OBSIDIAN_LOCAL_REST_API_KEY  the bearer token; otherwise resolved via the
#                       machine-ops secrets rail (get-secret.sh on PATH)
#   GET_SECRET          override: path to a get-secret.sh-compatible resolver
#                       (`<resolver> KEY` prints the value). Defaults to PATH lookup.
#
# Exit: 0 ok - 1 vault unavailable (skip) - 2 usage - 3 write failed.

set -uo pipefail

DEFAULT_URL="${OBSIDIAN_REST_URL:-https://127.0.0.1:27124}"
FALLBACK_URL="${OBSIDIAN_REST_URL_FALLBACK:-http://127.0.0.1:27123}"

# The plugin serves HTTPS with a self-signed cert, so -k is required and correct.
# --noproxy is NOT optional: a cloud session sets HTTPS_PROXY, and without this
# curl would route a loopback request — carrying the vault bearer token — through
# that proxy. Never send the token anywhere but the loopback interface.
CURL=(curl -sk --noproxy '*' --max-time 5)

resolve_key() {
  if [ -n "${OBSIDIAN_LOCAL_REST_API_KEY:-}" ]; then
    printf '%s' "$OBSIDIAN_LOCAL_REST_API_KEY"; return 0
  fi
  # The rail is reached by NAME (get-secret.sh on PATH) or by an explicit env
  # override — never by a path into another repo's checkout. A hardcoded path
  # to the machine-ops clone is true on one machine and silently dead on the
  # next; when the rail is absent the right outcome is a clean skip, not a guess.
  local gs
  gs="${GET_SECRET:-$(command -v get-secret.sh || true)}"
  [ -n "$gs" ] && [ -x "$gs" ] || return 1
  "$gs" OBSIDIAN_LOCAL_REST_API_KEY 2>/dev/null
}

# Percent-encode a vault path, keeping "/" as the separator. LC_ALL=C makes the
# loop walk BYTES, so a UTF-8 title (an em-dash in a note name, say) encodes to
# the right multi-byte sequence instead of a mangled single byte.
urlencode_path() {
  local s="$1" i c out=""
  local LC_ALL=C
  for (( i=0; i<${#s}; i++ )); do
    c="${s:i:1}"
    case "$c" in
      [a-zA-Z0-9.~_-]|/) out="$out$c" ;;
      *) out="$out$(printf '%%%02X' "'$c")" ;;
    esac
  done
  printf '%s' "$out"
}

# Try the HTTPS port, then the HTTP one. Prints the working base URL on success.
find_base_url() {
  local key="$1" url code
  for url in "$DEFAULT_URL" "$FALLBACK_URL"; do
    code="$("${CURL[@]}" -o /dev/null -w '%{http_code}' \
             -H "Authorization: Bearer $key" "$url/" 2>/dev/null || true)"
    case "$code" in
      200) printf '%s' "$url"; return 0 ;;
      401|403) echo "vault reachable at $url but the API key was rejected" >&2; return 1 ;;
    esac
  done
  return 1
}

MODE="${1:-}"
[ -n "$MODE" ] || { echo "usage: obsidian-put.sh --probe | <vault-path> <file>" >&2; exit 2; }

KEY="$(resolve_key || true)"
if [ -z "$KEY" ]; then
  echo "SKIP: no OBSIDIAN_LOCAL_REST_API_KEY (not in the environment, and the secrets rail could not supply it)" >&2
  exit 1
fi

BASE="$(find_base_url "$KEY")" || {
  echo "SKIP: Obsidian Local REST API not answering on $DEFAULT_URL or $FALLBACK_URL — Obsidian is probably not running on this host (expected in a cloud session)" >&2
  exit 1
}

if [ "$MODE" = "--probe" ]; then
  echo "OK: vault reachable at $BASE"
  exit 0
fi

VAULT_PATH="$MODE"
FILE="${2:-}"
[ -n "$FILE" ] && [ -r "$FILE" ] || { echo "usage: obsidian-put.sh <vault-path> <file>" >&2; exit 2; }

CODE="$("${CURL[@]}" -o /dev/null -w '%{http_code}' -X PUT \
  "$BASE/vault/$(urlencode_path "$VAULT_PATH")" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: text/markdown" \
  --data-binary "@$FILE" 2>/dev/null || true)"

case "$CODE" in
  200|201|204) echo "wrote: $VAULT_PATH"; exit 0 ;;
  *) echo "FAIL: PUT $VAULT_PATH returned HTTP ${CODE:-<none>}" >&2; exit 3 ;;
esac
