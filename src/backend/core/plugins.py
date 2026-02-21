"""Plugin manager for discovering, loading, and managing plugins."""

import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type

from fastapi import FastAPI

from .plugin_interfaces import (
    AuthProvider,
    KeajiPlugin,
    MediaProcessor,
    MetadataHandler,
    StorageBackend,
    ThemePlugin,
    Viewer,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""

    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Initialize plugin manager.

        Args:
            plugins_dir: Path to plugins directory. If None, uses backend/plugins/.
        """
        self.plugins_dir = plugins_dir or Path(__file__).parent.parent / "plugins"
        self.plugins: Dict[str, KeajiPlugin] = {}
        self.auth_providers: List[AuthProvider] = []
        self.storage_backends: Dict[str, StorageBackend] = {}
        self.media_processors: Dict[str, List[MediaProcessor]] = {}
        self.viewers: Dict[str, Viewer] = {}
        self.metadata_handlers: List[MetadataHandler] = []
        self.theme_plugins: Dict[str, ThemePlugin] = {}

    async def load_plugins(self, app: FastAPI, config: dict) -> None:
        """
        Discover and initialize all plugins from plugins_dir.

        Args:
            app: FastAPI application instance.
            config: Plugin configuration dict (e.g., from config.yaml or env).
        """
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return

        # Add plugins_dir to sys.path temporarily for imports
        plugins_path = str(self.plugins_dir)
        if plugins_path not in sys.path:
            sys.path.insert(0, plugins_path)

        # Discover .py files in plugins_dir (skip __pycache__, __init__.py)
        plugin_files = [
            f
            for f in self.plugins_dir.glob("*.py")
            if f.name != "__init__.py" and not f.name.startswith("_")
        ]

        for plugin_file in plugin_files:
            module_name = plugin_file.stem
            try:
                logger.info(f"Loading plugin module: {module_name}")
                module = importlib.import_module(module_name)

                # Find all KeajiPlugin subclasses in module
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, KeajiPlugin)
                        and obj is not KeajiPlugin
                    ):
                        try:
                            plugin_instance = obj()
                            plugin_config = config.get(module_name, {})
                            if not plugin_config.get("enabled", True):
                                logger.info(f"Plugin {plugin_instance.name} disabled")
                                continue

                            # Register plugin
                            await plugin_instance.register(app, plugin_config)
                            self.plugins[plugin_instance.name] = plugin_instance
                            logger.info(
                                f"Loaded plugin: {plugin_instance.name} "
                                f"v{plugin_instance.version}"
                            )

                            # Index by type for quick lookup
                            if isinstance(plugin_instance, AuthProvider):
                                self.auth_providers.append(plugin_instance)
                            elif isinstance(plugin_instance, StorageBackend):
                                self.storage_backends[plugin_instance.storage_type] = (
                                    plugin_instance
                                )
                            elif isinstance(plugin_instance, MediaProcessor):
                                proc_type = plugin_instance.processor_type
                                if proc_type not in self.media_processors:
                                    self.media_processors[proc_type] = []
                                self.media_processors[proc_type].append(
                                    plugin_instance
                                )
                            elif isinstance(plugin_instance, Viewer):
                                self.viewers[plugin_instance.viewer_type] = (
                                    plugin_instance
                                )
                            elif isinstance(plugin_instance, ThemePlugin):
                                self.theme_plugins[plugin_instance.theme_name] = (
                                    plugin_instance
                                )
                            elif isinstance(plugin_instance, MetadataHandler):
                                self.metadata_handlers.append(plugin_instance)

                        except Exception as e:
                            logger.error(
                                f"Failed to load plugin class {name}: {e}",
                                exc_info=True,
                            )

            except Exception as e:
                logger.error(
                    f"Failed to load plugin module {module_name}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"Plugin manager ready: "
            f"{len(self.plugins)} plugin(s) loaded, "
            f"{len(self.auth_providers)} auth provider(s), "
            f"{len(self.storage_backends)} storage backend(s)"
        )

    def get_auth_provider(self, auth_type: str) -> Optional[AuthProvider]:
        """Get auth provider by type."""
        for provider in self.auth_providers:
            if provider.auth_type == auth_type:
                return provider
        return None

    def get_storage_backend(self, storage_type: str = "local") -> Optional[
        StorageBackend
    ]:
        """Get storage backend by type (default: local)."""
        return self.storage_backends.get(storage_type)

    def get_media_processor(
        self, processor_type: str
    ) -> Optional[MediaProcessor]:
        """Get first media processor of given type."""
        processors = self.media_processors.get(processor_type, [])
        return processors[0] if processors else None

    def get_viewer(self, viewer_type: str) -> Optional[Viewer]:
        """Get viewer by type."""
        return self.viewers.get(viewer_type)

    def get_by_type(self, plugin_type: str) -> List[KeajiPlugin]:
        """
        Get all plugins of a given type.
        
        Args:
            plugin_type: Type of plugin ("theme", "auth", "storage", etc.)
        
        Returns:
            List of plugins matching the type.
        """
        if plugin_type == "theme":
            return list(self.theme_plugins.values())
        elif plugin_type == "auth":
            return self.auth_providers
        elif plugin_type == "storage":
            return list(self.storage_backends.values())
        elif plugin_type == "viewer":
            return list(self.viewers.values())
        elif plugin_type == "metadata":
            return self.metadata_handlers
        else:
            # Return all plugins matching the capability
            return [p for p in self.plugins.values() if plugin_type in p.capabilities]

    async def health_check(self) -> dict:
        """Get health status of all plugins."""
        statuses = {}
        for name, plugin in self.plugins.items():
            try:
                status = await plugin.health_check()
                statuses[name] = status
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                statuses[name] = {"status": "error", "error": str(e)}
        return {"plugins": statuses, "total": len(self.plugins)}

    def list_auth_providers(self) -> List[dict]:
        """List available auth providers for frontend discovery."""
        return [
            {
                "name": provider.name,
                "auth_type": provider.auth_type,
                "version": provider.version,
            }
            for provider in self.auth_providers
        ]
