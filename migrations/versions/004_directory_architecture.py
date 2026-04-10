"""Directory-based project storage architecture

Adds slug, category, directory_path, disk_size_bytes, is_archived to projects.
Removes description and custom_metadata from projects.
Drops the models table (files are now managed on disk).

Revision ID: 004_directory_architecture
Revises: 003_add_app_settings
Create Date: 2026-04-10

"""

import re
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = "004_directory_architecture"
down_revision = "003_add_app_settings"
branch_labels = None
depends_on = None


def _slugify(title: str) -> str:
    """Derive a filesystem-safe slug from a project title.

    Rules (per spec §2.3):
    - Lowercase, alphanumeric and hyphens only
    - Spaces (and other non-alphanumeric chars) replaced with hyphens
    - Consecutive hyphens collapsed
    - Maximum 64 characters
    """
    slug = title.lower()
    # Replace any non-alphanumeric character with a hyphen
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Collapse consecutive hyphens
    slug = re.sub(r"-{2,}", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")
    # Enforce 64-char maximum
    slug = slug[:64].rstrip("-")
    return slug or "project"


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Add new columns to projects (all nullable/with default initially  #
    #    so existing rows can be populated before adding NOT NULL)          #
    # ------------------------------------------------------------------ #
    op.add_column("projects", sa.Column("slug", sa.String(64), nullable=True))
    op.add_column(
        "projects",
        sa.Column("category", sa.String(255), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("directory_path", sa.String(1024), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("disk_size_bytes", sa.BigInteger(), nullable=True, server_default="0"),
    )
    op.add_column(
        "projects",
        sa.Column("is_archived", sa.Boolean(), nullable=True, server_default="false"),
    )

    # ------------------------------------------------------------------ #
    # 2. Data migration: compute slug, category, and directory_path for   #
    #    all existing project rows.                                        #
    # ------------------------------------------------------------------ #
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id, title FROM projects")).fetchall()

    # Track (owner_id resolved below) - we just need slug uniqueness across
    # the whole table for the data migration (category is Uncategorized for all).
    seen_slugs: dict[str, set[str]] = {}

    for row in rows:
        project_id = row[0]
        title = row[1] or "project"

        base_slug = _slugify(title)
        owner_row = conn.execute(
            text("SELECT owner_id FROM projects WHERE id = :id"),
            {"id": project_id},
        ).fetchone()
        owner_id = owner_row[0] if owner_row else "unknown"

        # Ensure slug uniqueness per owner within Uncategorized
        key = f"{owner_id}:Uncategorized"
        if key not in seen_slugs:
            seen_slugs[key] = set()

        slug = base_slug
        suffix = 1
        while slug in seen_slugs[key]:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        seen_slugs[key].add(slug)

        directory_path = f"Projects/Uncategorized/{slug}"

        conn.execute(
            text(
                "UPDATE projects SET slug = :slug, category = :category, "
                "directory_path = :dir_path WHERE id = :id"
            ),
            {
                "slug": slug,
                "category": "Uncategorized",
                "dir_path": directory_path,
                "id": project_id,
            },
        )

    # ------------------------------------------------------------------ #
    # 3. Apply NOT NULL constraints now that rows are populated.           #
    # ------------------------------------------------------------------ #
    op.alter_column("projects", "slug", nullable=False)
    op.alter_column("projects", "category", nullable=False)
    op.alter_column("projects", "is_archived", nullable=False)

    # ------------------------------------------------------------------ #
    # 4. Create unique constraint and indexes.                             #
    # ------------------------------------------------------------------ #
    op.create_unique_constraint(
        "uq_project_owner_category_slug",
        "projects",
        ["owner_id", "category", "slug"],
    )
    op.create_index("ix_projects_owner_category", "projects", ["owner_id", "category"])
    op.create_index("ix_projects_is_archived", "projects", ["is_archived"])

    # ------------------------------------------------------------------ #
    # 5. Drop removed columns from projects.                              #
    # ------------------------------------------------------------------ #
    op.drop_column("projects", "description")
    op.drop_column("projects", "custom_metadata")

    # ------------------------------------------------------------------ #
    # 6. Drop the models table (files are now managed on disk).           #
    # ------------------------------------------------------------------ #
    op.drop_table("models")


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # Reverse: recreate models table, restore projects columns.           #
    # ------------------------------------------------------------------ #

    # Recreate models table
    op.create_table(
        "models",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("uploaded_by_id", sa.String(36), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("custom_metadata", sa.JSON(), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_models_storage_key", "models", ["storage_key"])
    op.create_index("ix_models_project_id", "models", ["project_id"])
    op.create_index("ix_models_id", "models", ["id"])

    # Restore projects columns
    op.add_column("projects", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "projects",
        sa.Column("custom_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )

    # Remove new columns
    op.drop_index("ix_projects_is_archived", table_name="projects")
    op.drop_index("ix_projects_owner_category", table_name="projects")
    op.drop_constraint("uq_project_owner_category_slug", "projects", type_="unique")
    op.drop_column("projects", "is_archived")
    op.drop_column("projects", "disk_size_bytes")
    op.drop_column("projects", "directory_path")
    op.drop_column("projects", "category")
    op.drop_column("projects", "slug")
