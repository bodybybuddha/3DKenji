---
layout: default
title: Plugin Development
---

# Plugin Development Guide

3DKenji now loads plugins from an installation-specific external plugin root instead of from `src/backend/plugins`. This guide explains the v1 package layout and how to build plugins that can be discovered safely at startup.

## Contents

- [Plugin System Overview](#plugin-system-overview)
- [Plugin Root](#plugin-root)
- [Manifest Files](#manifest-files)
- [Plugin Best Practices](#plugin-best-practices)
- [Plugin Interfaces](#plugin-interfaces)

## Plugin System Overview

The plugin system allows you to extend 3DKenji with custom implementations for:

- **Cosmetic plugins** – CSS-driven themes and visual overrides
- **Viewer plugins** – File viewers matched by extension for project page previews

Public API routes are not plugin-defined in v1. Core code owns request routing, permission checks, and response shaping.

## Plugin Root

Plugins are discovered from `PLUGINS_ROOT` at application startup.

Default locations:
- App containers: `/data/plugins`
- Devcontainer: `/working/plugins`

Each plugin package is one directory under `PLUGINS_ROOT`:

```text
PLUGINS_ROOT/
├── _system/
│   └── plugin-registry.yaml
└── core-themes/
    ├── plugin.yaml
    ├── settings.yaml
    └── assets/
        └── themes/
            ├── dark.css
            └── light.css
```

## Core Concepts

### PluginManager

The runtime `PluginManager` discovers plugin folders from `PLUGINS_ROOT`, validates `plugin.yaml`, ensures `settings.yaml` exists, merges central enable-state from `_system/plugin-registry.yaml`, and then exposes active theme and viewer contributions to the application.

```python
from backend.core.plugins import PluginManager

manager = PluginManager()
await manager.load_plugins(app, {})

themes = manager.get_by_type("theme")
plugins = manager.list_plugins()
```

### Manifest Files

Each plugin package must contain a `plugin.yaml` manifest. Example:

```yaml
id: core-themes
name: Core Themes
version: 0.1.0
author: 3DKenji
type: cosmetic
description: Bundled dark and light themes.
themes:
  - name: dark
    label: Dark
    css_file: assets/themes/dark.css
    default: true
  - name: light
    label: Light
    css_file: assets/themes/light.css
settings_defaults:
  default_theme: dark
```

### settings.yaml

Each plugin owns an editable `settings.yaml`. The admin plugin page serves this file in a text editor and writes it back after YAML validation.

Internal implementation note: markdown files opened through the standalone project file editor (`/projects/{project_id}/files/editor`) are rendered and edited with Toast UI Editor (`tui.editor`) loaded from the Toast CDN. The editor follows the active app theme (`dark`/`light`) and re-initializes on theme toggle so markdown source and preview remain readable in both modes.

Example:

```yaml
default_theme: dark
```

### Central Enable State

Plugin enable/disable state is installation-level and stored outside the plugin package in:

```yaml
plugins:
  core-themes:
    enabled: true
```

This data lives in `PLUGINS_ROOT/_system/plugin-registry.yaml`.

## Cosmetic Plugins

Cosmetic plugins contribute CSS assets only in v1. A single plugin package can expose multiple named theme variants, which is how the bundled dark and light themes are implemented now.

## Viewer Plugins

Viewer plugins are matched by file extension declared in `plugin.yaml`.

Example manifest fragment:

```yaml
viewers:
  - id: stl-viewer
    name: STL Viewer
    extensions:
      - stl
    js_file: assets/viewers/stl-viewer.js
    backend_entrypoint: viewer.renderers.stl:render
```

Viewer plugins may ship JS assets and backend entrypoint metadata, but core routes still decide when they execute.

## Operational Notes

- Startup discovery only: new plugin folders and manifest changes are picked up on application restart.
- The admin plugin page edits `settings.yaml` and the central enable-state registry only.
- If a plugin manifest is malformed, the package is skipped and reported as invalid in admin.
- If `settings.yaml` is missing, the runtime creates it from `settings_defaults` declared in `plugin.yaml`.
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
