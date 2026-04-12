---
layout: default
title: Configuration
---

# Configuration

3DKenji configuration through environment variables.

## Environment Variables

### Database

**DATABASE_URL** (Required)
Connection string for PostgreSQL database.

```bash
DATABASE_URL=postgresql://username:password@localhost:5432/kenji
```

Format: `postgresql://[user[:password]@][host][:port][/dbname]`

Examples:
- Local: `postgresql://kenji:kenji@localhost:5432/kenji`
- Docker: `postgresql://kenji:kenji@postgres:5432/kenji`
- Production: `postgresql://user:secure-password@db.example.com:5432/kenji`

### Storage

**STORAGE_ROOT** (Optional, default: `/data/storage`)
Root directory for project filesystem data.

```bash
STORAGE_ROOT=/data/storage
```

Projects are stored under:

```text
STORAGE_ROOT/Projects/<owner_nickname>/<slug>
```

Example:

```text
/data/storage/Projects/alice-prints/test-project-2
```

Note: set `STORAGE_ROOT` to the root path only (for example `/workspace/data/storage`), not to a nested `.../Projects` path.

Ensure directory exists and is writable:
```bash
mkdir -p /data/storage
chmod 755 /data/storage
```

Legacy project paths (`Projects/<owner_id>/<slug>` or `Projects/<category>/<slug>`) are supported during migration, but new and updated projects are persisted to owner-nickname paths.

### Email (SMTP)

Invitation emails are delivered through SMTP configuration stored in admin settings (`/admin/settings`) and can be overridden for test/dev use with environment flags.

**APP_BASE_URL** (Optional, default: `http://localhost:8000`)
Base URL used to generate invitation claim links in emails.

```bash
APP_BASE_URL=http://localhost:8000
```

**SMTP_MOCK_DELIVERY** (Optional, default: `false`)
When true, email sending is simulated and no external SMTP server is contacted.

```bash
SMTP_MOCK_DELIVERY=true
```

SMTP host, port, credentials, sender identity, and TLS mode are managed in the admin SMTP settings UI and persisted in application settings.

**PLUGINS_ROOT** (Optional, default: `/data/plugins`)
Root directory for installation-specific plugins.

```bash
PLUGINS_ROOT=/data/plugins
```

Plugins are discovered only at application startup in v1. Each plugin lives in its own folder beneath `PLUGINS_ROOT` and must include a `plugin.yaml` manifest.

```text
PLUGINS_ROOT/
├── _system/
│   └── plugin-registry.yaml
└── core-themes/
  ├── plugin.yaml
  ├── settings.yaml
  └── assets/
    └── themes/
```

Notes:
- `plugin.yaml` is the read-only manifest/control file for the package.
- `settings.yaml` is the admin-editable plugin configuration.
- `PLUGINS_ROOT/_system/plugin-registry.yaml` stores installation enable/disable state.
- Cosmetic plugins contribute CSS assets.
- Viewer plugins may also contribute JS assets and backend entrypoint metadata, but public API routes remain core-owned.

Ensure the plugin root exists and is writable:

```bash
mkdir -p /data/plugins/_system
chmod -R 755 /data/plugins
```

### Project Structure and Frontmatter

Project creation seeds each project directory with:

- `ProjectInfo.md` – Project metadata (YAML frontmatter) and documentation
- `PrintHistory.md` – Print session log (YAML frontmatter) and session entries
- `models/`
- `cad_files/`
- `timelapse/`
- `images/`

Both markdown files use **YAML-like frontmatter** for structured metadata. This hybrid approach means:

- **Database is canonical for**: ownership, permissions, system lifecycle
- **Filesystem is canonical for**: project artifacts, user-editable documentation, and metadata in frontmatter
- **Frontmatter is structured**: automatically parsed and never rendered in HTML output
- **Body is freeform**: human-readable markdown that users can edit directly

For complete details on ProjectInfo.md and PrintHistory.md frontmatter schemas, see
[docs/project-storage-architecture.md](project-storage-architecture.md).

### Logging

**LOG_DIR** (Optional, default: `/data/logs`)
Directory for application log files.

```bash
LOG_DIR=/data/logs
```

**LOG_MAX_SIZE_MB** (Optional, default: `10`)
Maximum size of each log file in megabytes before rotation.

```bash
LOG_MAX_SIZE_MB=10
```

**LOG_BACKUP_COUNT** (Optional, default: `5`)
Number of backup log files to keep during rotation.

```bash
LOG_BACKUP_COUNT=5
```

### Security

**SECRET_KEY** (Required)
Secret key for JWT token signing. Generate with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set to a strong random value:
```bash
SECRET_KEY=your-secret-key-here-min-32-chars
```

**ALGORITHM** (Optional, default: `HS256`)
JWT signing algorithm (HS256 recommended for single server).

```bash
ALGORITHM=HS256
```

**TOKEN_EXPIRE_HOURS** (Optional, default: `24`)
JWT token expiration time in hours.

```bash
TOKEN_EXPIRE_HOURS=24
```

### Server

**HOST** (Optional, default: `0.0.0.0`)
Server listen address.

```bash
HOST=0.0.0.0
```

**PORT** (Optional, default: `8000`)
Server listen port.

```bash
PORT=8000
```

**LOG_LEVEL** (Optional, default: `INFO`)
Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL

```bash
LOG_LEVEL=INFO
```

## Development Configuration

### .env File (Development)

Create `.env` file in project root:

```bash
DATABASE_URL=postgresql://kenji:kenji@localhost:5432/kenji
STORAGE_ROOT=/workspace/data/storage
PLUGINS_ROOT=/workspace/working/plugins
LOG_DIR=/workspace/data/logs
LOG_LEVEL=DEBUG
SECRET_KEY=dev-secret-key-change-in-production
TOKEN_EXPIRE_HOURS=24
HOST=0.0.0.0
PORT=8000
```

Load with:
```bash
source .env
make dev
```

## Docker Configuration

### docker-compose.yml

Environment variables in `docker-compose.yml`:

```yaml
services:
  api:
    environment:
      - DATABASE_URL=postgresql://kenji:kenji@postgres:5432/kenji
      - STORAGE_ROOT=/data/storage
      - PLUGINS_ROOT=/data/plugins
      - LOG_DIR=/data/logs
      - SECRET_KEY=${SECRET_KEY:-dev-secret-key}
      - LOG_LEVEL=INFO
      - PORT=8000
    volumes:
      - storage_data:/data/storage
      - logs_data:/data/logs
```

### .env.docker

For Docker Compose, create `.env` file:

```bash
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://kenji:kenji@postgres:5432/kenji
STORAGE_ROOT=/data/storage
PLUGINS_ROOT=/data/plugins
LOG_DIR=/data/logs
```

Start with:
```bash
docker-compose --env-file .env up
```

## Production Configuration

### Environment Variables (Required)

```bash
# REQUIRED CHANGES FROM DEFAULTS
SECRET_KEY=your-very-secure-random-key-min-32-chars
DATABASE_URL=postgresql://user:secure-password@db.example.com/kenji_prod
STORAGE_ROOT=/var/lib/kenji/storage
PLUGINS_ROOT=/var/lib/kenji/plugins

# RECOMMENDED
LOG_DIR=/var/log/kenji
LOG_LEVEL=WARNING
HOST=127.0.0.1  # Use reverse proxy (nginx) for external access
PORT=8000
TOKEN_EXPIRE_HOURS=24
```

### Generate Secure SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Output: TlJ_V1z3...  (copy this value)
export SECRET_KEY=TlJ_V1z3...
```

### Database Setup

Create PostgreSQL database and user:

```sql
CREATE USER kenji WITH PASSWORD 'secure-password-here';
CREATE DATABASE kenji_prod OWNER kenji;
GRANT ALL PRIVILEGES ON DATABASE kenji_prod TO kenji;
```

Then set:
```bash
DATABASE_URL=postgresql://kenji:secure-password-here@db.example.com/kenji_prod
```

### Storage Directory

Create and set permissions:

```bash
sudo mkdir -p /var/lib/kenji/storage
sudo chown kenji:kenji /var/lib/kenji/storage
sudo chmod 750 /var/lib/kenji/storage

sudo mkdir -p /var/lib/kenji/plugins/_system
sudo chown -R kenji:kenji /var/lib/kenji/plugins
sudo chmod -R 750 /var/lib/kenji/plugins
```

### Log Directory

Create and set permissions:

```bash
sudo mkdir -p /var/log/kenji
sudo chown kenji:kenji /var/log/kenji
sudo chmod 750 /var/log/kenji
```

### Run with Systemd

Create `/etc/systemd/system/kenji.service`:

```ini
[Unit]
Description=3DKenji API Server
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=kenji
WorkingDirectory=/opt/kenji
EnvironmentFile=/opt/kenji/.env.prod
ExecStart=/opt/kenji/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kenji
sudo systemctl start kenji
sudo systemctl status kenji
```

### Nginx Reverse Proxy

Configure nginx to proxy requests to 3DKenji:

```nginx
upstream kenji {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    client_max_body_size 10M;  # Match max file size
    
    location / {
        proxy_pass http://kenji;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Kubernetes Configuration

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kenji-config
data:
  LOG_LEVEL: "INFO"
  STORAGE_ROOT: "/data/storage"
  LOG_DIR: "/data/logs"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: kenji-secret
type: Opaque
stringData:
  DATABASE_URL: postgresql://user:password@postgres:5432/kenji
  SECRET_KEY: your-secret-key-here
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kenji
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: kenji
        image: kenji:1.0.0
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: kenji-secret
              key: DATABASE_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: kenji-secret
              key: SECRET_KEY
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: kenji-config
              key: LOG_LEVEL
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Troubleshooting

### "Cannot connect to database"

Check DATABASE_URL:
```bash
psql "$DATABASE_URL"  # Should connect successfully
```

### "Permission denied" on storage

Fix permissions:
```bash
sudo chown kenji:kenji $STORAGE_ROOT
sudo chmod 755 $STORAGE_ROOT
```

### Logs not being written

Check LOG_DIR exists and is writable:
```bash
touch $LOG_DIR/test.log && rm $LOG_DIR/test.log
```

### Port 8000 already in use

Change PORT or kill existing process:
```bash
export PORT=8001
# or
lsof -i :8000 | grep -v PID | awk '{print $2}' | xargs kill -9
```

## Security Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Use strong database password
- [ ] Enable HTTPS/TLS in production
- [ ] Run with dedicated `kenji` user (not root)
- [ ] Set restrictive file permissions (750, 755)
- [ ] Enable log rotation and retention
- [ ] Configure firewall to only allow HTTPS (port 443)
- [ ] Set up monitoring and alerting
- [ ] Regular database backups
- [ ] Enable audit logging for sensitive operations
