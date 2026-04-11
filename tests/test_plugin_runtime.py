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


@pytest.mark.asyncio
async def test_plugin_manager_resolves_viewer_by_extension(tmp_path: Path):
    import yaml

    viewer_dir = tmp_path / "stl-viewer-plugin"
    assets_dir = viewer_dir / "assets" / "viewers"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "stl-viewer.js").write_text("console.log('stl viewer');\n", encoding="utf-8")
    manifest = {
        "id": "stl-viewer-plugin",
        "name": "STL Viewer Plugin",
        "version": "1.0.0",
        "type": "viewer",
        "viewers": [
            {
                "id": "stl-viewer",
                "name": "STL Viewer",
                "extensions": ["stl", "3mf"],
                "js_file": "assets/viewers/stl-viewer.js",
            }
        ],
    }
    (viewer_dir / "plugin.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    (viewer_dir / "settings.yaml").write_text("enabled: true\n", encoding="utf-8")

    manager = PluginManager(tmp_path)
    await manager.load_plugins(app=None)  # type: ignore[arg-type]

    stl_viewer = manager.get_viewer_for_extension("stl")
    assert stl_viewer is not None
    assert stl_viewer.viewer_id == "stl-viewer"

    threemf_viewer = manager.get_viewer_for_extension(".3mf")
    assert threemf_viewer is not None
    assert threemf_viewer.plugin_id == "stl-viewer-plugin"

    assert manager.get_viewer_for_extension("obj") is None