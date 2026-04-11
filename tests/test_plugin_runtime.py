from pathlib import Path

import pytest

from backend.core.plugins import PluginManager
from backend.themes import ThemeManager


@pytest.mark.asyncio
async def test_plugin_manager_bootstraps_core_themes(tmp_path: Path):
    manager = PluginManager(tmp_path)

    await manager.load_plugins(app=None)  # type: ignore[arg-type]

    plugins = manager.list_plugins()
    assert any(plugin.plugin_id == "core-themes" for plugin in plugins)
    assert set(manager.theme_plugins.keys()) == {"dark", "light"}
    assert (tmp_path / "core-themes" / "plugin.yaml").exists()
    assert (tmp_path / "_system" / "plugin-registry.yaml").exists()


@pytest.mark.asyncio
async def test_theme_manager_uses_plugin_settings_default(tmp_path: Path):
    manager = PluginManager(tmp_path)
    await manager.load_plugins(app=None)  # type: ignore[arg-type]
    manager.save_plugin_settings("core-themes", "default_theme: light\n")
    await manager.load_plugins(app=None)  # type: ignore[arg-type]

    theme_manager = ThemeManager(manager)
    await theme_manager.load_themes()

    themes = await theme_manager.list_themes()
    assert theme_manager.default_theme == "light"
    assert themes[0]["name"] == "light"
    css = await theme_manager.get_theme_css("light")
    assert "--bg-primary: #ffffff;" in css


@pytest.mark.asyncio
async def test_plugin_manager_persists_enable_state(tmp_path: Path):
    manager = PluginManager(tmp_path)
    await manager.load_plugins(app=None)  # type: ignore[arg-type]

    manager.set_plugin_enabled("core-themes", False)
    await manager.load_plugins(app=None)  # type: ignore[arg-type]

    plugin = manager.get_plugin("core-themes")
    assert plugin.enabled is False
    assert manager.theme_plugins == {}