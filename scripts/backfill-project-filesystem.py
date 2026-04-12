#!/usr/bin/env python3
"""Migrate/backfill project filesystem artifacts for owner-based storage.

This script updates project directories to the owner-based layout:
    Projects/<owner_nickname>/<slug>

It also backfills seed files and upgrades frontmatter if missing/outdated.

Usage:
    source /workspace/.venv/bin/activate
    DATABASE_URL='postgresql://kenji:kenji@localhost:5432/kenji' \
        python scripts/backfill-project-filesystem.py --dry-run

    DATABASE_URL='postgresql://kenji:kenji@localhost:5432/kenji' \
        python scripts/backfill-project-filesystem.py --apply
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db import get_engine
from backend.models.project import Project
from backend.models.user import User
from backend.services.project_directory import service_for_project, get_projects_dir
from backend.services.markdown_service import (
    ensure_project_info_frontmatter,
    ensure_print_history_frontmatter,
)


def _candidate_paths(storage_root: Path, projects_root: Path, project: Project) -> list[Path]:
    """Build legacy path candidates for an existing project."""
    candidates: list[Path] = []

    if project.directory_path:
        dir_path = str(project.directory_path).strip("/")
        candidates.append(storage_root / dir_path)
        if dir_path.startswith("Projects/"):
            candidates.append(storage_root / ("projects/" + dir_path[len("Projects/") :]))
        if dir_path.startswith("projects/"):
            candidates.append(storage_root / ("Projects/" + dir_path[len("projects/") :]))

    candidates.append(projects_root / str(project.category) / str(project.slug))
    candidates.append(projects_root / str(project.owner_id) / str(project.slug))
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate/backfill project filesystem layout")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply filesystem/database changes")
    mode.add_argument("--dry-run", action="store_true", help="Show planned changes without applying")
    args = parser.parse_args()

    apply_changes = bool(args.apply)
    if not args.apply and not args.dry_run:
        # Safety default
        apply_changes = False

    engine = get_engine()
    projects_root = get_projects_dir()
    storage_root = projects_root.parent

    moved_dirs = 0
    move_conflicts = 0
    created_dirs = 0
    created_info = 0
    upgraded_frontmatter = 0
    upgraded_print_history = 0
    repaired_paths = 0
    total = 0

    with Session(engine) as session:
        user_nickname_map = {
            user.id: (user.nickname or user.id)
            for user in session.execute(select(User)).scalars().all()
        }
        projects = session.execute(select(Project)).scalars().all()
        total = len(projects)

        for project in projects:
            owner_segment = str(user_nickname_map.get(project.owner_id, project.owner_id))
            expected_rel_path = f"Projects/{owner_segment}/{project.slug}"
            expected_abs_path = projects_root / owner_segment / str(project.slug)

            selected_source: Path | None = None
            for candidate in _candidate_paths(storage_root, projects_root, project):
                if candidate.exists() and candidate != expected_abs_path:
                    selected_source = candidate
                    break

            if not expected_abs_path.exists() and selected_source and selected_source.exists():
                if apply_changes:
                    expected_abs_path.parent.mkdir(parents=True, exist_ok=True)
                    if expected_abs_path.exists():
                        move_conflicts += 1
                    else:
                        shutil.move(str(selected_source), str(expected_abs_path))
                        moved_dirs += 1
                else:
                    moved_dirs += 1

            if project.directory_path != expected_rel_path:
                project.directory_path = expected_rel_path
                repaired_paths += 1

            svc = service_for_project(
                owner_segment,
                str(project.slug),
                legacy_segment=str(project.category),
            )
            dir_exists_before = svc.project_directory_exists()
            info_exists_before = (svc._root / "ProjectInfo.md").exists()

            # Idempotent: only creates missing directories/files.
            if apply_changes:
                svc.create_project_directory(title=str(project.title), description="")

            if not dir_exists_before and (apply_changes and svc.project_directory_exists()):
                created_dirs += 1
            if not info_exists_before and (apply_changes and (svc._root / "ProjectInfo.md").exists()):
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
                    if apply_changes:
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
                    if apply_changes:
                        history_path.write_text(upgraded, encoding="utf-8")
                    upgraded_print_history += 1

        if apply_changes and repaired_paths > 0:
            session.commit()

    print(f"Mode: {'apply' if apply_changes else 'dry-run'}")
    print(f"Projects scanned: {total}")
    print(f"Directories moved to owner layout: {moved_dirs}")
    print(f"Move conflicts: {move_conflicts}")
    print(f"Directories created: {created_dirs}")
    print(f"ProjectInfo.md created: {created_info}")
    print(f"ProjectInfo.md frontmatter upgraded: {upgraded_frontmatter}")
    print(f"PrintHistory.md frontmatter upgraded: {upgraded_print_history}")
    print(f"directory_path repaired: {repaired_paths}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
