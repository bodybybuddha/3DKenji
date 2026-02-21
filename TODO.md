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

  - MVP Core Implementation (Services layer next)
    - See specs/001-title-3d-kenji/tasks.md for detailed progress
    - Just completed: Plugin framework (T015-T016), Data models (T017-T020)
    - Next: Services (T021-T023), Auth middleware (T024), Password auth plugin (T025)

Once MVP is complete (projects + models + password auth), we can iterate on additional features (OAuth, timelapse, extended UI).


