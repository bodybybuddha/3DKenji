"""Migration safety tests for migration 004_directory_architecture.

These tests verify that migration 004 upgrades forward correctly on both
a fresh (empty) database and a seeded database that has pre-existing project rows.

Tests REQUIRE a live PostgreSQL instance.  Set the TEST_PG_URL environment
variable (default: postgresql://kenji:kenji@localhost:5432/kenji_test).
"""

import os
import re
import uuid
from datetime import datetime

import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_PG_URL = os.environ.get(
    "TEST_PG_URL", "postgresql://kenji:kenji@localhost:5432/kenji_test"
)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def _make_alembic_cfg(url: str) -> Config:
    """Build an Alembic Config object pointing at our migrations."""
    cfg = Config(os.path.join(WORKSPACE_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(WORKSPACE_ROOT, "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _run_alembic(url: str, revision: str) -> None:
    """Run alembic upgrade while ensuring DATABASE_URL points to *url*.

    The migrations/env.py reads DATABASE_URL from the environment, which
    conftest.py overrides to a SQLite URL.  We temporarily patch the env var
    for the duration of each alembic call to fix this.
    """
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        cfg = _make_alembic_cfg(url)
        alembic_command.upgrade(cfg, revision)
    finally:
        if old is not None:
            os.environ["DATABASE_URL"] = old
        else:
            os.environ.pop("DATABASE_URL", None)


def _reset_db(engine) -> None:
    """Drop and recreate the public schema to start with a clean slate."""
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()


def _slugify(title: str) -> str:
    """Mirror the slugify logic in the migration (for assertion comparisons)."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    slug = slug[:64].rstrip("-")
    return slug or "project"


# ---------------------------------------------------------------------------
# Fixture: shared engine + reset between tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pg_engine():
    engine = create_engine(TEST_PG_URL, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect():
            pass
    except Exception as exc:
        engine.dispose()
        pytest.skip(f"Postgres not available for migration tests at {TEST_PG_URL}: {exc}")
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_db(pg_engine):
    """Reset the database before every test so each test gets a clean slate."""
    _reset_db(pg_engine)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMigration004FreshDB:
    """Verify migration 004 runs cleanly on an empty database."""

    @pytest.mark.integration
    def test_upgrade_head_on_fresh_db(self, pg_engine):
        """All migrations from scratch must succeed on an empty database."""
        _run_alembic(TEST_PG_URL, "head")

        inspector = inspect(pg_engine)
        tables = inspector.get_table_names()

        # Expected tables after full migration
        assert "projects" in tables
        assert "users" in tables
        assert "api_keys" in tables
        assert "app_settings" in tables
        # models table must be gone
        assert "models" not in tables

    @pytest.mark.integration
    def test_projects_table_has_new_columns(self, pg_engine):
        """Projects table must have the new directory-storage columns."""
        _run_alembic(TEST_PG_URL, "head")

        inspector = inspect(pg_engine)
        cols = {c["name"] for c in inspector.get_columns("projects")}

        assert "slug" in cols
        assert "category" in cols
        assert "directory_path" in cols
        assert "disk_size_bytes" in cols
        assert "is_archived" in cols

    @pytest.mark.integration
    def test_projects_table_old_columns_removed(self, pg_engine):
        """description and custom_metadata must no longer be present."""
        _run_alembic(TEST_PG_URL, "head")

        inspector = inspect(pg_engine)
        cols = {c["name"] for c in inspector.get_columns("projects")}

        assert "description" not in cols
        assert "custom_metadata" not in cols

    @pytest.mark.integration
    def test_unique_constraint_exists(self, pg_engine):
        """The (owner_id, category, slug) unique constraint must be present."""
        _run_alembic(TEST_PG_URL, "head")

        inspector = inspect(pg_engine)
        constraints = inspector.get_unique_constraints("projects")
        constraint_names = {c["name"] for c in constraints}
        assert "uq_project_owner_category_slug" in constraint_names

    @pytest.mark.integration
    def test_app_settings_seeded_with_defaults(self, pg_engine):
        """app_settings must be seeded with file_policy defaults after migration 003."""
        _run_alembic(TEST_PG_URL, "head")

        with pg_engine.connect() as conn:
            rows = conn.execute(
                text("SELECT key FROM app_settings ORDER BY key")
            ).fetchall()
        keys = {r[0] for r in rows}
        assert "file_policy.allowed_extensions" in keys
        assert "file_policy.hidden_name_patterns" in keys


class TestMigration004SeededDB:
    """Verify migration 004 forwards correctly when rows already exist."""

    @pytest.mark.integration
    def test_existing_projects_survive_migration(self, pg_engine):
        """Projects present at migration time must still exist afterward."""
        # Bring DB up to the revision immediately before 004
        _run_alembic(TEST_PG_URL, "003_add_app_settings")

        # Insert a user and two projects
        user_id = str(uuid.uuid4())
        project_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        now = datetime.utcnow()

        with pg_engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, username, email, display_name, password_hash, "
                    "is_admin, is_active, created_at, updated_at) VALUES "
                    "(:id, :uname, :email, :dn, :ph, false, true, :ca, :ua)"
                ),
                {
                    "id": user_id,
                    "uname": "migtest_user",
                    "email": "migtest@example.com",
                    "dn": "Mig Test",
                    "ph": "hash",
                    "ca": now,
                    "ua": now,
                },
            )
            for i, pid in enumerate(project_ids):
                conn.execute(
                    text(
                        "INSERT INTO projects (id, owner_id, title, description, "
                        "custom_metadata, created_at, updated_at) VALUES "
                        "(:id, :oid, :title, :desc, :cm, :ca, :ua)"
                    ),
                    {
                        "id": pid,
                        "oid": user_id,
                        "title": f"Test Project {i + 1}",
                        "desc": "A test project",
                        "cm": "{}",
                        "ca": now,
                        "ua": now,
                    },
                )
            conn.commit()

        # Now run migration 004
        _run_alembic(TEST_PG_URL, "004_directory_architecture")

        with pg_engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id FROM projects WHERE owner_id = :oid"),
                {"oid": user_id},
            ).fetchall()
        assert len(rows) == 2, "Both pre-migration projects should survive."

    @pytest.mark.integration
    def test_slug_populated_for_existing_rows(self, pg_engine):
        """slug is derived from title and populated for all existing projects."""
        _run_alembic(TEST_PG_URL, "003_add_app_settings")

        user_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        title = "Flexi Dragon v2 (PETG)"
        now = datetime.utcnow()

        with pg_engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, username, email, display_name, password_hash, "
                    "is_admin, is_active, created_at, updated_at) VALUES "
                    "(:id, :uname, :email, :dn, :ph, false, true, :ca, :ua)"
                ),
                {
                    "id": user_id,
                    "uname": "slugtest",
                    "email": "slug@example.com",
                    "dn": "Slug Tester",
                    "ph": "hash",
                    "ca": now,
                    "ua": now,
                },
            )
            conn.execute(
                text(
                    "INSERT INTO projects (id, owner_id, title, description, "
                    "custom_metadata, created_at, updated_at) VALUES "
                    "(:id, :oid, :title, :desc, :cm, :ca, :ua)"
                ),
                {
                    "id": project_id,
                    "oid": user_id,
                    "title": title,
                    "desc": "",
                    "cm": "{}",
                    "ca": now,
                    "ua": now,
                },
            )
            conn.commit()

        _run_alembic(TEST_PG_URL, "004_directory_architecture")

        with pg_engine.connect() as conn:
            row = conn.execute(
                text("SELECT slug FROM projects WHERE id = :id"),
                {"id": project_id},
            ).fetchone()

        expected_slug = _slugify(title)
        assert row is not None
        assert row[0] == expected_slug, f"Expected slug '{expected_slug}', got '{row[0]}'"

    @pytest.mark.integration
    def test_directory_path_populated_for_existing_rows(self, pg_engine):
        """directory_path is set to 'Projects/Uncategorized/{slug}' for existing rows."""
        _run_alembic(TEST_PG_URL, "003_add_app_settings")

        user_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        title = "My Test Widget"
        now = datetime.utcnow()

        with pg_engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, username, email, display_name, password_hash, "
                    "is_admin, is_active, created_at, updated_at) VALUES "
                    "(:id, :uname, :email, :dn, :ph, false, true, :ca, :ua)"
                ),
                {
                    "id": user_id,
                    "uname": "dirpathtest",
                    "email": "dirpath@example.com",
                    "dn": "Dir Path Test",
                    "ph": "hash",
                    "ca": now,
                    "ua": now,
                },
            )
            conn.execute(
                text(
                    "INSERT INTO projects (id, owner_id, title, description, "
                    "custom_metadata, created_at, updated_at) VALUES "
                    "(:id, :oid, :title, :desc, :cm, :ca, :ua)"
                ),
                {
                    "id": project_id,
                    "oid": user_id,
                    "title": title,
                    "desc": "",
                    "cm": "{}",
                    "ca": now,
                    "ua": now,
                },
            )
            conn.commit()

        _run_alembic(TEST_PG_URL, "004_directory_architecture")

        with pg_engine.connect() as conn:
            row = conn.execute(
                text("SELECT slug, category, directory_path FROM projects WHERE id = :id"),
                {"id": project_id},
            ).fetchone()

        slug, category, directory_path = row
        assert category == "Uncategorized"
        assert directory_path == f"Projects/Uncategorized/{slug}"

    @pytest.mark.integration
    def test_slug_uniqueness_per_owner_on_duplicate_titles(self, pg_engine):
        """Two projects with the same title get unique slugs (slug-1, slug-2)."""
        _run_alembic(TEST_PG_URL, "003_add_app_settings")

        user_id = str(uuid.uuid4())
        pid1, pid2 = str(uuid.uuid4()), str(uuid.uuid4())
        title = "Same Name Project"
        now = datetime.utcnow()

        with pg_engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, username, email, display_name, password_hash, "
                    "is_admin, is_active, created_at, updated_at) VALUES "
                    "(:id, :uname, :email, :dn, :ph, false, true, :ca, :ua)"
                ),
                {
                    "id": user_id,
                    "uname": "duptest",
                    "email": "dup@example.com",
                    "dn": "Dup Test",
                    "ph": "hash",
                    "ca": now,
                    "ua": now,
                },
            )
            for pid in [pid1, pid2]:
                conn.execute(
                    text(
                        "INSERT INTO projects (id, owner_id, title, description, "
                        "custom_metadata, created_at, updated_at) VALUES "
                        "(:id, :oid, :title, :desc, :cm, :ca, :ua)"
                    ),
                    {
                        "id": pid,
                        "oid": user_id,
                        "title": title,
                        "desc": "",
                        "cm": "{}",
                        "ca": now,
                        "ua": now,
                    },
                )
            conn.commit()

        _run_alembic(TEST_PG_URL, "004_directory_architecture")

        with pg_engine.connect() as conn:
            rows = conn.execute(
                text("SELECT slug FROM projects WHERE owner_id = :oid ORDER BY slug"),
                {"oid": user_id},
            ).fetchall()

        slugs = [r[0] for r in rows]
        assert len(slugs) == 2
        assert slugs[0] != slugs[1], "Duplicate titles must produce unique slugs."

    @pytest.mark.integration
    def test_models_table_removed(self, pg_engine):
        """The models table must not exist after migration 004."""
        _run_alembic(TEST_PG_URL, "head")

        inspector = inspect(pg_engine)
        assert "models" not in inspector.get_table_names()
