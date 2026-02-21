"""Theme management system for pluggable UI theming."""

import logging
from typing import Optional

from backend.core.plugin_interfaces import ThemePlugin
from backend.core.plugins import PluginManager

logger = logging.getLogger(__name__)


class ThemeManager:
    """Manages theme plugins and theme selection."""

    def __init__(self, plugin_manager: PluginManager):
        """
        Initialize theme manager.

        Args:
            plugin_manager: Plugin manager instance to discover themes.
        """
        self.plugin_manager = plugin_manager
        self._themes_cache: dict[str, ThemePlugin] = {}
        self._default_theme: Optional[str] = None

    async def load_themes(self) -> None:
        """Discover and load all theme plugins."""
        themes = self.plugin_manager.get_by_type("theme")
        
        for plugin in themes:
            self._themes_cache[plugin.theme_name] = plugin
            if hasattr(plugin, "is_default") and plugin.is_default:
                self._default_theme = plugin.theme_name
                logger.info(f"Set default theme to: {plugin.theme_name}")
        
        # If no default set, use first theme or "dark"
        if not self._default_theme:
            if "dark" in self._themes_cache:
                self._default_theme = "dark"
            elif self._themes_cache:
                self._default_theme = list(self._themes_cache.keys())[0]
        
        logger.info(f"Loaded {len(self._themes_cache)} themes")

    async def get_theme(self, theme_name: Optional[str] = None) -> ThemePlugin:
        """
        Get a theme by name.

        Args:
            theme_name: Name of theme to load. If None, returns default theme.

        Returns:
            ThemePlugin instance.

        Raises:
            ValueError: If theme not found.
        """
        if not theme_name:
            theme_name = self._default_theme or "dark"
        
        if theme_name not in self._themes_cache:
            raise ValueError(f"Theme not found: {theme_name}")
        
        return self._themes_cache[theme_name]

    async def get_theme_css(self, theme_name: Optional[str] = None) -> str:
        """
        Get CSS for a theme.

        Args:
            theme_name: Name of theme. If None, uses default.

        Returns:
            CSS string.
        """
        theme = await self.get_theme(theme_name)
        return await theme.get_css()

    async def get_theme_variables(
        self, theme_name: Optional[str] = None
    ) -> dict[str, str]:
        """
        Get CSS variables for a theme.

        Args:
            theme_name: Name of theme. If None, uses default.

        Returns:
            Dict of CSS variable names to values.
        """
        theme = await self.get_theme(theme_name)
        return await theme.get_css_variables()

    async def list_themes(self) -> list[dict]:
        """
        List all available themes.

        Returns:
            List of theme info dicts with 'name' and 'is_default' keys.
        """
        themes = []
        for name, plugin in self._themes_cache.items():
            themes.append({
                "name": name,
                "is_default": name == self._default_theme,
                "version": plugin.version,
            })
        return sorted(themes, key=lambda t: (not t["is_default"], t["name"]))

    @property
    def default_theme(self) -> str:
        """Get the default theme name."""
        return self._default_theme or "dark"

    @property
    def available_themes(self) -> list[str]:
        """Get list of all available theme names."""
        return list(self._themes_cache.keys())
