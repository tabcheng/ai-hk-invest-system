#!/bin/sh
set -eu

escaped_base_url=$(printf '%s' "${MINIAPP_API_BASE_URL:-}" | sed 's/\\/\\\\/g; s/"/\\"/g')

cat > /srv/config.js <<EOC
window.MINIAPP_API_BASE_URL = "${escaped_base_url}";
EOC

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
