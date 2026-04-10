---
layout: default
title: Plugin Development
---

# Plugin Development Guide

3DKenji uses a plugin architecture for extensibility. This guide explains how to build custom plugins.

## Plugin System Overview

The plugin system allows you to extend 3DKenji with custom implementations for:

- **AuthProvider** – Custom authentication (GitHub OAuth, SAML, LDAP)
- **StorageBackend** – Custom storage (S3, Azure Blob, GCS)
- **MediaProcessor** – Custom media processing
- **Viewer** – Custom 3D viewers
- **MetadataHandler** – Custom metadata extraction

## Core Concepts

### PluginManager

The `PluginManager` discovers and loads plugins from the `backend/plugins/` directory.

```python
from backend.core.plugins import PluginManager

manager = PluginManager()

# List available plugins
auth_plugins = manager.get_plugins('AuthProvider')
storage_plugins = manager.get_plugins('StorageBackend')

# Load a plugin
auth = manager.load('PasswordAuthProvider')
```

### Plugin Interfaces

All plugins inherit from base interfaces in `backend/core/plugin_interfaces.py`.

## Building an AuthProvider Plugin

### 1. Create the Plugin File

Create `backend/plugins/auth_github.py`:

```python
import httpx
from typing import Optional
from backend.core.plugin_interfaces import AuthProvider, AuthResult, UserIdentity

class GitHubAuthProvider(AuthProvider):
    """GitHub OAuth authentication provider"""
    
    name = "GitHubOAuth"
    version = "1.0.0"
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = httpx.AsyncClient()
    
    async def authenticate(self, provider_data: dict) -> Optional[AuthResult]:
        """
        Authenticate using GitHub OAuth code.
        
        Args:
            provider_data: {"code": "github-auth-code"}
        
        Returns:
            AuthResult with user identity and token, or None if failed
        """
        code = provider_data.get("code")
        if not code:
            return None
        
        # Exchange code for access token
        token_response = await self.client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"}
        )
        
        if token_response.status_code != 200:
            return None
        
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            return None
        
        # Get user info from GitHub
        user_response = await self.client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_response.status_code != 200:
            return None
        
        user_data = user_response.json()
        
        # Return AuthResult with user identity
        return AuthResult(
            success=True,
            user_identity=UserIdentity(
                provider="github",
                provider_user_id=str(user_data["id"]),
                email=user_data.get("email"),
                display_name=user_data.get("name", user_data["login"]),
                avatar_url=user_data.get("avatar_url"),
            ),
            token=access_token,
            refresh_token=None,
        )
    
    async def verify_token(self, token: str) -> Optional[UserIdentity]:
        """Verify a GitHub access token is still valid"""
        response = await self.client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            return None
        
        user_data = response.json()
        return UserIdentity(
            provider="github",
            provider_user_id=str(user_data["id"]),
            email=user_data.get("email"),
            display_name=user_data.get("name", user_data["login"]),
        )
    
    async def refresh_token(self, refresh_token: str) -> Optional[str]:
        """GitHub OAuth tokens don't have refresh tokens"""
        return None
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke a GitHub access token"""
        # GitHub doesn't provide a revoke endpoint, just return True
        return True
```

### 2. Register the Plugin

Update `backend/plugins/__init__.py` to enable the plugin:

```python
from .auth_github import GitHubAuthProvider

__all__ = ["GitHubAuthProvider"]
```

### 3. Use in Main App

Update `backend/main.py`:

```python
from backend.plugins.auth_github import GitHubAuthProvider
from backend.core.plugins import PluginManager

# Initialize GitHub OAuth provider
github_provider = GitHubAuthProvider(
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
)

# Add GitHub OAuth endpoint
@app.post("/api/v1/auth/github")
async def github_login(request: dict, db: Session = Depends(get_db)):
    """Login with GitHub OAuth"""
    result = await github_provider.authenticate(request)
    if not result or not result.success:
        raise HTTPException(status_code=401, detail="GitHub auth failed")
    
    # ... create/update user and issue JWT token
```

## Building a StorageBackend Plugin

### 1. Create the Plugin File

Create `backend/plugins/storage_s3.py`:

```python
import boto3
from typing import Optional
from pathlib import Path
from backend.core.plugin_interfaces import StorageBackend, ProcessResult

class S3StorageBackend(StorageBackend):
    """Amazon S3 storage backend"""
    
    name = "S3Storage"
    version = "1.0.0"
    
    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        access_key: str = None,
        secret_key: str = None,
    ):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            "s3",
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
    
    async def store(self, source_path: Path, destination_key: str) -> str:
        """
        Upload file to S3.
        
        Args:
            source_path: Local file path
            destination_key: S3 object key
        
        Returns:
            The destination_key
        """
        with open(source_path, "rb") as f:
            self.s3_client.upload_fileobj(
                f,
                self.bucket_name,
                destination_key,
                ExtraArgs={"ContentType": "application/octet-stream"}
            )
        
        return destination_key
    
    async def retrieve(self, storage_key: str) -> bytes:
        """Download file from S3"""
        obj = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=storage_key,
        )
        return obj["Body"].read()
    
    async def delete(self, storage_key: str) -> bool:
        """Delete file from S3"""
        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=storage_key,
        )
        return True
    
    async def get_url(self, storage_key: str) -> str:
        """Get public URL for S3 object"""
        return f"https://{self.bucket_name}.s3.amazonaws.com/{storage_key}"
    
    async def health_check(self) -> ProcessResult:
        """Check S3 connectivity"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return ProcessResult(
                success=True,
                message="S3 bucket accessible"
            )
        except Exception as e:
            return ProcessResult(
                success=False,
                message=f"S3 error: {str(e)}"
            )
```

### 2. Register and Use

Update `backend/main.py`:

```python
from backend.plugins.storage_s3 import S3StorageBackend
import os

# Initialize S3 storage
storage_backend = S3StorageBackend(
    bucket_name=os.getenv("S3_BUCKET_NAME"),
    region_name=os.getenv("S3_REGION", "us-east-1"),
    access_key=os.getenv("AWS_ACCESS_KEY_ID"),
    secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
```

## Plugin Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
async def authenticate(self, provider_data: dict) -> Optional[AuthResult]:
    try:
        # ... authentication logic
    except httpx.RequestError as e:
        logger.error(f"Auth provider error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

### 2. Async Operations

All plugin methods are async. Use `await` for I/O:

```python
async def authenticate(self, provider_data: dict) -> Optional[AuthResult]:
    # ✓ Correct: async I/O
    response = await self.client.get(url)
    
    # ✗ Wrong: blocking I/O
    response = requests.get(url)
```

### 3. Configuration

Use environment variables for plugin configuration:

```python
def __init__(self):
    self.api_key = os.getenv("PLUGIN_API_KEY")
    self.timeout = int(os.getenv("PLUGIN_TIMEOUT", "30"))
```

### 4. Logging

Log important events:

```python
from backend.logging_config import get_logger

logger = get_logger(__name__)

async def authenticate(self, provider_data: dict):
    logger.info(f"Authenticating with {self.name}")
    # ... authentication logic
    logger.debug(f"Auth result: {result}")
```

### 5. Testing

Create tests for your plugin:

```python
# tests/unit/test_auth_github.py
import pytest
from backend.plugins.auth_github import GitHubAuthProvider

@pytest.fixture
def github_provider():
    return GitHubAuthProvider(
        client_id="test-client-id",
        client_secret="test-client-secret",
    )

@pytest.mark.asyncio
async def test_authenticate(github_provider):
    result = await github_provider.authenticate({"code": "test-code"})
    assert result is None or result.success is False  # Without real credentials
```

## Plugin Interfaces

### AuthProvider

```python
class AuthProvider:
    async def authenticate(provider_data: dict) -> Optional[AuthResult]:
        """Authenticate user with provider data"""
    
    async def verify_token(token: str) -> Optional[UserIdentity]:
        """Verify a token is still valid"""
    
    async def refresh_token(refresh_token: str) -> Optional[str]:
        """Get a new access token from refresh token"""
    
    async def revoke_token(token: str) -> bool:
        """Revoke a token"""
```

### StorageBackend

```python
class StorageBackend:
    async def store(source_path: Path, destination_key: str) -> str:
        """Store a file"""
    
    async def retrieve(storage_key: str) -> bytes:
        """Retrieve file contents"""
    
    async def delete(storage_key: str) -> bool:
        """Delete a file"""
    
    async def get_url(storage_key: str) -> str:
        """Get URL to access file"""
    
    async def health_check() -> ProcessResult:
        """Check backend health"""
```

## Examples

### GitHub OAuth Plugin
See [auth_github.py](#building-an-authprovider-plugin) example above.

### S3 Storage Plugin
See [storage_s3.py](#building-a-storagebackend-plugin) example above.

### Contributing Plugins

To contribute a plugin to the main project:

1. Implement the plugin interface
2. Add comprehensive tests (>80% coverage)
3. Create documentation in `/docs/plugins/`
4. Submit a pull request to the main repository
5. Plugins must not introduce breaking changes to core APIs

## Questions?

- **Documentation**: [Main docs](index.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/3dkenji/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/3dkenji/discussions)
