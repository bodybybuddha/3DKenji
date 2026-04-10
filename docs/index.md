---
layout: default
title: Documentation
---

# 3DKenji Documentation

Welcome to 3DKenji – a self-hosted knowledge keeper for 3D printing projects.

## Getting Started

- **[Quick Start Guide](getting-started.md)** – Installation and setup
- **[API Reference](api-reference.md)** – Complete REST API documentation
- **[Configuration](configuration.md)** – Environment variables and settings
- **[Project Storage Architecture](project-storage-architecture.md)** – Filesystem layout, markdown formats, lifecycle
- **[Plugin Development](plugin-development.md)** – Building custom plugins

## Features

✅ **User Management** – Secure registration and JWT authentication  
✅ **Project Management** – Organize your 3D printing projects  
✅ **Filesystem-backed Projects** – Directories plus markdown project records  
✅ **Model Management** – Upload and track 3D model files  
✅ **API Keys** – Programmatic access to projects and models  
✅ **Health Monitoring** – Built-in Kubernetes readiness/liveness probes  
✅ **Observability** – Structured JSON logging for production monitoring  

## Core Concepts

### Projects
A project is a collection of related 3D models and print jobs. Create projects to organize your printing work by theme, type, or goal.

### Models  
3D model files (.stl, .3mf, .obj, .gcode) uploaded to projects. Each model has metadata including tags, custom fields, and file information.

### API Keys
Programmatic access tokens for integrations. Create keys to allow external tools to interact with your projects and models.

## Documentation Structure

```
docs/
├── index.md                      # This file
├── getting-started.md            # Installation & quick start
├── api-reference.md              # REST API documentation
├── configuration.md              # Environment & settings
├── project-storage-architecture.md # Filesystem project model
├── plugin-development.md         # Plugin development guide
└── architecture.md               # System design & architecture
```

## Quick Links

- **[Home](/)** – 3DKenji on GitHub
- **[Issues](https://github.com/yourusername/3dkenji/issues)** – Report bugs
- **[Discussions](https://github.com/yourusername/3dkenji/discussions)** – Ask questions
- **[API Docs](http://localhost:8000/docs)** – Interactive Swagger UI (when running)

## Version Info

- **Current Version**: 1.0.0
- **Release Date**: February 21, 2026
- **Status**: Production Ready ✅

---

**Made with ❤️ for the 3D printing community**
