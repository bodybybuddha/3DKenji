"""Add app_settings table for admin-configurable file policy

Revision ID: 003_add_app_settings
Revises: 002_add_admin_flags
Create Date: 2026-04-09

"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003_add_app_settings"
down_revision = "002_add_admin_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_app_settings_id", "app_settings", ["id"])
    op.create_index("ix_app_settings_key", "app_settings", ["key"])
    op.create_index("ix_app_settings_updated_by", "app_settings", ["updated_by"])

    # Seed default file policy settings so upload/listing behavior is deterministic.
    now = datetime.utcnow()
    settings_table = sa.table(
        "app_settings",
        sa.column("id", sa.String(36)),
        sa.column("key", sa.String(128)),
        sa.column("value_json", sa.JSON()),
        sa.column("updated_by", sa.String(36)),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    op.bulk_insert(
        settings_table,
        [
            {
                "id": "d7e6b73b-5f7f-4d06-8f2d-a1b8089e8a01",
                "key": "file_policy.allowed_extensions",
                "value_json": [
                    "stl",
                    "3mf",
                    "obj",
                    "step",
                    "stp",
                    "f3d",
                    "f3z",
                    "fcstd",
                    "fcbak",
                    "scad",
                    "blend",
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                    "gif",
                    "mp4",
                    "mkv",
                    "avi",
                    "md",
                    "txt",
                    "pdf",
                ],
                "updated_by": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "8ad4a7ce-4ed8-4069-8b6b-1ca285f4e702",
                "key": "file_policy.hidden_name_patterns",
                "value_json": [".DS_Store", "Thumbs.db", "desktop.ini", "._*", "*.tmp"],
                "updated_by": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "4f2fd4d2-a529-4b5a-8598-93c8505d3f03",
                "key": "file_policy.max_upload_size_mb",
                "value_json": 100,
                "updated_by": None,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_app_settings_updated_by", table_name="app_settings")
    op.drop_index("ix_app_settings_key", table_name="app_settings")
    op.drop_index("ix_app_settings_id", table_name="app_settings")
    op.drop_table("app_settings")
