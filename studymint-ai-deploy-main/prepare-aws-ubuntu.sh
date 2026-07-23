#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="studymint-ai"
INSTALL_DIR="${INSTALL_DIR:-/opt/${APP_NAME}}"
APP_PORT="${APP_PORT:-8080}"
FRONTEND_BIND="${FRONTEND_BIND:-0.0.0.0}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GIT_REF="${GIT_REF:-main}"
COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"
ENV_FILE="${INSTALL_DIR}/.env"

export DEBIAN_FRONTEND=noninteractive

log() {
  printf '\n[%s] %s\n' "${APP_NAME}" "$*"
}

die() {
  printf '\n[%s] ERROR: %s\n' "${APP_NAME}" "$*" >&2
  exit 1
}

need_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
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

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    return 0
  fi

  need_command sudo
  log "Re-running with sudo."
  exec sudo -E bash "$0" "$@"
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker and Docker Compose are already installed."
    return 0
  fi

  log "Installing Docker Engine and Docker Compose plugin."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc

  . /etc/os-release
  local codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
  [ -n "${codename}" ] || die "Could not determine Ubuntu codename."

  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
    "$(dpkg --print-architecture)" "${codename}" > /etc/apt/sources.list.d/docker.list

  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
}

install_base_packages() {
  log "Installing base packages."
  apt-get update
  apt-get install -y ca-certificates curl gnupg openssl
}

prepare_directory() {
  log "Preparing ${INSTALL_DIR}."
  mkdir -p "${INSTALL_DIR}"
  chmod 750 "${INSTALL_DIR}"
}

install_compose_file() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  if [ -n "${COMPOSE_SOURCE_URL:-}" ]; then
    log "Downloading compose file from COMPOSE_SOURCE_URL."
    curl -fsSL "${COMPOSE_SOURCE_URL}" -o "${COMPOSE_FILE}"
    return 0
  fi

  if [ -f "${script_dir}/docker-compose.yml" ]; then
    log "Copying compose file from ${script_dir}/docker-compose.yml."
    if [ "$(realpath "${script_dir}/docker-compose.yml")" = "$(realpath -m "${COMPOSE_FILE}")" ]; then
      log "Compose file is already in ${INSTALL_DIR}."
    else
      cp "${script_dir}/docker-compose.yml" "${COMPOSE_FILE}"
    fi
    return 0
  fi

  if [ -n "${GITHUB_REPO:-}" ]; then
    log "Downloading compose file from GitHub repo ${GITHUB_REPO} at ${GIT_REF}."
    curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/${GIT_REF}/deploy/docker-compose.yml" -o "${COMPOSE_FILE}"
    return 0
  fi

  die "No compose file found. Copy this script with deploy/docker-compose.yml, or set GITHUB_REPO=owner/repo."
}

random_hex() {
  openssl rand -hex "$1"
}

write_env_file() {
  if [ -f "${ENV_FILE}" ] && [ "${FORCE_ENV:-0}" != "1" ]; then
    log "Keeping existing ${ENV_FILE}. Set FORCE_ENV=1 to regenerate it."
    return 0
  fi

  need_command openssl

  local public_url="${PUBLIC_URL:-}"
  if [ -z "${public_url}" ]; then
    if [ -n "${DOMAIN:-}" ]; then
      public_url="https://${DOMAIN}"
    else
      local public_ip
      local imds_token
      imds_token="$(curl -fsS --max-time 3 -X PUT \
        -H "X-aws-ec2-metadata-token-ttl-seconds: 60" \
        http://169.254.169.254/latest/api/token 2>/dev/null || true)"
      if [ -n "${imds_token}" ]; then
        public_ip="$(curl -fsS --max-time 3 \
          -H "X-aws-ec2-metadata-token: ${imds_token}" \
          http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
      else
        public_ip="$(curl -fsS --max-time 3 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
      fi
      if [ -n "${public_ip}" ]; then
        public_url="http://${public_ip}:${APP_PORT}"
      else
        public_url="http://localhost:${APP_PORT}"
      fi
    fi
  fi

  local postgres_password="${POSTGRES_PASSWORD:-$(random_hex 24)}"
  local secret_key="${SECRET_KEY:-$(random_hex 32)}"
  local openai_api_key="${OPENAI_API_KEY:-replace-with-openai-api-key}"
  local ghcr_owner="${GHCR_OWNER:-replace-with-github-owner}"
  local frontend_public_url="${FRONTEND_PUBLIC_URL:-${public_url}}"
  local smtp_host="${SMTP_HOST:-smtp.hostinger.com}"
  local smtp_username="${SMTP_USERNAME:-info@marketing.ainexis.tech}"
  local smtp_from_email="${SMTP_FROM_EMAIL:-info@marketing.ainexis.tech}"
  if [ "${ghcr_owner}" != "replace-with-github-owner" ]; then
    ghcr_owner="${ghcr_owner,,}"
  fi

  log "Writing ${ENV_FILE}."
  umask 077
  cat > "${ENV_FILE}" <<EOF
# Image source
GHCR_OWNER=${ghcr_owner}
IMAGE_TAG=${IMAGE_TAG}

# Public port exposed by the frontend Nginx container
APP_PORT=${APP_PORT}
FRONTEND_BIND=${FRONTEND_BIND}

# Database
POSTGRES_USER=${POSTGRES_USER:-studymint}
POSTGRES_PASSWORD=${postgres_password}
POSTGRES_DB=${POSTGRES_DB:-studymint}

# Backend application settings
ENVIRONMENT=production
SECRET_KEY=${secret_key}
ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-1440}
BACKEND_CORS_ORIGINS=${BACKEND_CORS_ORIGINS:-${public_url}}
BACKEND_CORS_ORIGIN_REGEX=${BACKEND_CORS_ORIGIN_REGEX:-}
FRONTEND_PUBLIC_URL=${frontend_public_url}
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=${EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS:-24}
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=${PASSWORD_RESET_TOKEN_EXPIRE_MINUTES:-60}

# Email verification and password reset SMTP
SMTP_HOST=${smtp_host}
SMTP_PORT=${SMTP_PORT:-465}
SMTP_USERNAME=${smtp_username}
SMTP_PASSWORD=${SMTP_PASSWORD:-replace-with-hostinger-email-password}
SMTP_FROM_EMAIL=${smtp_from_email}
SMTP_FROM_NAME=${SMTP_FROM_NAME:-StudyMint AI}
SMTP_USE_SSL=${SMTP_USE_SSL:-true}
SMTP_USE_STARTTLS=${SMTP_USE_STARTTLS:-false}

# OpenAI
OPENAI_API_KEY=${openai_api_key}
OPENAI_MODEL=${OPENAI_MODEL:-gpt-5.5}
OPENAI_GUARDRAIL_MODEL=${OPENAI_GUARDRAIL_MODEL:-gpt-4.1-mini}
OPENAI_GUARDRAIL_MAX_OUTPUT_TOKENS=${OPENAI_GUARDRAIL_MAX_OUTPUT_TOKENS:-12000}
OPENAI_REASONING_EFFORT=${OPENAI_REASONING_EFFORT:-high}
OPENAI_TEXT_VERBOSITY=${OPENAI_TEXT_VERBOSITY:-medium}
OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL:-https://api.openai.com/v1}
OPENAI_TIMEOUT_SECONDS=${OPENAI_TIMEOUT_SECONDS:-90}
OPENAI_MAX_OUTPUT_TOKENS=${OPENAI_MAX_OUTPUT_TOKENS:-24000}

# Exports
PDF_EXPORT_BASE_URL=/exports
PDF_EXPORT_DIR=/app/exports
EOF
  chmod 600 "${ENV_FILE}"
}

docker_login_if_requested() {
  if [ -z "${GHCR_TOKEN:-}" ]; then
    return 0
  fi

  [ -n "${GHCR_USERNAME:-}" ] || die "Set GHCR_USERNAME when GHCR_TOKEN is set."
  log "Logging in to ghcr.io as ${GHCR_USERNAME}."
  printf '%s' "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USERNAME}" --password-stdin
}

configure_firewall() {
  if ! command -v ufw >/dev/null 2>&1; then
    log "ufw is not installed; skipping host firewall changes."
    return 0
  fi

  if [ "${CONFIGURE_UFW:-0}" != "1" ]; then
    log "Skipping ufw configuration because CONFIGURE_UFW is not 1."
    return 0
  fi

  log "Allowing SSH in ufw."
  ufw allow OpenSSH >/dev/null || true
  if [ "${USE_HOST_NGINX:-0}" = "1" ] || [ -n "${DOMAIN:-}" ] || [ "${FRONTEND_BIND}" = "127.0.0.1" ]; then
    log "Allowing TCP 80 and 443 in ufw for host Nginx."
    ufw allow 80/tcp >/dev/null || true
    ufw allow 443/tcp >/dev/null || true
  else
    log "Allowing TCP ${APP_PORT} in ufw."
    ufw allow "${APP_PORT}/tcp" >/dev/null || true
  fi
  ufw --force enable >/dev/null || true
}

env_has_placeholder() {
  grep -Eq '^(GHCR_OWNER|OPENAI_API_KEY|SMTP_PASSWORD)=replace-with-' "${ENV_FILE}"
}

start_stack() {
  if env_has_placeholder; then
    log "Deployment files are ready, but ${ENV_FILE} still has placeholders."
    printf 'Edit these values before starting:\n'
    grep -En '^(GHCR_OWNER|OPENAI_API_KEY|SMTP_PASSWORD)=' "${ENV_FILE}" || true
    printf '\nThen run:\n  cd %s\n  docker compose pull\n  docker compose up -d\n  docker compose ps\n' "${INSTALL_DIR}"
    return 0
  fi

  log "Pulling images and starting Docker Compose stack."
  cd "${INSTALL_DIR}"
  docker compose pull
  docker compose up -d
  docker compose ps

  if [ "${USE_HOST_NGINX:-0}" = "1" ] || [ -n "${DOMAIN:-}" ] || [ "${FRONTEND_BIND}" = "127.0.0.1" ]; then
    printf '\nStudyMint AI is listening behind Docker at %s:%s.\n' "${FRONTEND_BIND}" "${APP_PORT}"
    printf 'Run setup-nginx-https.sh, and make sure your AWS security group allows inbound TCP 80 and 443.\n'
  else
    printf '\nStudyMint AI should be available on port %s after the health checks pass.\n' "${APP_PORT}"
    printf 'Make sure your AWS security group allows inbound TCP %s from the clients that need access.\n' "${APP_PORT}"
  fi
}

main() {
  as_root "$@"
  require_ubuntu
  install_base_packages
  install_docker
  prepare_directory
  install_compose_file
  write_env_file
  docker_login_if_requested
  configure_firewall
  start_stack
}

main "$@"
