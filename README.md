# 3DKenji

**Self-hosted knowledge keeper for 3D printing projects.**

Manage and document your 3D models, print jobs, and project artifacts with a production-ready REST API. Store project metadata in the database and filesystem artifacts in your own infrastructure.

## Features

- User and access management (local authentication + OIDC/OAuth2 support)
- Project and 3D model management with filesystem-backed artifacts
- API keys for automation and integrations
- Pluggable storage and viewer systems
- Production deployment ready (Kubernetes health checks, structured logging)
- Hybrid metadata storage (database records + markdown frontmatter)

## Quick Start

### Docker Compose (Recommended)

```bash
git clone https://github.com/bodybybuddha/3DKenji.git
cd 3dkenji
docker-compose up
```

The API runs at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Local Development

```bash
git clone https://github.com/bodybybuddha/3DKenji.git
cd 3dkenji
make install
make dev
```

### Devcontainer

Open in VS Code with the devcontainer extension for automatic setup.

## Documentation

Complete documentation is available in the `docs/` folder:

- **[Getting Started](docs/getting-started.md)** – Installation and first steps
- **[API Reference](docs/api-reference.md)** – Complete REST API documentation
- **[Configuration](docs/configuration.md)** – Environment variables and settings
- **[OAuth / OIDC Setup](docs/oauth-setup.md)** – Single sign-on configuration
- **[Project Storage Architecture](docs/project-storage-architecture.md)** – Filesystem layout and metadata
- **[Full Documentation Index](docs/index.md)** – All topics

> **Note**: This README is a landing page. See the documentation folder for detailed guides, configuration options, and API examples.

## Version

**1.0.0** – Production-stable release with OAuth, API key improvements, and filesystem-backed projects.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a working branch from `dev` using `feature/*`, `bugfix/*`, `docs/*`, or `chore/*` prefix
3. Add tests for new features
4. Run `make test` to verify
5. Submit a pull request to `dev`

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT – See [LICENSE](LICENSE) for details.

## Support

- **Documentation**: [docs/index.md](docs/index.md)
- **Issues**: [GitHub Issues](https://github.com/bodybybuddha/3DKenji/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bodybybuddha/3DKenji/discussions)
