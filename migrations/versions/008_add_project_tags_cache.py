"""Add cached project tags column.

Revision ID: 008_add_project_tags_cache
Revises: 007_add_user_nickname
Create Date: 2026-04-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "008_add_project_tags_cache"
down_revision = "007_add_user_nickname"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    project_columns = {col["name"] for col in inspector.get_columns("projects")}

    if "tags_cache" not in project_columns:
        op.add_column("projects", sa.Column("tags_cache", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    project_columns = {col["name"] for col in inspector.get_columns("projects")}

    if "tags_cache" in project_columns:
        op.drop_column("projects", "tags_cache")
