# StudyMint AI Deployment

This folder is for the production server. It pulls prebuilt images from GitHub Container Registry and runs the app with Docker Compose.

## Images

The GitHub Actions workflow publishes:

- `ghcr.io/<owner>/studymint-ai-backend:<tag>`
- `ghcr.io/<owner>/studymint-ai-frontend:<tag>`

The frontend image serves the React app with Nginx and proxies:

- `/api/v1/*` to the backend container
- `/exports/*` to the backend container

## Server Setup

## Automated GitHub Flow

After the backend, frontend, and deploy folders are split into their own repositories, the workflow is:

1. Push code to `dev`.
2. The repo CI workflow runs on `dev`.
3. If CI passes, `Promote Dev to Main` fast-forwards `main`.
4. Backend and frontend promotion explicitly dispatch the image publish workflow on `main`.
5. The image workflow pushes `latest` and `sha-*` images to GHCR.
6. The image workflow dispatches `StudyMint-AI/studymint-ai-deploy` / `Deploy Server`.
7. The deploy workflow SSHs to the Ubuntu server, syncs `docker-compose.yml`, runs `docker compose pull`, then `docker compose up -d`.

Deploy repo changes are also tested on `dev`, promoted to `main`, and then dispatch `Deploy Server` to sync the latest compose/scripts and restart the stack. Backend/frontend changes still build images first, then dispatch the same deploy workflow.

Required secrets in all three repositories:

- `CI_PROMOTION_TOKEN`: GitHub token that can push to the same repo and run workflows. A classic token needs `repo` and `workflow`.

Required secrets in both `studymint-ai-backend` and `studymint-ai-frontend`:

- `DEPLOY_REPO_TOKEN`: GitHub token allowed to run workflows in `StudyMint-AI/studymint-ai-deploy`. A classic token needs `repo` and `workflow`; a fine-grained token needs access to the deploy repo with Actions read/write.

The workflows use `CI_PROMOTION_TOKEN` instead of the built-in `GITHUB_TOKEN`, so they still work when organization-level GitHub Actions write permissions are disabled.

Required secrets in `studymint-ai-deploy`:

- `SERVER_HOST`: public IP or DNS name of the Ubuntu server.
- `SERVER_USER`: SSH user, for example `ubuntu`.
- `SERVER_SSH_KEY`: private SSH key for that user.
- `GHCR_USERNAME`: GitHub username that can read the GHCR packages.
- `GHCR_TOKEN`: GitHub token with `read:packages`; for private packages, also give it repo access to the backend/frontend repos.

Optional secrets in `studymint-ai-deploy`:

- `SERVER_PORT`: SSH port, defaults to `22`.
- `SERVER_DEPLOY_PATH`: server path, defaults to `/opt/studymint-ai`.

The server still needs the production `.env` file in `SERVER_DEPLOY_PATH`. Run the bootstrap script once to create it, then let GitHub Actions handle updates.

### Stuvia Agent and n8n

The backend exposes a Stuvia topic-to-document agent. It scrapes title/topic signals, generates review-ready StudyMint documents, and can hand a listing package to n8n for background workflow orchestration.

n8n is an internal operator tool. It coordinates post-generation review/publishing workflows and calls private publisher services; it is not the tenant UI and it is not needed for public topic scraping. Tenant users should connect Stuvia from the StudyMint Integration Center; they should not need the n8n URL, webhook URL, workflow editor, or credential names.

Scraping the public Stuvia source URL does not use Stuvia email/password. Stuvia credentials are only used later for authorized publishing. Selected topic titles are recorded per tenant so later agent runs skip previously used titles/topics and do not generate duplicate documents from the same topic.

The compose profile seeds this workflow into n8n automatically before n8n starts:

```text
deploy/workflows/stuvia-agent-review.n8n.json
```

Optional local/server n8n runtime:

```bash
docker compose --profile automation up -d n8n
```

The `n8n-seed` service runs first, imports the bundled workflow if it is missing, and then n8n starts with the workflow already available in the editor.

For Git Bash on Windows, use Unix-style paths:

```bash
cd ~/Documents/study-mint-ai/deploy
docker compose --profile automation up -d n8n
```

Set `N8N_STUVIA_WEBHOOK_URL` in the backend environment to the imported workflow webhook URL. Keep `N8N_STUVIA_WEBHOOK_TOKEN` empty unless your workflow expects a bearer token. These are internal deployment settings and are not shown in the tenant UI.

For auto-publish, tenants connect Stuvia inside StudyMint only. StudyMint stores the Stuvia password encrypted, sends n8n a private credential lookup URL, and keeps the password out of tenant-visible configuration and normal API responses.

1. Set a stable `SECRET_KEY`; changing it makes previously stored encrypted Stuvia passwords unreadable.
2. Set `N8N_STUVIA_WEBHOOK_TOKEN` to a private random token if the workflow or publisher needs credential lookup access.
3. Set `BACKEND_PUBLIC_URL` to an internal backend URL reachable from n8n or the publisher, for example `http://backend:8000` in the full compose stack.
4. Point `STUVIA_BROWSER_PUBLISHER_URL` at a private Playwright/browser publisher service. That service should fetch credentials from the `credential_lookup_url` with `Authorization: Bearer <N8N_STUVIA_WEBHOOK_TOKEN>`.

n8n encrypts its own workflow data using `N8N_ENCRYPTION_KEY`; set a stable random value before production use. The current workflow only routes auto-publish requests to the publisher endpoint. The browser publisher itself still has to be implemented and must not bypass CAPTCHA, 2FA, rate limits, or Stuvia terms.

### Accounts and Email Verification

Public signup creates regular `USER` accounts only. These users cannot see the Admin page, and admin APIs require a verified `SUPER_ADMIN` account.

Admin users are created from the backend container after the stack is running:

```bash
cd /opt/studymint-ai
sudo docker compose exec backend python -m app.cli.create_admin \
  --email admin@example.com \
  --full-name "StudyMint Admin" \
  --password "replace-with-a-strong-password"
```

Regular users must verify their email before signing in. For Hostinger email, set these values in `/opt/studymint-ai/.env`:

```bash
FRONTEND_PUBLIC_URL=https://studymint-ai.apphiah.com
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS=24
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=60
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USERNAME=info@marketing.ainexis.tech
SMTP_PASSWORD=replace-with-hostinger-email-password
SMTP_FROM_EMAIL=info@marketing.ainexis.tech
SMTP_FROM_NAME=StudyMint AI
SMTP_USE_SSL=true
SMTP_USE_STARTTLS=false
```

After changing the server `.env`, restart the backend:

```bash
cd /opt/studymint-ai
sudo docker compose up -d
```

### Bootstrap an AWS Ubuntu server

For HTTPS with host Nginx, first point your domain DNS `A` record to the Ubuntu server public IP. In the AWS security group, allow inbound TCP:

- `22` for SSH
- `80` for HTTP / Let's Encrypt validation
- `443` for HTTPS

Copy this `deploy/` folder to the server, then run:

```bash
cd deploy
sudo GHCR_OWNER='<github-user-or-org>' \
  OPENAI_API_KEY='<openai-api-key>' \
  SMTP_PASSWORD='<hostinger-email-password>' \
  DOMAIN='app.example.com' \
  FRONTEND_BIND='127.0.0.1' \
  USE_HOST_NGINX='1' \
  CONFIGURE_UFW='1' \
  bash ./prepare-aws-ubuntu.sh
```

Then install host Nginx and issue the HTTPS certificate:

```bash
sudo DOMAIN='app.example.com' \
  EMAIL='admin@example.com' \
  bash ./setup-nginx-https.sh
```

This leaves the Docker frontend bound to `127.0.0.1:8080`; public traffic enters through Nginx on ports `80` and `443`.

Optional variables:

- `IMAGE_TAG=latest` or a branch, release, or `sha-*` tag published by GitHub Actions.
- `APP_PORT=8080` to change the public frontend port.
- `FRONTEND_BIND=127.0.0.1` when using host Nginx, or `0.0.0.0` when exposing the container directly.
- `GHCR_USERNAME='<github-user>' GHCR_TOKEN='<token-with-read-packages>'` for private GHCR packages.
- `GITHUB_REPO='<owner/repo>'` if running the script without copying `docker-compose.yml`.
- `CONFIGURE_UFW=1` if you want the script to configure `ufw`; it allows `80` and `443` when `DOMAIN`, `USE_HOST_NGINX=1`, or `FRONTEND_BIND=127.0.0.1` is set.

If you do not have a domain yet, skip `setup-nginx-https.sh` until DNS is ready. HTTPS certificates need a real domain pointed at the server.

The script installs Docker Engine and the Compose plugin, creates `/opt/studymint-ai`, writes `/opt/studymint-ai/.env`, copies or downloads `docker-compose.yml`, pulls the GHCR images, runs migrations, and starts the stack.

### Manual setup

```bash
mkdir -p studymint-ai
cd studymint-ai
curl -O https://raw.githubusercontent.com/<owner>/<repo>/main/deploy/docker-compose.yml
curl -O https://raw.githubusercontent.com/<owner>/<repo>/main/deploy/.env.example
cp .env.example .env
```

Edit `.env`:

- Set `GHCR_OWNER` to your GitHub username or organization.
- Set `IMAGE_TAG` to `latest`, a branch tag, or a release tag.
- Set `POSTGRES_PASSWORD`, `SECRET_KEY`, and `OPENAI_API_KEY`.
- Set `BACKEND_CORS_ORIGINS` to the public URL of the frontend.
- Set `FRONTEND_PUBLIC_URL` to the public frontend URL used in verification links.
- Set `SMTP_PASSWORD` to the Hostinger mailbox password for `info@marketing.ainexis.tech`.
- Set `FRONTEND_BIND=127.0.0.1` when host Nginx proxies traffic to Docker.

If your GHCR packages are private, log in first:

```bash
echo "<github-token-with-read-packages>" | docker login ghcr.io -u <github-username> --password-stdin
```

Start the stack:

```bash
docker compose pull
docker compose up -d
docker compose ps
```

View logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

Upgrade to a newly published image:

```bash
docker compose pull
docker compose up -d
```

Run migrations manually if needed:

```bash
docker compose run --rm migrate
```

## Local Smoke Checks

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/api/v1/templates
```

With host Nginx and HTTPS, the public checks are:

```bash
curl https://app.example.com/healthz
curl https://app.example.com/api/v1/templates
```

The container remains available only on the server at `http://127.0.0.1:8080` when `FRONTEND_BIND=127.0.0.1`.

## Free Hosting Options

Best fit for this Docker Compose setup:

- **Oracle Cloud Always Free VM**: run Docker and this `deploy/docker-compose.yml` directly on an Always Free compute instance. This is the cleanest free option for a full-stack app with Postgres, backend, frontend, persistent exports, and GHCR image pulls.

Other options:

- **Fly.io**: good for container apps, but it is usage-billed and not the same as running this Docker Compose file directly.
- **Render/Railway/Koyeb-style platforms**: useful for simple web services, but usually require splitting frontend, backend, and database into separate managed services instead of using this compose stack as-is.

For this project, start with Oracle Cloud Always Free if you want one free server that pulls GHCR images and runs the whole stack.
