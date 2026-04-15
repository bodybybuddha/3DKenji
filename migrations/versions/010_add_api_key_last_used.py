"""Add last_used_at column to api_keys table.

Revision ID: 010_add_api_key_last_used
Revises: 009_add_oauth_identity
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "010_add_api_key_last_used"
down_revision = "009_add_oauth_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    api_key_columns = {col["name"] for col in inspector.get_columns("api_keys")}

    if "last_used_at" not in api_key_columns:
        op.add_column(
            "api_keys",
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    api_key_columns = {col["name"] for col in inspector.get_columns("api_keys")}

    if "last_used_at" in api_key_columns:
        op.drop_column("api_keys", "last_used_at")
