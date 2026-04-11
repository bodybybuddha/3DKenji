"""External plugin registry for installation-specific plugins."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import FastAPI

logger = logging.getLogger(__name__)

_CSS_VAR_PATTERN = re.compile(r"(?P<name>--[A-Za-z0-9\-_]+)\s*:\s*(?P<value>[^;]+);")


def get_plugins_root() -> Path:
    """Return the configured external plugins root."""
    return Path(os.environ.get("PLUGINS_ROOT", "/data/plugins"))


@dataclass(slots=True)
class ThemeContribution:
    """One theme contribution exposed by an installed plugin package."""

    plugin_id: str
    plugin_name: str
    theme_name: str
    label: str
    version: str
    css_path: Path
    is_default: bool = False

    async def get_css(self) -> str:
        return self.css_path.read_text(encoding="utf-8")

    async def get_css_variables(self) -> dict[str, str]:
        css = await self.get_css()
        variables: dict[str, str] = {}
        for match in _CSS_VAR_PATTERN.finditer(css):
            variables[match.group("name")] = match.group("value").strip()
        return variables


@dataclass(slots=True)
class ViewerContribution:
    """Viewer contribution metadata reserved for project-page integration."""

    plugin_id: str
    viewer_id: str
    name: str
    extensions: list[str] = field(default_factory=list)
    js_file: Optional[Path] = None
    backend_entrypoint: Optional[str] = None


@dataclass(slots=True)
class PluginRecord:
    """Installed plugin package metadata."""

    plugin_id: str
    name: str
    version: str
    plugin_type: str
    author: str
    description: str
    plugin_dir: Path
    manifest_path: Path
    settings_path: Path
    enabled: bool
    status: str
    warnings: list[str] = field(default_factory=list)
    themes: list[ThemeContribution] = field(default_factory=list)
    viewers: list[ViewerContribution] = field(default_factory=list)

    @property
    def contribution_count(self) -> int:
        return len(self.themes) + len(self.viewers)


class PluginManager:
    """Manages external plugin discovery, registry state, and contributions."""

    def __init__(self, plugins_root: Optional[Path] = None):
        self.plugins_root = plugins_root or get_plugins_root()
        self.system_dir = self.plugins_root / "_system"
        self.registry_path = self.system_dir / "plugin-registry.yaml"
        self.plugins: dict[str, PluginRecord] = {}
        self.theme_plugins: dict[str, ThemeContribution] = {}
        self.viewers: dict[str, ViewerContribution] = {}

    async def load_plugins(self, app: FastAPI, config: dict | None = None) -> None:
        """Discover plugin packages from the configured external plugins root."""
        del app, config

        self.plugins.clear()
        self.theme_plugins.clear()
        self.viewers.clear()

        self._ensure_plugin_root()
        self._bootstrap_default_plugins()

        registry = self._read_yaml_file(self.registry_path, default={"plugins": {}})
        registry_plugins = registry.get("plugins", {}) if isinstance(registry, dict) else {}

        for plugin_dir in sorted(self.plugins_root.iterdir()):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue

            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                logger.warning("Skipping plugin without plugin.yaml: %s", plugin_dir)
                continue

            try:
                manifest = self._read_yaml_file(manifest_path, default={})
                if not isinstance(manifest, dict):
                    raise ValueError("plugin.yaml must contain a mapping at the document root")
                record = self._build_plugin_record(plugin_dir, manifest, registry_plugins)
                self.plugins[record.plugin_id] = record
                if record.enabled:
                    for theme in record.themes:
                        self.theme_plugins[theme.theme_name] = theme
                    for viewer in record.viewers:
                        self.viewers[viewer.viewer_id] = viewer
            except Exception as exc:
                plugin_id = plugin_dir.name
                logger.error("Failed to load plugin %s: %s", plugin_id, exc)
                self.plugins[plugin_id] = PluginRecord(
                    plugin_id=plugin_id,
                    name=plugin_id,
                    version="unknown",
                    plugin_type="invalid",
                    author="",
                    description="",
                    plugin_dir=plugin_dir,
                    manifest_path=manifest_path,
                    settings_path=plugin_dir / "settings.yaml",
                    enabled=False,
                    status="invalid",
                    warnings=[str(exc)],
                )

        logger.info(
            "Plugin registry ready: %s plugin(s), %s active theme(s), %s viewer(s)",
            len(self.plugins),
            len(self.theme_plugins),
            len(self.viewers),
        )

    def get_by_type(self, plugin_type: str) -> list[Any]:
        if plugin_type == "theme":
            return list(self.theme_plugins.values())
        if plugin_type == "viewer":
            return list(self.viewers.values())
        return [plugin for plugin in self.plugins.values() if plugin.plugin_type == plugin_type]

    def list_plugins(self) -> list[PluginRecord]:
        return sorted(self.plugins.values(), key=lambda plugin: plugin.name.lower())

    def get_plugin(self, plugin_id: str) -> PluginRecord:
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            raise KeyError(plugin_id)
        return plugin

    def get_plugin_settings_text(self, plugin_id: str) -> str:
        return self.get_plugin(plugin_id).settings_path.read_text(encoding="utf-8")

    def save_plugin_settings(self, plugin_id: str, settings_text: str) -> None:
        parsed = yaml.safe_load(settings_text) or {}
        if not isinstance(parsed, dict):
            raise ValueError("settings.yaml must contain a YAML mapping at the document root")
        plugin = self.get_plugin(plugin_id)
        plugin.settings_path.write_text(settings_text.rstrip() + "\n", encoding="utf-8")

    def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> None:
        plugin = self.get_plugin(plugin_id)
        registry = self._read_yaml_file(self.registry_path, default={"plugins": {}})
        plugins = registry.setdefault("plugins", {})
        plugin_state = plugins.setdefault(plugin_id, {})
        plugin_state["enabled"] = bool(enabled)
        self._write_yaml_file(self.registry_path, registry)
        plugin.enabled = bool(enabled)

    def get_viewer_for_extension(self, extension: str) -> Optional[ViewerContribution]:
        normalized = extension.lower().lstrip(".")
        for viewer in self.viewers.values():
            if normalized in {value.lower().lstrip('.') for value in viewer.extensions}:
                return viewer
        return None

    async def health_check(self) -> dict[str, Any]:
        return {
            "plugins": {
                plugin.plugin_id: {
                    "status": plugin.status,
                    "enabled": plugin.enabled,
                    "warnings": plugin.warnings,
                }
                for plugin in self.list_plugins()
            },
            "total": len(self.plugins),
        }

    def _ensure_plugin_root(self) -> None:
        self.plugins_root.mkdir(parents=True, exist_ok=True)
        self.system_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._write_yaml_file(self.registry_path, {"plugins": {}})

    def _bootstrap_default_plugins(self) -> None:
        plugin_dir = self.plugins_root / "core-themes"
        assets_dir = plugin_dir / "assets" / "themes"
        if plugin_dir.exists():
            return

        assets_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "id": "core-themes",
            "name": "Core Themes",
            "version": "1.0.0",
            "author": "3DKenji",
            "type": "cosmetic",
            "description": "Bundled dark and light themes for the admin and user UI.",
            "themes": [
                {
                    "name": "dark",
                    "label": "Dark",
                    "css_file": "assets/themes/dark.css",
                    "default": True,
                },
                {
                    "name": "light",
                    "label": "Light",
                    "css_file": "assets/themes/light.css",
                    "default": False,
                },
            ],
            "settings_defaults": {
                "default_theme": "dark",
            },
        }
        self._write_yaml_file(plugin_dir / "plugin.yaml", manifest)
        self._write_yaml_file(plugin_dir / "settings.yaml", manifest["settings_defaults"])
        (assets_dir / "dark.css").write_text(_DEFAULT_DARK_THEME_CSS, encoding="utf-8")
        (assets_dir / "light.css").write_text(_DEFAULT_LIGHT_THEME_CSS, encoding="utf-8")

    def _build_plugin_record(
        self,
        plugin_dir: Path,
        manifest: dict[str, Any],
        registry_plugins: dict[str, Any],
    ) -> PluginRecord:
        plugin_id = str(manifest.get("id") or plugin_dir.name)
        settings_path = plugin_dir / "settings.yaml"
        if not settings_path.exists():
            defaults = manifest.get("settings_defaults", {})
            if defaults and not isinstance(defaults, dict):
                raise ValueError("settings_defaults must be a mapping")
            self._write_yaml_file(settings_path, defaults if isinstance(defaults, dict) else {})

        settings = self._read_yaml_file(settings_path, default={})
        if settings is None:
            settings = {}
        if not isinstance(settings, dict):
            raise ValueError("settings.yaml must contain a mapping at the document root")

        registry_entry = registry_plugins.get(plugin_id, {}) if isinstance(registry_plugins, dict) else {}
        enabled = bool(registry_entry.get("enabled", True))

        themes: list[ThemeContribution] = []
        raw_themes = manifest.get("themes", []) or []
        for theme_manifest in raw_themes:
            if not isinstance(theme_manifest, dict):
                raise ValueError("Each theme entry in plugin.yaml must be a mapping")
            theme_name = str(theme_manifest.get("name", "")).strip()
            css_file = str(theme_manifest.get("css_file", "")).strip()
            if not theme_name or not css_file:
                raise ValueError("Theme entries must include name and css_file")
            css_path = (plugin_dir / css_file).resolve()
            css_path.relative_to(plugin_dir.resolve())
            if not css_path.exists():
                raise ValueError(f"Theme CSS file does not exist: {css_file}")
            themes.append(
                ThemeContribution(
                    plugin_id=plugin_id,
                    plugin_name=str(manifest.get("name") or plugin_id),
                    theme_name=theme_name,
                    label=str(theme_manifest.get("label") or theme_name.title()),
                    version=str(manifest.get("version") or "0.0.0"),
                    css_path=css_path,
                    is_default=False,
                )
            )

        configured_default_theme = str(settings.get("default_theme", "")).strip()
        for theme in themes:
            manifest_default = any(
                isinstance(theme_manifest, dict)
                and str(theme_manifest.get("name", "")).strip() == theme.theme_name
                and bool(theme_manifest.get("default", False))
                for theme_manifest in raw_themes
            )
            theme.is_default = (
                theme.theme_name == configured_default_theme
                or (not configured_default_theme and manifest_default)
            )

        viewers: list[ViewerContribution] = []
        for viewer_manifest in manifest.get("viewers", []) or []:
            if not isinstance(viewer_manifest, dict):
                raise ValueError("Each viewer entry in plugin.yaml must be a mapping")
            viewer_id = str(viewer_manifest.get("id") or viewer_manifest.get("name") or "").strip()
            if not viewer_id:
                raise ValueError("Viewer entries must include id or name")
            js_file = viewer_manifest.get("js_file")
            js_path: Optional[Path] = None
            if js_file:
                js_path = (plugin_dir / str(js_file)).resolve()
                js_path.relative_to(plugin_dir.resolve())
                if not js_path.exists():
                    raise ValueError(f"Viewer JS file does not exist: {js_file}")
            viewers.append(
                ViewerContribution(
                    plugin_id=plugin_id,
                    viewer_id=viewer_id,
                    name=str(viewer_manifest.get("name") or viewer_id),
                    extensions=[str(value) for value in viewer_manifest.get("extensions", []) or []],
                    js_file=js_path,
                    backend_entrypoint=(
                        str(viewer_manifest.get("backend_entrypoint"))
                        if viewer_manifest.get("backend_entrypoint")
                        else None
                    ),
                )
            )

        status = "enabled" if enabled else "disabled"
        warnings: list[str] = []
        if not themes and not viewers:
            warnings.append("Plugin declares no active contributions")

        return PluginRecord(
            plugin_id=plugin_id,
            name=str(manifest.get("name") or plugin_id),
            version=str(manifest.get("version") or "0.0.0"),
            plugin_type=str(manifest.get("type") or "unknown"),
            author=str(manifest.get("author") or ""),
            description=str(manifest.get("description") or ""),
            plugin_dir=plugin_dir,
            manifest_path=plugin_dir / "plugin.yaml",
            settings_path=settings_path,
            enabled=enabled,
            status=status,
            warnings=warnings,
            themes=themes,
            viewers=viewers,
        )

    @staticmethod
    def _read_yaml_file(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        return default if data is None else data

    @staticmethod
    def _write_yaml_file(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


_DEFAULT_DARK_THEME_CSS = """/* Core Themes: Dark */
:root {
  --color-primary: #3b82f6;
  --color-success: #10b981;
  --color-danger: #ef4444;
  --color-warning: #f59e0b;
  --color-info: #0ea5e9;
  --bg-primary: #1f2937;
  --bg-secondary: #111827;
  --bg-tertiary: #374151;
  --text-primary: #f3f4f6;
  --text-secondary: #d1d5db;
  --text-tertiary: #9ca3af;
  --border-color: #4b5563;
  --border-light: #6b7280;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5);
}

input, textarea, select {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border-color: var(--border-color);
}

input:focus, textarea:focus, select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.btn-primary {
  background-color: var(--color-primary);
  color: white;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-danger {
  background-color: var(--color-danger);
  color: white;
}

.btn-danger:hover {
  background-color: #dc2626;
}

.card {
  background-color: var(--bg-secondary);
  border-color: var(--border-color);
  color: var(--text-primary);
}

code, pre {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
}
"""

_DEFAULT_LIGHT_THEME_CSS = """/* Core Themes: Light */
:root {
  --color-primary: #2563eb;
  --color-success: #059669;
  --color-danger: #dc2626;
  --color-warning: #d97706;
  --color-info: #0284c7;
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-tertiary: #f3f4f6;
  --text-primary: #111827;
  --text-secondary: #374151;
  --text-tertiary: #6b7280;
  --border-color: #d1d5db;
  --border-light: #e5e7eb;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.15);
}

input, textarea, select {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border-color: var(--border-color);
}

input:focus, textarea:focus, select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.btn-primary {
  background-color: var(--color-primary);
  color: white;
}

.btn-primary:hover {
  background-color: #1d4ed8;
}

.btn-danger {
  background-color: var(--color-danger);
  color: white;
}

.btn-danger:hover {
  background-color: #b91c1c;
}

.card {
  background-color: var(--bg-secondary);
  border-color: var(--border-color);
  color: var(--text-primary);
}

code, pre {
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}
"""
