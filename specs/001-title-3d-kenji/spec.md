# Feature Specification: 3D Kenji Core: Projects & Models

**Feature Branch**: `001-title-3d-kenji`  
**Created**: 2025-09-07  
**Status**: Draft  
**Input**: User description: "3D Kenji is an open source, self-hosted knowledge keeper for 3D printing projects. It helps you track 3d models, print jobs, settings, filaments used, and media like timelapses and pictures. Also, there should be a note taking via markdown files for tracking other aspects of the printing project. The concept is to provide a web-front end to what a person would use a complex directory structure for to track their 3d projects. It's basically Notion, file explorer, file previewer, file editor, octoprint (future features). This is an API-first project that will allow for multiple users - authentication can be done with a username/password, or oAuth (providers can be interchangable - github, google being the primary two.). In addition, the users can create API keys to have different scopes of capabilities to their projects. All projects will have security where the owner can have full access to all features of their project and can grant other users different scopes (default: no access, other roles: reader, contributor, other future role). The front end will be initally a web ui with Jinja2 (flask) - but as the web app will be api first, this can change for different implementations. The project will be containerize so that the front and backend can be spun up with minimum setup - just port, and persistent configuration/data location. In addition all development should be done via devcontiners. The backend database should be postres with jsonB to help with flexibilty of future features. All new version/modifications will have need an upgrade path for the database - possibly use a database migration tool. The basic structure will be a project. That project can contain one or more 3d model files (*.3mf, *.stl, etc.) for each model in the project. Each model will have basic information on the model, where the model was downloaded from if appropriate, tag support for the model for categorization, 3d print history, and any time lapse of the 3d print. The model should have a 3d viewer so users can see a 3d model rendering. if pictures are included with the proejct information, a key picture can be used for a thumbnail to represent the project or model, or both. Otherwise a render of the 3d file should be used. If no 3d file or picture is available a generic image can be used. Templates for needed information for projects, eg title, tag, description,etc, can be defined by admins. The templates can be used for other features in the future."

## Execution Flow (main)
```
1. User/agent requests create or read operations via API or UI
2. Backend authorizes request (user session or API key)
3. Validate input and store metadata; persist files/media to storage
4. Return API response (resource representation) or stream media
5. Admin operations manage users, roles, API keys, and templates
```

---

## ⚡ Quick Guidelines
- Focus: Let users create and manage Projects containing Models, Media, Print History, and Notes.
- Expose every meaningful action via a machine-readable API (OpenAPI). UI is a convenience layer built on the same API.
- Mark implementation decisions that remain open with [NEEDS CLARIFICATION: ...].

### Section Requirements
- Mandatory sections below completed. Ambiguities are marked explicitly.

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a 3D printing hobbyist, I want to create a Project, add 3D model files and media, track print jobs and notes, and optionally grant other people or services scoped access to my project so I can collaborate and automate workflows.

### Acceptance Scenarios
1. Given an authenticated user, when they POST /api/v1/projects with valid attributes, then the system creates a project owned by that user and returns 201 with the project resource.
2. Given a project owner, when they upload a model file to POST /api/v1/projects/{id}/models, then the model metadata is stored and file is accessible by URL with appropriate permissions.
3. Given a collaborator with "reader" role, when they GET project resources, they receive read-only representations and cannot modify project state.
4. Given an API key with scopes [read], when used to access GET endpoints on a project it is authorized for, then requests succeed only for allowed operations.
5. Given a missing thumbnail and an available 3D model, when requesting a project thumbnail, then the system returns a rendered preview or a generic placeholder if render not available.
6. Given an API key with scopes [timelapse], upload up to a 50mb video file to a project's model.
7. Given a collaborator with "GlobalAdmin" role, they have the ability to change all application configurations and will have access to all data.

### Edge Cases
- Uploading very large model files up to 10mb for *.3mf and *.stl files
- Concurrent edits to a project by multiple users
- Revoked API key used in-flight
- Missing or corrupted model file for viewer rendering

---

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The system MUST allow users to create, read, update, and delete Projects via API endpoints.
- **FR-002**: The system MUST allow users to add Models to a Project, where each Model has metadata: id, project_id, filename, optional source_url, tags, human-friendly title, and arbitrary metadata.
- **FR-003**: The system MUST allow attaching Media (images, timelapses, videos) to Projects and Models and expose accessible URLs when authorized.
- **FR-004**: The system MUST support Notes stored as Markdown files attached to a Project or Models and allow CRUD operations over the API.
- **FR-005**: The system MUST support user accounts and authentication via username/password and external OAuth providers (e.g., GitHub, Google).
- **FR-006**: The system MUST allow users to create scoped API keys that can be issued, listed, revoked, and scoped to project(s) and permission levels.
- **FR-007**: The system MUST enforce per-resource authorization: project owner has full permissions; other users must be granted explicit roles (none, reader, contributor, admin).
- **FR-008**: The system MUST expose an administrative API for managing templates and user roles.
- **FR-009**: The system MUST record print job history for Models with timestamped entries and be able to query by model and project.
- **FR-010**: The system MUST expose an OpenAPI specification reflecting public endpoints and authentication methods.
- **FR-011**: The system MUST surface structured logs for security events and errors; logs should be configurable to chosen sinks (default: files with rotation).

*Marked ambiguities / decisions to confirm*
- **FR-012**: Allowed file types for Models: .stl, .3mf, .obj, .gcode
- **FR-013**: Maximum file size and storage lifecycle: configurable by file type.
- **FR-014**: Exact API key scope model (string scopes, RBAC roles, or resource-scoped permissions): GlobalAdmin - for administrators of the website, project-based: admin (read/write data, user accessibility, read/write project configuration information), contributor (read/write data), reader (read data)

### Non-functional Requirements
- **NFR-001**: The system MUST be deployable as containers; local development MUST support VS Code devcontainers.
- **NFR-002**: Persistent data must be durable across container restarts and upgrades.
- **NFR-003**: Releases MUST follow semantic versioning; breaking API changes must include migration guides and depreciation windows.
- **NFR-004**: The system SHOULD default to PostgreSQL for durable storage and allow flexible metadata storage for models and projects (logical JSON fields).
- **NFR-005**: The system SHOULD provide reasonable default observability (structured logs, request tracing hooks) and allow configuration to swap sinks.

---

## Key Entities *(include if feature involves data)*
- **User**: id, username, email, display_name, role(s), created_at
- **Project**: id, title, owner_id (User), description, metadata (opaque JSON), created_at, updated_at
- **Model**: id, project_id, filename, source_url, tags[], metadata (opaque JSON), thumbnail_url, uploaded_by, created_at
- **Media**: id, model_id|project_id, type (image/video/timelapse), url, metadata
- **PrintJob**: id, model_id, project_id, user_id, start_at, end_at, status, settings (opaque JSON)
- **APIKey**: id, owner_id, key_identifier, hashed_key, scopes[], expires_at, revoked_flag
- **Template**: id, name, schema_definition (structured JSON), created_by

Data shapes above are logical; implementation storage (Postgres JSONB, file store) belongs in the implementation plan and migrations.

---

## Review & Acceptance Checklist

- [ ] User scenarios are clear and testable
- [ ] All functional requirements are measurable
- [ ] Ambiguities resolved (see [NEEDS CLARIFICATION] markers)
- [ ] OpenAPI contract created and reviewed
- [ ] Migration plan for DB changes included in implementation PR
- [ ] CI runs unit and contract tests for these behaviors

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [ ] User scenarios defined (in progress — see acceptance scenarios)
- [ ] Requirements finalized (pending clarifications above)
- [ ] Entities identified
- [ ] Review checklist ready

---

NOTES / NEXT ACTIONS
- Resolve [NEEDS CLARIFICATION] items (file size, allowed file types, API key scope model, storage for binary media).
- Produce an OpenAPI draft (paths, operations, security schemes) that matches these FRs.
- Create migration plan for storage model and file/media handling.

