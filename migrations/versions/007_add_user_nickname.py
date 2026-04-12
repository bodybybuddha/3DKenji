"""Add user nickname for human-readable storage ownership.

Revision ID: 007_add_user_nickname
Revises: 006_project_access_controls
Create Date: 2026-04-12
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "007_add_user_nickname"
down_revision = "006_project_access_controls"
branch_labels = None
depends_on = None


def _normalize_nickname(value: str) -> str:
    nickname = (value or "").strip().lower()
    nickname = re.sub(r"[^a-z0-9_-]+", "-", nickname)
    nickname = re.sub(r"-{2,}", "-", nickname).strip("-_")
    nickname = nickname[:64].rstrip("-_")
    if len(nickname) < 3:
        nickname = "user"
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", nickname):
        nickname = "user"
    return nickname


def _backfill_nicknames(bind) -> None:
    users_table = sa.table(
        "users",
        sa.column("id", sa.String(length=36)),
        sa.column("username", sa.String(length=255)),
        sa.column("nickname", sa.String(length=64)),
    )

    rows = bind.execute(
        sa.select(users_table.c.id, users_table.c.username, users_table.c.nickname).order_by(users_table.c.id.asc())
    ).fetchall()

    assigned: set[str] = set()

    for row in rows:
        existing_nickname = row.nickname
        if existing_nickname:
            assigned.add(str(existing_nickname).lower())

    for row in rows:
        if row.nickname:
            continue

        base = _normalize_nickname(str(row.username or ""))
        candidate = base
        suffix = 1

        while candidate.lower() in assigned:
            suffix += 1
            token = f"-{suffix}"
            trimmed = base[: max(1, 64 - len(token))].rstrip("-_") or "user"
            candidate = f"{trimmed}{token}"

        bind.execute(
            users_table.update().where(users_table.c.id == row.id).values(nickname=candidate)
        )
        assigned.add(candidate.lower())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    if "nickname" not in user_columns:
        op.add_column("users", sa.Column("nickname", sa.String(length=64), nullable=True))

    _backfill_nicknames(bind)

    user_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
    if "ix_users_nickname" not in user_indexes:
        op.create_index("ix_users_nickname", "users", ["nickname"], unique=True)

    op.alter_column("users", "nickname", existing_type=sa.String(length=64), nullable=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {col["name"] for col in inspector.get_columns("users")}
    user_indexes = {idx["name"] for idx in inspector.get_indexes("users")}

    if "ix_users_nickname" in user_indexes:
        op.drop_index("ix_users_nickname", table_name="users")

    if "nickname" in user_columns:
        op.drop_column("users", "nickname")
