"""Light theme plugin - Alternative light background theme."""

from fastapi import FastAPI

from backend.core.plugin_interfaces import ThemePlugin


class LightTheme(ThemePlugin):
    """Light theme with white backgrounds and dark text."""

    name = "LightTheme"
    version = "1.0.0"
    author = "3DKenji"
    theme_name = "light"
    is_default = False

    async def register(self, app: FastAPI, config: dict) -> None:
        """Register theme with FastAPI (no routes needed)."""
        pass

    async def health_check(self) -> dict:
        """Return theme health status."""
        return {"status": "healthy", "theme": self.theme_name}

    async def get_css_variables(self) -> dict[str, str]:
        """Return CSS variables for light theme."""
        return {
            # Semantic Colors
            "--color-primary": "#2563eb",
            "--color-success": "#059669",
            "--color-danger": "#dc2626",
            "--color-warning": "#d97706",
            "--color-info": "#0284c7",
            
            # Backgrounds
            "--bg-primary": "#ffffff",
            "--bg-secondary": "#f9fafb",
            "--bg-tertiary": "#f3f4f6",
            
            # Text
            "--text-primary": "#111827",
            "--text-secondary": "#374151",
            "--text-tertiary": "#6b7280",
            
            # Borders
            "--border-color": "#d1d5db",
            "--border-light": "#e5e7eb",
            
            # Shadows
            "--shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.05)",
            "--shadow-md": "0 4px 6px rgba(0, 0, 0, 0.1)",
            "--shadow-lg": "0 10px 15px rgba(0, 0, 0, 0.15)",
        }

    async def get_css(self) -> str:
        """Return complete CSS for light theme."""
        variables = await self.get_css_variables()
        
        # Convert dict to CSS variable declarations
        var_declarations = "\n  ".join(
            f"{key}: {value};" for key, value in variables.items()
        )
        
        css = f"""/* Light Theme */
:root {{
  {var_declarations}
}}

/* Light backgrounds for inputs and cards */
input, textarea, select {{
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border-color: var(--border-color);
}}

input:focus, textarea:focus, select:focus {{
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}}

/* Buttons */
.btn-primary {{
  background-color: var(--color-primary);
  color: white;
}}

.btn-primary:hover {{
  background-color: #1d4ed8;
}}

.btn-danger {{
  background-color: var(--color-danger);
  color: white;
}}

.btn-danger:hover {{
  background-color: #b91c1c;
}}

/* Cards and containers */
.card {{
  background-color: var(--bg-secondary);
  border-color: var(--border-color);
  color: var(--text-primary);
}}

/* Code blocks */
code, pre {{
  background-color: var(--bg-tertiary);
  color: var(--text-primary);
}}
"""
        return css
