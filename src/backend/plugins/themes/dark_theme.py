"""Dark theme plugin - Default theme with dark background."""

from fastapi import FastAPI

from backend.core.plugin_interfaces import ThemePlugin


class DarkTheme(ThemePlugin):
    """Dark theme with gray backgrounds and light text."""

    name = "DarkTheme"
    version = "1.0.0"
    author = "3DKenji"
    theme_name = "dark"
    is_default = True

    async def register(self, app: FastAPI, config: dict) -> None:
        """Register theme with FastAPI (no routes needed)."""
        pass

    async def health_check(self) -> dict:
        """Return theme health status."""
        return {"status": "healthy", "theme": self.theme_name}

    async def get_css_variables(self) -> dict[str, str]:
        """Return CSS variables for dark theme."""
        return {
            # Semantic Colors
            "--color-primary": "#3b82f6",
            "--color-success": "#10b981",
            "--color-danger": "#ef4444",
            "--color-warning": "#f59e0b",
            "--color-info": "#0ea5e9",
            
            # Backgrounds
            "--bg-primary": "#1f2937",
            "--bg-secondary": "#111827",
            "--bg-tertiary": "#374151",
            
            # Text
            "--text-primary": "#f3f4f6",
            "--text-secondary": "#d1d5db",
            "--text-tertiary": "#9ca3af",
            
            # Borders
            "--border-color": "#4b5563",
            "--border-light": "#6b7280",
            
            # Shadows
            "--shadow-sm": "0 1px 2px rgba(0, 0, 0, 0.3)",
            "--shadow-md": "0 4px 6px rgba(0, 0, 0, 0.4)",
            "--shadow-lg": "0 10px 15px rgba(0, 0, 0, 0.5)",
        }

    async def get_css(self) -> str:
        """Return complete CSS for dark theme."""
        variables = await self.get_css_variables()
        
        # Convert dict to CSS variable declarations
        var_declarations = "\n  ".join(
            f"{key}: {value};" for key, value in variables.items()
        )
        
        css = f"""/* Dark Theme */
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
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}}

/* Buttons */
.btn-primary {{
  background-color: var(--color-primary);
  color: white;
}}

.btn-primary:hover {{
  background-color: #2563eb;
}}

.btn-danger {{
  background-color: var(--color-danger);
  color: white;
}}

.btn-danger:hover {{
  background-color: #dc2626;
}}

/* Cards and containers */
.card {{
  background-color: var(--bg-secondary);
  border-color: var(--border-color);
  color: var(--text-primary);
}}

/* Code blocks */
code, pre {{
  background-color: var(--bg-secondary);
  color: var(--text-primary);
}}
"""
        return css
