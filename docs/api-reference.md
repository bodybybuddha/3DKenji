# API Reference

Complete documentation of all 3DKenji REST API endpoints.

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
  "email": "alice@example.com",
  "password": "SecurePassword123!",
  "display_name": "Alice Smith"
}
```

**Parameters**:
- `username` (string, required) – Unique username, 3-50 chars
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

---

## Projects Endpoints

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
  "description": "Printer calibration prints"
}
```

**Parameters**:
- `title` (string, required) – Project name, 1-200 chars
- `description` (string, optional) – Project description

**Response** (201):
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
- `400` – Title missing or too long

---

### List Projects
Get all projects for authenticated user (paginated).

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
      "id": 1,
      "title": "Benchy Calibration",
      "description": "Printer calibration prints",
      "owner_id": "user_123",
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
Update project title or description.

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
  "description": "Updated description"
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

### Delete Project
Delete a project and all its models.

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

## Models Endpoints

### Upload Model
Upload a 3D model file to a project.

**Request**:
```
POST /projects/{project_id}/models
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Parameters**:
- `project_id` (integer, required, path) – Project ID
- `file` (file, required, multipart) – Model file (.stl, .3mf, .obj, .gcode)
- `tags` (string, optional, multipart) – Comma-separated tags
- `custom_metadata` (JSON, optional, multipart) – Custom metadata

**Response** (201):
```json
{
  "id": 1,
  "project_id": 1,
  "filename": "benchy.stl",
  "size_bytes": 1048576,
  "file_type": "application/octet-stream",
  "storage_key": "projects/1/models/1/benchy.stl",
  "created_at": "2026-02-21T10:30:45Z",
  "tags": ["calibration"],
  "custom_metadata": {},
  "owner_id": "user_123"
}
```

**Errors**:
- `401` – Unauthorized
- `403` – Not the project owner
- `400` – Invalid file type (not .stl/.3mf/.obj/.gcode)
- `400` – File too large (> 10MB)
- `404` – Project not found

---

### List Models
Get all models in a project.

**Request**:
```
GET /projects/{project_id}/models?skip=0&limit=10
Authorization: Bearer <token>
```

**Parameters**:
- `project_id` (integer, required, path) – Project ID
- `skip` (integer, optional) – Pagination offset
- `limit` (integer, optional) – Items per page

**Response** (200):
```json
{
  "items": [
    {
      "id": 1,
      "project_id": 1,
      "filename": "benchy.stl",
      "size_bytes": 1048576,
      "file_type": "application/octet-stream",
      "storage_key": "projects/1/models/1/benchy.stl",
      "created_at": "2026-02-21T10:30:45Z",
      "tags": [],
      "custom_metadata": {},
      "owner_id": "user_123"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 10
}
```

**Errors**:
- `401` – Unauthorized
- `403` – Access denied
- `404` – Project not found

---

### Get Model
Get metadata for a specific model.

**Request**:
```
GET /models/{id}
Authorization: Bearer <token>
```

**Parameters**:
- `id` (integer, required) – Model ID

**Response** (200):
```json
{
  "id": 1,
  "project_id": 1,
  "filename": "benchy.stl",
  "size_bytes": 1048576,
  "file_type": "application/octet-stream",
  "storage_key": "projects/1/models/1/benchy.stl",
  "created_at": "2026-02-21T10:30:45Z",
  "tags": ["calibration"],
  "custom_metadata": {"nozzle_temp": 210},
  "owner_id": "user_123"
}
```

**Errors**:
- `401` – Unauthorized
- `403` – Access denied
- `404` – Model not found

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
