---
layout: default
title: Getting Started
---

# Getting Started with 3DKenji

Get up and running with 3DKenji in minutes.

## Installation

### Option 1: Docker Compose (Recommended)

The fastest way to get started with all dependencies:

```bash
git clone https://github.com/yourusername/3dkenji.git
cd 3dkenji
docker-compose up
```

This starts:
- FastAPI backend on `http://localhost:8000`
- PostgreSQL database on `localhost:5432`
- Interactive API docs on `http://localhost:8000/docs`

### Option 2: Local Development

If you prefer to run on your machine:

```bash
# Clone repository
git clone https://github.com/yourusername/3dkenji.git
cd 3dkenji

# Install dependencies (creates virtual environment)
make install

# Run development server
make dev
```

Server runs at `http://localhost:8000`.

### Option 3: Devcontainer

For VS Code users:

1. Open the repository in VS Code
2. Click the "Reopen in Container" prompt
3. Devcontainer automatically:
   - Creates Python virtual environment
   - Installs all dependencies
   - Starts PostgreSQL database
   - Sets up debugging

## Your First Project

### Step 1: Create a User Account

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "MySecurePassword123!",
    "display_name": "Alice Smith"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Important**: Save the `access_token` – you'll use it for all requests.

### Step 2: Create Your First Project

```bash
TOKEN="your-token-from-step-1"

curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Benchy Calibration",
    "description": "Calibration prints for printer tuning"
  }'
```

Response includes project `id`:
```json
{
  "id": 1,
  "title": "Benchy Calibration",
  "description": "Calibration prints for printer tuning",
  "owner_id": "user_123",
  "created_at": "2026-02-21T10:30:45Z"
}
```

### Step 3: Upload a 3D Model

Use the project ID from step 2:

```bash
curl -X POST http://localhost:8000/api/v1/projects/1/models \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/benchy.stl" \
  -F "tags=calibration,benchmark" \
  -F "custom_metadata={\"nozzle_temp\": 210, \"bed_temp\": 60}"
```

### Step 4: List Your Models

```bash
curl -X GET http://localhost:8000/api/v1/projects/1/models \
  -H "Authorization: Bearer $TOKEN"
```

## Interactive API Documentation

3DKenji provides interactive Swagger UI for exploring the API:

1. Start the server: `make dev` or `docker-compose up`
2. Open browser: `http://localhost:8000/docs`
3. Click "Authorize" and enter your token
4. Try endpoints directly in the browser

## Common Tasks

### Change Your Password

```bash
curl -X POST http://localhost:8000/api/v1/auth/password-change \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "old_password": "MySecurePassword123!",
    "new_password": "NewSecurePassword456!"
  }'
```

### Create an API Key for Automation

```bash
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Home Assistant Integration"}'
```

Response (secret shown once):
```json
{
  "id": "key_abc123",
  "name": "Home Assistant Integration",
  "created_at": "2026-02-21T10:30:45Z",
  "secret": "sk_live_abc123def456ghi789jkl..."
}
```

Use the secret in API requests:
```bash
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer sk_live_abc123def456ghi789jkl..."
```

### Update a Project

```bash
curl -X PATCH http://localhost:8000/api/v1/projects/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Benchy Calibration Prints",
    "description": "Updated description"
  }'
```

### Delete a Project

Deletes the project and all its models:

```bash
curl -X DELETE http://localhost:8000/api/v1/projects/1 \
  -H "Authorization: Bearer $TOKEN"
```

## File Upload Details

### Supported File Types
- `.stl` – Stereolithography (most common)
- `.3mf` – 3D Manufacturing Format
- `.obj` – Wavefront OBJ
- `.gcode` – G-code (printer-ready)

### File Size Limit
Maximum 10MB per file.

### Upload Response

```json
{
  "id": 1,
  "project_id": 1,
  "filename": "benchy.stl",
  "size_bytes": 1048576,
  "file_type": "application/vnd.ms-pmd",
  "storage_key": "projects/1/models/1/benchy.stl",
  "created_at": "2026-02-21T10:30:45Z",
  "tags": ["calibration", "benchmark"],
  "custom_metadata": {},
  "owner_id": "user_123"
}
```

## Testing

Run the test suite:

```bash
make test
```

Tests verify:
- ✅ User authentication and JWT tokens
- ✅ Project CRUD operations
- ✅ File upload and validation
- ✅ API key generation
- ✅ Health check endpoints

## Troubleshooting

**Q: "Connection refused" error**
- Ensure PostgreSQL is running: `docker-compose ps`
- Check `DATABASE_URL` is correct

**Q: "Port 8000 already in use"**
```bash
# Find process on port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

**Q: CORS error when using from frontend**
- CORS is not configured by default
- Set `CORS_ORIGINS` environment variable to allow origins

**Q: File upload fails**
- Check file format is in: .stl, .3mf, .obj, .gcode
- Check file size is under 10MB
- Check storage directory is writable

## Next Steps

- **[API Reference](api-reference.md)** – Full endpoint documentation
- **[Configuration](configuration.md)** – Customize environment
- **[Plugin Development](plugin-development.md)** – Build custom extensions
- **[Deployment](configuration.md#production)** – Deploy to production

## Getting Help

- **Documentation**: [Online docs](https://docs.example.com)
- **Issues**: [GitHub Issues](https://github.com/yourusername/3dkenji/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/3dkenji/discussions)
