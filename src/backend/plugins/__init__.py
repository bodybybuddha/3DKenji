"""Built-in and custom plugins for 3D Kenji.

Plugins are discovered from this directory at startup. Each plugin module
should contain at least one subclass of a plugin interface (e.g., AuthProvider,
StorageBackend) and define it as a module-level class.

Example plugin structure:

    class MyAuthProvider(AuthProvider):
        name = "my-auth"
        version = "1.0.0"
        author = "Your Name"
        auth_type = "custom"

        async def register(self, app, config):
            # Register routes with FastAPI app
            pass

        async def authenticate(self, credentials):
            # Implement auth logic
            pass

        async def get_login_url(self, state, redirect_uri):
            # Return None for password-based auth
            return None

        async def validate_token(self, token):
            # Validate and return user identity
            pass

        async def health_check(self):
            return {"status": "ok"}
"""
