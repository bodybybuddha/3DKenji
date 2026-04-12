"""Tests for ProjectAccessService."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.db.base import Base
from backend.models.project import Project
from backend.models.user import User
from backend.services.project_access import ProjectAccessService


@pytest.fixture
def test_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _new_user(test_db: Session, username: str, email: str) -> User:
    user = User(
        id=f"{username}-id",
        username=username,
        nickname=username,
        email=email,
        display_name=username,
        password_hash="hash",
        is_admin=False,
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    return user


def _new_project(test_db: Session, owner_id: str, visibility: str = "private") -> Project:
    project = Project(
        id=f"project-{owner_id}-{visibility}",
        owner_id=owner_id,
        title="Test Project",
        slug="test-project",
        category="Uncategorized",
        visibility=visibility,
        directory_path=f"Projects/{owner_id}/test-project",
        disk_size_bytes=0,
        is_archived=False,
    )
    test_db.add(project)
    test_db.commit()
    return project


def test_owner_has_full_access(test_db: Session):
    owner = _new_user(test_db, "owner", "owner@example.com")
    project = _new_project(test_db, owner.id)

    access = ProjectAccessService(test_db)

    assert access.can_view(project, owner.id)
    assert access.can_edit(project, owner.id)
    assert access.can_manage_access(project, owner.id)


def test_viewer_collaborator_has_read_only_access(test_db: Session):
    owner = _new_user(test_db, "owner1", "owner1@example.com")
    viewer = _new_user(test_db, "viewer1", "viewer1@example.com")
    project = _new_project(test_db, owner.id)

    access = ProjectAccessService(test_db)
    access.upsert_collaborator(
        project=project,
        target_user_id=viewer.id,
        role="viewer",
        granted_by_id=owner.id,
    )

    assert access.can_view(project, viewer.id)
    assert not access.can_edit(project, viewer.id)


def test_editor_collaborator_has_edit_access(test_db: Session):
    owner = _new_user(test_db, "owner2", "owner2@example.com")
    editor = _new_user(test_db, "editor2", "editor2@example.com")
    project = _new_project(test_db, owner.id)

    access = ProjectAccessService(test_db)
    access.upsert_collaborator(
        project=project,
        target_user_id=editor.id,
        role="editor",
        granted_by_id=owner.id,
    )

    assert access.can_view(project, editor.id)
    assert access.can_edit(project, editor.id)


def test_public_project_allows_anonymous_read(test_db: Session):
    owner = _new_user(test_db, "owner3", "owner3@example.com")
    project = _new_project(test_db, owner.id, visibility="public")

    access = ProjectAccessService(test_db)

    assert access.can_view(project, None)
    assert not access.can_edit(project, None)


def test_accept_invitation_requires_matching_email(test_db: Session):
    owner = _new_user(test_db, "owner4", "owner4@example.com")
    invited = _new_user(test_db, "invited4", "invited@example.com")
    stranger = _new_user(test_db, "stranger4", "stranger@example.com")
    project = _new_project(test_db, owner.id)

    access = ProjectAccessService(test_db)
    invitation = access.create_invitation(
        project=project,
        invited_email=invited.email,
        role="viewer",
        token_hash="abc123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        invited_by_id=owner.id,
    )

    denied = access.accept_invitation(token_hash=invitation.token_hash, user_id=stranger.id)
    assert denied is None

    accepted = access.accept_invitation(token_hash=invitation.token_hash, user_id=invited.id)
    assert accepted is not None
    assert accepted.user_id == invited.id

    stored_invitation = test_db.execute(
        select(type(invitation)).where(type(invitation).id == invitation.id)
    ).scalar_one()
    assert stored_invitation.accepted_at is not None
