---
layout: default
title: API Reference
---

# API Reference

Complete documentation of all 3DKenji REST API endpoints.

## Contents

- [Authentication](#authentication)
- [Authentication Endpoints](#authentication-endpoints)
- [Projects](#projects-endpoints)
- [Project Files](#project-files)
- [API Keys](#api-keys)
- [Health & Status](#health--status)

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All protected endpoints require `Authorization` header with JWT bearer token:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Tokens are obtained from the authentication endpoints and expire after 24 hours.

## Response Format

All responses are JSON with consistent structure:

**Success (2xx)**:
```json
{
  "id": 1,
  "title": "Project Name",
  ...
}
```

**Error (4xx/5xx)**:
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Authentication Endpoints

### Register User
Create a new user account and receive JWT token.

**Request**:
```
POST /auth/register
Content-Type: application/json
```

**Body**:
```json
{
  "username": "alice",
  "nickname": "alice-prints",
  "email": "alice@example.com",
  "password": "SecurePassword123!",
  "display_name": "Alice Smith"
}
```

**Parameters**:
- `username` (string, required) – Unique username, 3-50 chars
- `nickname` (string, optional) – Storage-safe nickname (3-64 chars, lowercase letters/numbers/`_`/`-`)
- `email` (string, required) – Valid email address
- `password` (string, required) – Minimum 8 characters
- `display_name` (string, optional) – User's display name

**Response** (201):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `400` – Email already exists
- `400` – Weak password (< 8 chars)
- `400` – Invalid email format

---

### Login
Authenticate with username and password.

**Request**:
```
POST /auth/login
Content-Type: application/json
```

**Body**:
```json
{
  "username": "alice",
  "password": "SecurePassword123!"
}
```

**Response** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401` – Invalid credentials
- `404` – User not found

---

### Change Password
Update user password (requires authentication).

**Request**:
```
POST /auth/password-change
Authorization: Bearer <token>
Content-Type: application/json
```

**Body**:
```json
{
  "old_password": "SecurePassword123!",
  "new_password": "NewSecurePassword456!"
}
```

**Response** (200):
```json
{
  "message": "Password changed successfully"
}
```

**Errors**:
- `401` – Unauthorized (no valid token)
- `400` – Old password incorrect
- `400` – New password too weak

### OAuth / OIDC Endpoints

These endpoints enable external OIDC authentication and account linking. Replace `{provider}` with your configured provider slug (default: `oidc`). OAuth configuration is now stored in the database through the admin settings screen. See [docs/oauth-setup.md](docs/oauth-setup.md) for operator setup and examples.

- `GET /auth/oauth/{provider}/authorize` — Initiate OIDC login (redirects to provider).
  - Auth: public
  - Response: HTTP 302 redirect to provider authorization URL.
  - Errors: `400` for misconfiguration, `503` if IdP unreachable.

- `GET /auth/oauth/{provider}/callback` — OIDC callback endpoint.
  - Auth: public (called by provider)
  - Behavior: validates `state` and ID token, issues 3DKenji JWT, sets cookie (if configured), and redirects to frontend or returns JSON depending on client.
  - Errors: `400` invalid/expired state, `401` invalid ID token, `500` internal validation error.

- `POST /auth/oauth/{provider}/link` — Start link flow for logged-in users.
  - Auth: requires existing authenticated session (Bearer token or cookie)
  - Request: empty body
  - Response (200): `{ "authorize_url": "https://..." }` — a URL the client can open to complete linking.
  - Errors: `401` unauthenticated, `400` provider misconfigured.

- `DELETE /auth/oauth/{provider}/unlink` — Unlink a provider from your account.
  - Auth: requires authenticated session and user must have a local password set
  - Request: empty body
  - Response (204): No content on success
  - Errors: `401` unauthenticated, `403` local password not set (prevents lockout), `404` provider not linked.

- `POST /auth/admin/recovery-login` — Admin-only local credential recovery.
  - Auth: public (used as fallback)
  - Request JSON:
    ```json
    { "username": "admin", "password": "LocalPassword!" }
    ```
  - Response (200): `{ "access_token": "...", "token_type": "bearer" }`
  - Errors: `401` invalid credentials, `403` account is not an admin.

- `POST /auth/admin/set-local-password` — Admin sets a local password (useful if admin account was created via OIDC).
  - Auth: requires admin JWT (logged in via OIDC or recovery)
  - Request JSON:
    ```json
    { "new_password": "NewRecoveryPassword!" }
    ```
  - Response (200): `{ "message": "Local password set" }`
  - Errors: `401` unauthenticated, `403` not an admin, `400` weak password.

### Admin OAuth Configuration

- `POST /admin/settings/oauth` — Save database-backed OAuth / OIDC settings from the admin settings page.
  - Auth: requires admin session or admin JWT cookie/session
  - Content type: `application/x-www-form-urlencoded` (used by the admin UI)
  - Request fields:
    - `enabled` — checkbox; enables OIDC login
    - `provider_name` — URL slug such as `oidc`
    - `issuer_url` — provider issuer URL
    - `client_id` — provider client ID
    - `client_secret` — new client secret value; leave blank to keep the stored secret
    - `callback_url` — full OIDC callback URL
    - `scopes` — space-separated scopes
    - `cookie_secure` — checkbox; mark auth cookie as secure
    - `clear_client_secret` — checkbox; removes the stored secret
  - Response (200): HTML success fragment used by the admin settings page
  - Errors: `400` invalid or incomplete settings, `403` admin access required

---

## Projects Endpoints

### Access Model

- Owners have full project access.
- Collaborators can be assigned `viewer` (read) or `editor` (write) roles.
- Public projects are readable without authentication via dedicated public endpoints.

### Create Project
Create a new project (requires authentication).

**Request**:
```
POST /projects
Authorization: Bearer <token>
Content-Type: application/json
```

**Body**:
```json
{
  "title": "Benchy Calibration",
  "description": "Printer calibration prints",
  "visibility": "private"
}
```

**Parameters**:
- `title` (string, required) – Project name, 1-200 chars
- `description` (string, optional) – Project description
- `visibility` (string, optional) – `private` or `public`

**Response** (201):
```json
{
  "id": "a5e4420a-3e22-41c3-a219-0bd9d8b7ab07",
  "title": "Benchy Calibration",
  "slug": "benchy-calibration",
  "category": "Uncategorized",
  "visibility": "private",
  "directory_path": "Projects/alice-prints/benchy-calibration",
  "owner_id": "user_123",
  "created_at": "2026-02-21T10:30:45Z",
  "updated_at": "2026-02-21T10:30:45Z"
}
```

**Errors**:
- `401` – Unauthorized
- `400` – Title missing or too long

---

### List Projects
Get all projects accessible to the authenticated user (owned + collaborator + public).

**Request**:
```
GET /projects?skip=0&limit=10
Authorization: Bearer <token>
```

**Query Parameters**:
- `skip` (integer, optional, default=0) – Number of items to skip
- `limit` (integer, optional, default=10) – Number of items to return

**Response** (200):
```json
{
  "items": [
    {
      "id": "project_123",
      "title": "Benchy Calibration",
      "owner_id": "user_123",
      "slug": "benchy-calibration",
      "category": "Calibration",
      "visibility": "private",
      "directory_path": "/data/storage/Projects/alice/benchy-calibration",
      "disk_size_bytes": 24576,
      "is_archived": false,
      "created_at": "2026-02-21T10:30:45Z",
      "updated_at": "2026-02-21T10:30:45Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 10
}
```

**Errors**:
- `401` – Unauthorized

---

### Get Project
Get details of a specific project.

**Request**:
```
GET /projects/{id}
Authorization: Bearer <token>
```

**Parameters**:
- `id` (integer, required) – Project ID

**Response** (200):
```json
{
  "id": 1,
  "title": "Benchy Calibration",
  "description": "Printer calibration prints",
  "owner_id": "user_123",
  "created_at": "2026-02-21T10:30:45Z",
  "updated_at": "2026-02-21T10:30:45Z"
}
```

**Errors**:
- `401` – Unauthorized
- `403` – Access denied (not your project)
- `404` – Project not found

---

### Update Project
Update project title/category/visibility.

**Request**:
```
PATCH /projects/{id}
Authorization: Bearer <token>
Content-Type: application/json
```

**Body**:
```json
{
  "title": "Updated Project Name",
  "custom_metadata": {
    "category": "Calibration",
    "visibility": "public"
  }
}
```

**Parameters**:
- `title` (string, optional) – New project name
- `description` (string, optional) – New description

**Response** (200):
```json
{
  "id": 1,
  "title": "Updated Project Name",
  "description": "Updated description",
  "owner_id": "user_123",
  "created_at": "2026-02-21T10:30:45Z",
  "updated_at": "2026-02-21T10:30:46Z"
}
```

**Errors**:
- `401` – Unauthorized
- `403` – Not the project owner
- `404` – Project not found

---

### List Public Projects
List publicly visible projects without authentication.

**Request**:
```
GET /projects/public?skip=0&limit=100
```

**Response** (200):
```json
{
  "items": [
    {
      "id": "a5e4420a-3e22-41c3-a219-0bd9d8b7ab07",
      "title": "Benchy Calibration",
      "slug": "benchy-calibration",
      "visibility": "public"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

---

### Get Public Project
Read one publicly visible project without authentication.

**Request**:
```
GET /projects/public/{project_id}
```

**Errors**:
- `404` – Not found, private, or archived

---

## Collaboration Endpoints

All collaboration management endpoints below require owner permissions on the target project.

### List Collaborators
```
GET /projects/{project_id}/collaborators
Authorization: Bearer <token>
```

### Add or Update Collaborator
```
POST /projects/{project_id}/collaborators
Authorization: Bearer <token>
Content-Type: application/json
```

Body:
```json
{
  "user_id": "b84a2750-c27f-43e4-a735-a09f8f4c5c5f",
  "role": "editor"
}
```

### Remove Collaborator
```
DELETE /projects/{project_id}/collaborators/{user_id}
Authorization: Bearer <token>
```

---

## Invitation Endpoints

### Create Invitation
```
POST /projects/{project_id}/invitations
Authorization: Bearer <token>
Content-Type: application/json
```

Body:
```json
{
  "email": "collaborator@example.com",
  "role": "viewer",
  "expires_in_days": 7
}
```

Returns a one-time invitation token and invitation metadata.

### List Project Invitations
```
GET /projects/{project_id}/invitations?include_inactive=false
Authorization: Bearer <token>
```

### Update Invitation Role
```
PATCH /projects/{project_id}/invitations/{invitation_id}
Authorization: Bearer <token>
Content-Type: application/json
```

### Revoke Invitation
```
DELETE /projects/{project_id}/invitations/{invitation_id}
Authorization: Bearer <token>
```

### Accept Invitation by Token
```
POST /projects/invitations/{token}/accept
Authorization: Bearer <token>
```

### Accept Invitation by ID
```
POST /projects/invitations/id/{invitation_id}/accept
Authorization: Bearer <token>
```

### List My Pending Invitations
```
GET /projects/invitations/mine
Authorization: Bearer <token>
```

Pending invitations are matched by authenticated user email. Acceptance fails if invitation email does not match the current user.

---

### Delete Project
Delete a project and its associated metadata.

**Request**:
```
DELETE /projects/{id}
Authorization: Bearer <token>
```

**Parameters**:
- `id` (integer, required) – Project ID

**Response** (204): No content

**Errors**:
- `401` – Unauthorized
- `403` – Not the project owner
- `404` – Project not found

---

## Project Files Endpoints

### List Project Files
List files in a project directory. This powers the Project Files browser in the web UI.

**Request**:
```
GET /projects/{project_id}/files?path=models
Authorization: Bearer <token>
```

**Parameters**:
- `project_id` (integer, required, path) – Project ID
- `path` (string, optional, query) – Directory inside the project to browse. Defaults to project root.
- `format` (string, optional, query) – Use `html` for server-rendered fragments; omit for JSON.

**Response** (200):
```json
{
  "project_id": 1,
  "path": "models",
  "parent_path": "",
  "items": [
    {
      "name": "benchy.stl",
      "relative_path": "models/benchy.stl",
      "is_dir": false,
      "size_bytes": 1048576,
      "size": "1.0 MB",
      "extension": "stl",
      "is_editable": false,
      "viewer": {
        "viewer_id": "stl-viewer",
        "name": "STL Basic Preview",
        "plugin_id": "stl-viewer-plugin",
        "has_js": true
      }
    }
  ]
}
```

**Errors**:
- `401` – Unauthorized
- `403` – Access denied
- `400` – Invalid or traversal path
- `404` – Directory not found

---

### Upload Project File
Upload a file into the selected project directory.

**Request**:
```
POST /projects/{project_id}/files/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Parameters**:
- `project_id` (integer, required, path) – Project ID
- `file` (file, required, multipart) – File to upload
- `path` (string, optional, multipart) – Target directory inside the project, such as `models` or `images`

**Response** (201):
```json
{
  "project_id": 1,
  "path": "models",
  "relative_path": "models/benchy.stl",
  "name": "benchy.stl",
  "size_bytes": 1048576,
  "size": "1.0 MB"
}
```

**Errors**:
- `401` – Unauthorized
- `403` – Not the project owner
- `400` – Invalid filename or target path
- `404` – Directory not found
- `413` – File too large (> 100MB)

---

### Preview Project File
Preview a file in JSON or HTML form. Text formats return inline preview text, and viewer-enabled formats can render through plugin-provided preview code.

**Request**:
```
GET /projects/{project_id}/files/preview?path=models/benchy.stl
Authorization: Bearer <token>
```

**Parameters**:
- `project_id` (integer, required, path) – Project ID
- `path` (string, required, query) – File path inside the project
- `format` (string, optional, query) – Use `html` for rendered preview markup; omit for JSON

**Response** (200):
```json
{
  "path": "models/benchy.stl",
  "extension": "stl",
  "size_bytes": 1048576,
  "viewer": {
    "viewer_id": "stl-viewer",
    "name": "STL Basic Preview",
    "plugin_id": "stl-viewer-plugin",
    "has_js": true
  },
  "preview_mode": "binary",
  "preview_text": null
}
```

**Errors**:
- `401` – Unauthorized
- `403` – Access denied
- `400` – Invalid path or directory requested instead of a file
- `404` – File not found

---

### Download Project File
Download a file from a project.

**Request**:
```
GET /projects/{project_id}/files/download?path=models/benchy.stl
Authorization: Bearer <token>
```

**Parameters**:
- `project_id` (integer, required, path) – Project ID
- `path` (string, required, query) – File path inside the project

**Response** (200): Binary file download

**Errors**:
- `401` – Unauthorized
- `403` – Access denied
- `400` – Invalid path
- `404` – File not found

---

## API Keys Endpoints

### Create API Key
Generate a new API key for programmatic access.

**Request**:
```
POST /keys
Authorization: Bearer <token>
Content-Type: application/json
```

**Body**:
```json
{
  "name": "CI/CD Pipeline"
}
```

**Parameters**:
- `name` (string, required) – Key name for identification

**Response** (201):
```json
{
  "id": "key_abc123",
  "name": "CI/CD Pipeline",
  "created_at": "2026-02-21T10:30:45Z",
  "secret": "sk_live_abc123def456ghi789jkl..."
}
```

**Important**: The `secret` is only shown once. Store it securely.

**Errors**:
- `401` – Unauthorized
- `400` – Name missing

---

### List API Keys
Get all API keys for authenticated user (secrets not shown).

**Request**:
```
GET /keys
Authorization: Bearer <token>
```

**Response** (200):
```json
{
  "items": [
    {
      "id": "key_abc123",
      "name": "CI/CD Pipeline",
      "created_at": "2026-02-21T10:30:45Z"
    }
  ],
  "total": 1
}
```

**Errors**:
- `401` – Unauthorized

---

### Revoke API Key
Delete and disable an API key immediately.

**Request**:
```
DELETE /keys/{id}
Authorization: Bearer <token>
```

**Parameters**:
- `id` (string, required) – Key ID (e.g., "key_abc123")

**Response** (204): No content

**Errors**:
- `401` – Unauthorized
- `403` – Permission denied
- `404` – Key not found

---

## Health & Status Endpoints

### Full System Health
Get complete health status of all components.

**Request**:
```
GET /health
```

**Response** (200):
```json
{
  "status": "ok",
  "timestamp": "2026-02-21T10:30:45.123Z",
  "components": [
    {
      "name": "storage_backend",
      "status": "ok",
      "timestamp": "2026-02-21T10:30:45.123Z"
    },
    {
      "name": "database",
      "status": "ok",
      "timestamp": "2026-02-21T10:30:45.123Z"
    }
  ]
}
```

---

### Readiness Probe
Check if service is ready to accept requests (Kubernetes).

**Request**:
```
GET /health/ready
```

**Response**: 
- `200` – Service is ready
- `503` – Service not ready

---

### Liveness Probe
Check if service process is alive (Kubernetes).

**Request**:
```
GET /health/live
```

**Response**:
- `200` – Service is alive
- `503` – Service failed

---

## Status Codes Reference

| Code | Meaning |
|------|---------|
| 200 | OK – Request succeeded |
| 201 | Created – Resource created successfully |
| 204 | No Content – Successful, no response body |
| 400 | Bad Request – Invalid parameters |
| 401 | Unauthorized – Missing or invalid token |
| 403 | Forbidden – Permission denied |
| 404 | Not Found – Resource not found |
| 500 | Internal Server Error – Server error |
| 503 | Service Unavailable – Service not ready |

---

## Rate Limiting

Currently no rate limiting is implemented. Production deployments should add rate limiting via reverse proxy (nginx, CloudFlare, etc.).

## Examples

### cURL Examples
See [getting-started.md](getting-started.md) for common cURL examples.

### Python Example
```python
import requests

BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# List projects
response = requests.get(
    f"{BASE_URL}/projects",
    headers={"Authorization": f"Bearer {TOKEN}"}
)
projects = response.json()
```

### JavaScript/Fetch Example
```javascript
const BASE_URL = "http://localhost:8000/api/v1";
const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";

// List projects
const response = await fetch(`${BASE_URL}/projects`, {
  headers: {
    "Authorization": `Bearer ${TOKEN}`
  }
});
const projects = await response.json();
```
