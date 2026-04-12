"""Add project visibility, collaborators, and invitations.

Revision ID: 006_project_access_controls
Revises: 005_add_deletion_policy
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "006_project_access_controls"
down_revision = "005_add_deletion_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    project_columns = {col["name"] for col in inspector.get_columns("projects")}
    if "visibility" not in project_columns:
        op.add_column(
            "projects",
            sa.Column("visibility", sa.String(length=20), nullable=False, server_default="private"),
        )

    project_indexes = {idx["name"] for idx in inspector.get_indexes("projects")}
    if "ix_projects_visibility" not in project_indexes:
        op.create_index("ix_projects_visibility", "projects", ["visibility"], unique=False)

    tables = set(inspector.get_table_names())
    if "project_collaborators" not in tables:
        op.create_table(
            "project_collaborators",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
            sa.Column("granted_by_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["granted_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("project_id", "user_id", name="uq_project_collaborator_project_user"),
        )

    collaborator_indexes = {idx["name"] for idx in inspector.get_indexes("project_collaborators")}
    if "ix_project_collaborators_id" not in collaborator_indexes:
        op.create_index("ix_project_collaborators_id", "project_collaborators", ["id"], unique=False)
    if "ix_project_collaborators_project_id" not in collaborator_indexes:
        op.create_index(
            "ix_project_collaborators_project_id",
            "project_collaborators",
            ["project_id"],
            unique=False,
        )
    if "ix_project_collaborators_user_id" not in collaborator_indexes:
        op.create_index(
            "ix_project_collaborators_user_id",
            "project_collaborators",
            ["user_id"],
            unique=False,
        )

    if "project_invitations" not in tables:
        op.create_table(
            "project_invitations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("invited_email", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("invited_by_id", sa.String(length=36), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("accepted_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    invitation_indexes = {idx["name"] for idx in inspector.get_indexes("project_invitations")}
    if "ix_project_invitations_id" not in invitation_indexes:
        op.create_index("ix_project_invitations_id", "project_invitations", ["id"], unique=False)
    if "ix_project_invitations_invited_email" not in invitation_indexes:
        op.create_index(
            "ix_project_invitations_invited_email",
            "project_invitations",
            ["invited_email"],
            unique=False,
        )
    if "ix_project_invitations_project_id" not in invitation_indexes:
        op.create_index(
            "ix_project_invitations_project_id",
            "project_invitations",
            ["project_id"],
            unique=False,
        )
    if "ix_project_invitations_token_hash" not in invitation_indexes:
        op.create_index(
            "ix_project_invitations_token_hash",
            "project_invitations",
            ["token_hash"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("ix_project_invitations_token_hash", table_name="project_invitations")
    op.drop_index("ix_project_invitations_project_id", table_name="project_invitations")
    op.drop_index("ix_project_invitations_invited_email", table_name="project_invitations")
    op.drop_index("ix_project_invitations_id", table_name="project_invitations")
    op.drop_table("project_invitations")

    op.drop_index("ix_project_collaborators_user_id", table_name="project_collaborators")
    op.drop_index("ix_project_collaborators_project_id", table_name="project_collaborators")
    op.drop_index("ix_project_collaborators_id", table_name="project_collaborators")
    op.drop_table("project_collaborators")

    op.drop_index("ix_projects_visibility", table_name="projects")
    op.drop_column("projects", "visibility")