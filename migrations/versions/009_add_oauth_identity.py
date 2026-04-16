"""Add OAuth identity support for OIDC/OAuth providers.

Revision ID: 009_add_oauth_identity
Revises: 008_add_project_tags_cache
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "009_add_oauth_identity"
down_revision = "008_add_project_tags_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # Create oauth_identities table
    if "oauth_identities" not in tables:
        op.create_table(
            "oauth_identities",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("provider", sa.String(length=64), nullable=False),
            sa.Column("provider_user_id", sa.String(length=255), nullable=False),
            sa.Column("provider_email", sa.String(length=255), nullable=True),
            sa.Column("provider_display_name", sa.String(length=255), nullable=True),
            sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_identity_provider_sub"),
        )

    # Create indexes for oauth_identities
    oauth_indexes = {idx["name"] for idx in inspector.get_indexes("oauth_identities")}
    if "ix_oauth_identities_id" not in oauth_indexes:
        op.create_index("ix_oauth_identities_id", "oauth_identities", ["id"], unique=False)
    if "ix_oauth_identities_user_id" not in oauth_indexes:
        op.create_index("ix_oauth_identities_user_id", "oauth_identities", ["user_id"], unique=False)
    if "ix_oauth_identities_provider" not in oauth_indexes:
        op.create_index("ix_oauth_identities_provider", "oauth_identities", ["provider"], unique=False)
    if "ix_oauth_identities_provider_user_id" not in oauth_indexes:
        op.create_index(
            "ix_oauth_identities_provider_user_id",
            "oauth_identities",
            ["provider", "provider_user_id"],
            unique=False,
        )

    # Alter users.password_hash to be nullable (for OIDC-only accounts)
    user_columns = [col for col in inspector.get_columns("users")]
    password_hash_col = next((col for col in user_columns if col["name"] == "password_hash"), None)
    if password_hash_col and not password_hash_col.get("nullable", False):
        op.alter_column("users", "password_hash", nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Revert users.password_hash to non-nullable
    # First set a temporary default for any null values to avoid constraint violation
    user_columns = [col for col in inspector.get_columns("users")]
    password_hash_col = next((col for col in user_columns if col["name"] == "password_hash"), None)
    if password_hash_col and password_hash_col.get("nullable", True):
        # Update any NULL password_hash values to empty string before making it non-nullable
        bind.execute(sa.text("UPDATE users SET password_hash = '' WHERE password_hash IS NULL"))
        op.alter_column("users", "password_hash", nullable=False, server_default="")
        # Remove the server_default after the column is non-nullable
        op.alter_column("users", "password_hash", server_default=None)

    # Drop oauth_identities indexes
    oauth_indexes = {idx["name"] for idx in inspector.get_indexes("oauth_identities")}
    if "ix_oauth_identities_provider_user_id" in oauth_indexes:
        op.drop_index("ix_oauth_identities_provider_user_id", table_name="oauth_identities")
    if "ix_oauth_identities_provider" in oauth_indexes:
        op.drop_index("ix_oauth_identities_provider", table_name="oauth_identities")
    if "ix_oauth_identities_user_id" in oauth_indexes:
        op.drop_index("ix_oauth_identities_user_id", table_name="oauth_identities")
    if "ix_oauth_identities_id" in oauth_indexes:
        op.drop_index("ix_oauth_identities_id", table_name="oauth_identities")

    # Drop oauth_identities table
    tables = set(inspector.get_table_names())
    if "oauth_identities" in tables:
        op.drop_table("oauth_identities")
