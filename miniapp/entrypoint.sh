#!/bin/sh
set -eu

escaped_base_url=$(printf '%s' "${MINIAPP_API_BASE_URL:-}" | sed 's/\\/\\\\/g; s/"/\\"/g')
commit_sha=$(printf '%s' "${RAILWAY_GIT_COMMIT_SHA:-}" | cut -c1-7)
if [ -z "$commit_sha" ]; then
  commit_sha="unknown"
fi
ui_build_version_raw="${MINIAPP_UI_BUILD_VERSION:-$commit_sha}"
deployed_build_raw="${MINIAPP_DEPLOYED_BUILD:-$commit_sha}"
if [ -z "$ui_build_version_raw" ]; then ui_build_version_raw="unknown"; fi
if [ -z "$deployed_build_raw" ]; then deployed_build_raw="unknown"; fi
escaped_ui_build_version=$(printf '%s' "$ui_build_version_raw" | sed 's/\\/\\\\/g; s/"/\\"/g')
escaped_deployed_build=$(printf '%s' "$deployed_build_raw" | sed 's/\\/\\\\/g; s/"/\\"/g')

cat > /srv/config.js <<EOC
window.MINIAPP_API_BASE_URL = "${escaped_base_url}";
window.MINIAPP_UI_BUILD_VERSION = "${escaped_ui_build_version}";
window.MINIAPP_DEPLOYED_BUILD = "${escaped_deployed_build}";
EOC

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
