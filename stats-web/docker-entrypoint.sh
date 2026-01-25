#!/bin/sh
set -e

TEMPLATE="/usr/share/nginx/html/env.js.template"
TARGET="/usr/share/nginx/html/env.js"

if [ -f "$TEMPLATE" ]; then
  BACKEND_URL_VALUE="${BACKEND_URL:-}"
  sed "s|__BACKEND_URL__|$BACKEND_URL_VALUE|g" "$TEMPLATE" > "$TARGET"
fi

exec "$@"
