# To dos

# Completed

  - got the basic devcontainers working
  - .gitignore is updated
  - repo is committed to git and github
  - makefile adjustments
    - the file is constantly replacing the venv.  we need to remove all that and just have an init one to create it the first time.
    - review all of the different make commands. I don't think they are all neccessary.  its getting hard to understand what the development work flow is
  - README.MD
    - need to remove the stuff about uv setup. This is done already for the basic project, so its not needed on another person's machine per se.
    - for dev work, devcontainers will take care of the venv stuff, I think.  Something to test
  - Run standard test to make sure pytest is working
    - pytest runs and contract tests pass with minimal endpoints.
  - Plugin framework (PluginManager, interfaces)
  - Data models and Alembic migrations (User, Project, Model, APIKey)

# In Progress

  - None currently

# Next Steps

**Current Branch - Final Feature Implementation:**

  - ✅ **Archive-on-Delete Feature** (COMPLETE)
    - ✅ Added `deletion_policy` field to Project model (archive/hard_delete)
    - ✅ Implemented archive logic: move to archive category instead of delete
    - ✅ Implemented hard_delete logic for permanent removal
    - ✅ Database migration (005_add_deletion_policy)
    - ✅ Tests for archive, hard_delete, and default behavior
    - ✅ ProjectDTO updated to include deletion_policy field
    - Next: Admin UI integration (defer to next branch if time constrained)

**Post-Branch (Future Work):**

  - **Admin UI for Deletion Policy**
    - Add deletion_policy setting to Admin panel
    - Allow per-project or global default configuration
    - Database schema for admin settings (if needed)

  - **Option 1**: Feature development from specs/002-plugin-architecture/
    - OAuth plugins (GitHub, Google)
    - Cloud storage backends (S3, Azure)
    - Media processors (thumbnails, previews)
    - Advanced viewer integrations
  
  - **Option 2**: Additional polish and hardening
    - Performance optimization
    - Additional security auditing
    - Enhanced observability/monitoring
    - Database optimization
  
  - **Option 3**: Production deployment preparation
    - Kubernetes manifests
    - Production environment setup
    - Deployment documentation
    - Monitoring/alerting configuration


