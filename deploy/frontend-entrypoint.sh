#!/bin/sh
set -eu

API_BASE="${PARKFLOW_API_BASE:-}"

cat > /usr/share/nginx/html/config.js <<EOF
window.PARKFLOW_API_BASE = "${API_BASE}";
EOF
