#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="studymint-ai"
DOMAIN="${DOMAIN:-}"
APP_PORT="${APP_PORT:-8080}"
UPSTREAM_URL="${UPSTREAM_URL:-http://127.0.0.1:${APP_PORT}}"
EMAIL="${EMAIL:-}"
ENABLE_CERTBOT="${ENABLE_CERTBOT:-1}"
NGINX_SITE="/etc/nginx/sites-available/${APP_NAME}"
NGINX_SITE_LINK="/etc/nginx/sites-enabled/${APP_NAME}"

export DEBIAN_FRONTEND=noninteractive

log() {
  printf '\n[%s-nginx] %s\n' "${APP_NAME}" "$*"
}

die() {
  printf '\n[%s-nginx] ERROR: %s\n' "${APP_NAME}" "$*" >&2
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    return 0
  fi

  need_command sudo
  log "Re-running with sudo."
  exec sudo -E bash "$0" "$@"
}

require_ubuntu() {
  if [ ! -r /etc/os-release ]; then
    die "This script expects Ubuntu."
  fi

  . /etc/os-release
  if [ "${ID:-}" != "ubuntu" ]; then
    die "This script expects Ubuntu, found ${PRETTY_NAME:-unknown OS}."
  fi
}

install_packages() {
  log "Installing Nginx and Certbot packages."
  apt-get update
  apt-get install -y nginx certbot python3-certbot-nginx
  systemctl enable --now nginx
}

configure_firewall() {
  if ! command -v ufw >/dev/null 2>&1; then
    log "ufw is not installed; skipping host firewall changes."
    return 0
  fi

  log "Allowing SSH, HTTP, and HTTPS in ufw."
  ufw allow OpenSSH >/dev/null || true
  ufw allow 80/tcp >/dev/null || true
  ufw allow 443/tcp >/dev/null || true
  ufw --force enable >/dev/null || true
}

write_nginx_site() {
  [ -n "${DOMAIN}" ] || die "Set DOMAIN, for example DOMAIN=app.example.com."

  log "Writing Nginx site for ${DOMAIN} -> ${UPSTREAM_URL}."
  cat > "${NGINX_SITE}" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    client_max_body_size 50m;

    location / {
        proxy_pass ${UPSTREAM_URL};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_connect_timeout 30s;
        proxy_send_timeout 300s;
    }
}
EOF

  ln -sf "${NGINX_SITE}" "${NGINX_SITE_LINK}"
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl reload nginx
}

issue_certificate() {
  if [ "${ENABLE_CERTBOT}" != "1" ]; then
    log "Skipping Certbot because ENABLE_CERTBOT is not 1."
    return 0
  fi

  log "Requesting Let's Encrypt certificate for ${DOMAIN}."
  if [ -n "${EMAIL}" ]; then
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --email "${EMAIL}" --redirect
  else
    certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --register-unsafely-without-email --redirect
  fi

  systemctl reload nginx
}

main() {
  as_root "$@"
  require_ubuntu
  install_packages
  configure_firewall
  write_nginx_site
  issue_certificate

  printf '\nNginx is configured for https://%s and proxies to %s.\n' "${DOMAIN}" "${UPSTREAM_URL}"
  printf 'Make sure your AWS security group allows inbound TCP 80 and 443.\n'
}

main "$@"
