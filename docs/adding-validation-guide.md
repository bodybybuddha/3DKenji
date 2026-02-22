# Adding Input Validation to Existing Endpoints

This guide shows how to add proper validation to your FastAPI endpoints to prevent the issues you've been experiencing.

## The Problem

You mentioned fixing issues reactively as they pop up. This usually means:
- ❌ Missing validation on required fields
- ❌ No length limits enforced
- ❌ Special characters not handled
- ❌ Security vulnerabilities (XSS, SQL injection)
- ❌ Inconsistent validation between frontend and backend
- ❌ Poor error messages

## The Solution

Add **comprehensive validation at multiple layers**:

### Layer 1: Pydantic Models (Data Validation)
### Layer 2: FastAPI Path/Query Validation
### Layer 3: Business Logic Validation
### Layer 4: Database Constraints

---

## 1. Pydantic Model Validation

### Before (Weak Validation)
```python
from pydantic import BaseModel

class ProjectCreate(BaseModel):
    name: str
    description: str = None
```

**Problems:**
- No length limits
- No format validation
- Allows empty strings
- No XSS prevention

### After (Strong Validation)
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
import re
import html

class ProjectCreate(BaseModel):
    name: str = Field(
        ...,  # Required
        min_length=3,
        max_length=100,
        description="Project name"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Project description"
    )
    
    @validator('name')
    def validate_name(cls, v):
        # Trim whitespace
        v = v.strip()
        
        # Reject if empty after trimming
        if not v:
            raise ValueError('Name cannot be empty or whitespace only')
        
        # Reject dangerous characters
        if any(char in v for char in ['<', '>', '"', "'"]):
            raise ValueError('Name contains invalid characters')
        
        # Escape HTML to prevent XSS
        v = html.escape(v)
        
        return v
    
    @validator('description')
    def validate_description(cls, v):
        if v:
            # Escape HTML
            v = html.escape(v.strip())
        return v
```

---

## 2. Username Validation (Security Critical)

```python
from pydantic import BaseModel, Field, validator
import re

class UserCreate(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (alphanumeric and underscore only)"
    )
    email: EmailStr  # Built-in email validation
    password: str = Field(..., min_length=8, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    
    @validator('username')
    def validate_username(cls, v):
        v = v.strip().lower()
        
        # Only alphanumeric and underscore
        if not re.match(r'^[a-z0-9_]+$', v):
            raise ValueError(
                'Username must contain only letters, numbers, and underscores'
            )
        
        # Reserved names
        reserved = ['admin', 'root', 'system', 'api', 'www']
        if v in reserved:
            raise ValueError('This username is reserved')
        
        return v
    
    @validator('password')
    def validate_password(cls, v):
        # Check minimum complexity
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        # Optionally check for complexity
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        
        return v
    
    @validator('display_name')
    def validate_display_name(cls, v):
        if v:
            import html
            v = html.escape(v.strip())
            if not v:
                return None
        return v
```

---

## 3. File Upload Validation

```python
from fastapi import UploadFile, HTTPException
from typing import List

ALLOWED_EXTENSIONS = {'.stl', '.obj', '.3mf', '.gcode'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

async def validate_file_upload(file: UploadFile) -> UploadFile:
    """Validate uploaded file."""
    
    # Check filename
    if not file.filename:
        raise HTTPException(400, "No filename provided")
    
    # Sanitize filename (prevent path traversal)
    safe_filename = os.path.basename(file.filename)
    if safe_filename != file.filename:
        raise HTTPException(400, "Invalid filename")
    
    # Check extension
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (read chunk by chunk)
    size = 0
    chunk_size = 8192
    content = bytearray()
    
    while chunk := await file.read(chunk_size):
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            raise HTTPException(400, f"File too large (max {MAX_FILE_SIZE} bytes)")
        content.extend(chunk)
    
    # Reset file pointer
    file.file.seek(0)
    
    # Validate content type
    if file.content_type not in ['application/octet-stream', 'model/stl', 'model/obj']:
        raise HTTPException(400, f"Invalid content type: {file.content_type}")
    
    return file
```

---

## 4. Query Parameter Validation

```python
from fastapi import Query
from typing import Optional

@router.get("/projects")
async def list_projects(
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, max_length=100),
    sort_by: str = Query("created_at", regex="^(name|created_at|updated_at)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
):
    """List projects with validated parameters."""
    
    # Sanitize search query
    if search:
        import html
        search = html.escape(search.strip())
    
    # ... rest of implementation
```

---

## 5. Database Uniqueness Validation

```python
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project with validation."""
    
    # Check for duplicate name (per user)
    existing = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.name == project_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project '{project_data.name}' already exists"
        )
    
    try:
        project = Project(
            name=project_data.name,
            description=project_data.description,
            user_id=current_user.id
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project
    
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database constraint violation"
        )
```

---

## 6. Rate Limiting

```python
from fastapi import Request, HTTPException
from datetime import datetime, timedelta
from collections import defaultdict

# Simple in-memory rate limiter (use Redis in production)
rate_limit_data = defaultdict(list)

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Decorator for rate limiting."""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Get client identifier
            client_id = request.client.host
            now = datetime.utcnow()
            
            # Clean old requests
            rate_limit_data[client_id] = [
                req_time for req_time in rate_limit_data[client_id]
                if now - req_time < timedelta(seconds=window_seconds)
            ]
            
            # Check limit
            if len(rate_limit_data[client_id]) >= max_requests:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Try again in {window_seconds} seconds."
                )
            
            # Record request
            rate_limit_data[client_id].append(now)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
@router.post("/auth/login")
@rate_limit(max_requests=5, window_seconds=300)  # 5 attempts per 5 minutes
async def login(request: Request, credentials: LoginCredentials):
    # ... login logic
    pass
```

---

## 7. Consistent Error Responses

```python
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any

class ErrorDetail(BaseModel):
    field: str
    message: str

class ErrorResponse(BaseModel):
    error: str
    details: List[ErrorDetail] = []

def format_validation_error(exc: ValidationError) -> ErrorResponse:
    """Convert Pydantic validation error to consistent format."""
    details = []
    for error in exc.errors():
        field = '.'.join(str(loc) for loc in error['loc'])
        details.append(ErrorDetail(
            field=field,
            message=error['msg']
        ))
    
    return ErrorResponse(
        error="Validation failed",
        details=details
    )

# Use in exception handler
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content=format_validation_error(exc).dict()
    )
```

---

## 8. Frontend Validation (HTMX)

### Add validation endpoint
```python
@router.post("/validate/project-name")
async def validate_project_name(
    name: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate project name and return error if invalid."""
    
    # Length check
    if len(name) < 3:
        return HTMLResponse("<span class='error'>Name too short (min 3 chars)</span>")
    if len(name) > 100:
        return HTMLResponse("<span class='error'>Name too long (max 100 chars)</span>")
    
    # Check duplicates
    existing = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.name == name
    ).first()
    
    if existing:
        return HTMLResponse("<span class='error'>Name already exists</span>")
    
    return HTMLResponse("<span class='success'>✓</span>")
```

### HTML form with HTMX validation
```html
<form hx-post="/api/v1/projects" hx-target="#result">
    <input 
        type="text" 
        name="name" 
        hx-post="/api/v1/projects/validate/project-name"
        hx-trigger="blur"
        hx-target="#name-error"
    />
    <span id="name-error"></span>
    
    <button type="submit">Create Project</button>
</form>
<div id="result"></div>
```

---

## 9. Security Headers

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response
```

---

## 10. Validation Checklist

For **every** user input field, ensure:

- [ ] **Type validation** (string, int, email, etc.)
- [ ] **Required vs optional** explicitly defined
- [ ] **Length limits** (min/max)
- [ ] **Format validation** (regex where appropriate)
- [ ] **Whitespace handling** (trim, reject whitespace-only)
- [ ] **Special characters** (allow, reject, or escape)
- [ ] **HTML escaping** for display (prevent XSS)
- [ ] **SQL injection prevention** (use parameterized queries)
- [ ] **Path traversal prevention** (for file paths)
- [ ] **Uniqueness constraints** (where applicable)
- [ ] **Business logic validation** (e.g., date ranges)
- [ ] **Rate limiting** (for sensitive operations)
- [ ] **Clear error messages** (user-friendly)
- [ ] **Consistent error format** (JSON structure)
- [ ] **Frontend validation** (for UX)
- [ ] **Backend validation** (for security)
- [ ] **Tests** (validation tests for all cases)

---

## Quick Wins

### 1. Add HTML Escaping Everywhere
```python
import html

# Before returning user-generated content
safe_text = html.escape(user_input)
```

### 2. Add Length Limits to All String Fields
```python
name: str = Field(..., min_length=1, max_length=100)
```

### 3. Use Pydantic's Built-in Validators
```python
from pydantic import EmailStr, HttpUrl, constr

email: EmailStr  # Validates email format
website: HttpUrl  # Validates URL format
username: constr(regex=r'^[a-z0-9_]+$')  # Regex validation
```

### 4. Centralize Validation Logic
```python
# src/backend/core/validation.py
def validate_username(username: str) -> str:
    """Centralized username validation."""
    # ... validation logic
    return username

# Use everywhere
validated_username = validate_username(input_username)
```

---

## Testing Your Validation

```python
def test_project_name_too_short(auth_client):
    response = auth_client.post("/api/v1/projects", json={
        "name": "ab"  # Too short
    })
    assert response.status_code == 400
    assert "too short" in response.json()["detail"].lower()

def test_xss_in_project_name(auth_client):
    response = auth_client.post("/api/v1/projects", json={
        "name": "<script>alert('xss')</script>"
    })
    # Should either reject or sanitize
    if response.status_code == 201:
        assert "<script>" not in response.json()["name"]
```

---

## Summary

The key to preventing reactive bug fixing is **comprehensive, layered validation**:

1. **Pydantic models** - Type and format validation
2. **Custom validators** - Business logic validation
3. **Database constraints** - Data integrity
4. **Rate limiting** - Abuse prevention
5. **Frontend validation** - User experience
6. **Backend validation** - Security (never trust the client)
7. **Comprehensive tests** - Catch issues before production

Start with the most critical endpoints (auth, user input) and work your way through the application systematically.
