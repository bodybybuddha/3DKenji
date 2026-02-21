"""Plugin interfaces and base classes for 3D Kenji extensibility."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import FastAPI


@dataclass
class AuthResult:
    """Result of authentication attempt."""

    user_id: str
    username: str
    email: str
    display_name: str
    scopes: list[str] = None  # Optional permission scopes from auth provider


@dataclass
class UserIdentity:
    """Validated user identity."""

    user_id: str
    username: str
    email: str
    display_name: str


@dataclass
class ProcessResult:
    """Result of media processing."""

    output_path: str
    metadata: dict
    mimetype: str


@dataclass
class ViewerResponse:
    """Response from viewer plugin."""

    html: Optional[str] = None  # HTML to render (iframe or embed)
    asset_url: Optional[str] = None  # URL to asset
    error: Optional[str] = None


class KeajiPlugin(ABC):
    """Base interface for all plugins."""

    name: str
    version: str
    author: str
    capabilities: list[str]  # e.g., ["media-processor", "viewer"]

    @abstractmethod
    async def register(self, app: FastAPI, config: dict) -> None:
        """Called at startup. Plugin registers routes/handlers with FastAPI app."""
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """Return plugin status for observability. Should include 'status' key."""
        pass


class AuthProvider(KeajiPlugin):
    """Pluggable authentication strategy interface."""

    auth_type: str  # "password", "github", "google", "ldap", "saml"
    capabilities = ["auth-provider"]

    @abstractmethod
    async def authenticate(self, credentials: dict) -> AuthResult:
        """
        Authenticate user and return identity.

        Args:
            credentials: provider-specific dict
                - For password: {"username": str, "password": str}
                - For OAuth: {"code": str, "state": str, "redirect_uri": str}

        Returns:
            AuthResult with user identity and scopes.

        Raises:
            ValueError: If authentication fails.
        """
        pass

    @abstractmethod
    async def get_login_url(self, state: str, redirect_uri: str) -> Optional[str]:
        """
        For interactive flows (OAuth): return login URL.
        For simple auth (password): return None.
        """
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> Optional[UserIdentity]:
        """
        Validate an issued token/session and return user identity.

        Returns:
            UserIdentity if valid, None if invalid or expired.
        """
        pass


class StorageBackend(KeajiPlugin):
    """Pluggable storage for media and models."""

    storage_type: str  # "local", "s3", "azure"
    capabilities = ["storage-backend"]

    @abstractmethod
    async def store(self, source_path: str, destination_key: str) -> str:
        """
        Store a file and return its access URL/key.

        Args:
            source_path: Local file path to upload.
            destination_key: Logical key (e.g., "projects/{id}/models/{name}").

        Returns:
            String that can be used to retrieve the file later.
        """
        pass

    @abstractmethod
    async def retrieve(self, storage_key: str) -> bytes:
        """
        Retrieve file contents by storage key.

        Raises:
            FileNotFoundError: If key does not exist.
        """
        pass

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Delete a stored file."""
        pass

    @abstractmethod
    async def get_url(self, storage_key: str) -> str:
        """Return a URL to access the stored file."""
        pass


class MediaProcessor(KeajiPlugin):
    """Process media (timelapse, resizing, transcoding, etc.)."""

    processor_type: str  # "timelapse", "image-resize", "video-transcode"
    capabilities = ["media-processor"]

    @abstractmethod
    async def process(
        self,
        source_path: str,
        project_id: str,
        model_id: Optional[str],
        metadata: dict,
    ) -> ProcessResult:
        """
        Process source file and return result.

        Args:
            source_path: Local path to source file.
            project_id: Project ID for context.
            model_id: Model ID if processing model-specific media.
            metadata: Additional context (e.g., frame rate, codec).

        Returns:
            ProcessResult with output path and metadata.
        """
        pass

    @abstractmethod
    async def supported_formats(self) -> list[str]:
        """Return list of supported input file extensions."""
        pass


class Viewer(KeajiPlugin):
    """Render or preview a resource."""

    viewer_type: str  # "model-3d", "image", "note"
    capabilities = ["viewer"]

    @abstractmethod
    async def render(
        self, resource_id: str, resource_type: str, context: dict
    ) -> ViewerResponse:
        """
        Render a resource and return HTML or asset URL.

        Args:
            resource_id: ID of the resource to render.
            resource_type: Type of resource ("model", "media", "note").
            context: Additional context (e.g., project_id, user_id for permissions).

        Returns:
            ViewerResponse with HTML, asset URL, or error.
        """
        pass

    @abstractmethod
    async def supported_types(self) -> list[str]:
        """Return list of supported file extensions or MIME types."""
        pass


class MetadataHandler(KeajiPlugin):
    """Custom schema validators and enrichment for project/model metadata."""

    handler_type: str  # "gcode-validator", "printer-profile", etc.
    capabilities = ["metadata-handler"]

    @abstractmethod
    async def validate(self, metadata: dict) -> tuple[bool, Optional[str]]:
        """
        Validate metadata against schema.

        Returns:
            Tuple of (is_valid, error_message).
        """
        pass

    @abstractmethod
    async def enrich(self, metadata: dict) -> dict:
        """
        Enrich metadata with additional computed fields.

        Example: receive GCODE settings, return validated + normalized metadata.
        """
        pass
