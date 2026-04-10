#!/usr/bin/env python3
"""Backfill filesystem artifacts for existing projects.

Creates project directories and seed files (ProjectInfo.md, PrintHistory.md)
for projects that already exist in the database.

Usage:
  source /workspace/.venv/bin/activate
  DATABASE_URL='postgresql://kenji:kenji@localhost:5432/kenji' python scripts/backfill-project-filesystem.py
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import get_engine
from backend.models.project import Project
from backend.services.project_directory import service_for_project
from backend.services.markdown_service import (
    ensure_project_info_frontmatter,
    ensure_print_history_frontmatter,
)


def main() -> int:
    engine = get_engine()

    created_dirs = 0
    created_info = 0
    upgraded_frontmatter = 0
    upgraded_print_history = 0
    repaired_paths = 0
    total = 0

    with Session(engine) as session:
        projects = session.execute(select(Project)).scalars().all()
        total = len(projects)

        for project in projects:
            expected_rel_path = f"Projects/{project.category}/{project.slug}"
            if project.directory_path != expected_rel_path:
                project.directory_path = expected_rel_path
                repaired_paths += 1

            svc = service_for_project(str(project.category), str(project.slug))
            dir_exists_before = svc.project_directory_exists()
            info_exists_before = (svc._root / "ProjectInfo.md").exists()

            # Idempotent: only creates missing directories/files.
            svc.create_project_directory(title=str(project.title), description="")

            if not dir_exists_before and svc.project_directory_exists():
                created_dirs += 1
            if not info_exists_before and (svc._root / "ProjectInfo.md").exists():
                created_info += 1

            # Upgrade ProjectInfo.md frontmatter
            info_path = svc._root / "ProjectInfo.md"
            if info_path.exists():
                original = info_path.read_text(encoding="utf-8")
                upgraded = ensure_project_info_frontmatter(
                    original,
                    title=str(project.title),
                )
                if upgraded != original:
                    info_path.write_text(upgraded, encoding="utf-8")
                    upgraded_frontmatter += 1

            # Upgrade PrintHistory.md frontmatter
            history_path = svc._root / "PrintHistory.md"
            if history_path.exists():
                original = history_path.read_text(encoding="utf-8")
                upgraded = ensure_print_history_frontmatter(
                    original,
                    title=str(project.title),
                )
                if upgraded != original:
                    history_path.write_text(upgraded, encoding="utf-8")
                    upgraded_print_history += 1

        if repaired_paths > 0:
            session.commit()

    print(f"Projects scanned: {total}")
    print(f"Directories created: {created_dirs}")
    print(f"ProjectInfo.md created: {created_info}")
    print(f"ProjectInfo.md frontmatter upgraded: {upgraded_frontmatter}")
    print(f"PrintHistory.md frontmatter upgraded: {upgraded_print_history}")
    print(f"directory_path repaired: {repaired_paths}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
