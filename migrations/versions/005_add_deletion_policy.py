"""Add deletion_policy to projects for configurable archive vs hard_delete behavior

Revision ID: 005_add_deletion_policy
Revises: 004_directory_architecture
Create Date: 2026-04-10

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "005_add_deletion_policy"
down_revision = "004_directory_architecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add deletion_policy column with default 'archive'
    op.add_column(
        "projects",
        sa.Column(
            "deletion_policy",
            sa.String(50),
            nullable=False,
            server_default="archive",
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "deletion_policy")
