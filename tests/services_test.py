"""Tests for services layer."""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.db.base import Base
from backend.models.user import User
from backend.models.project import Project
from backend.models.model import Model
from backend.services.user_service import UserService
from backend.services.project_service import ProjectService
from backend.services.model_service import ModelService


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


@pytest.fixture
def user_service(test_db: Session):
    """Create UserService instance."""
    return UserService(test_db)


@pytest.fixture
def project_service(test_db: Session, tmp_path, monkeypatch):
    """Create ProjectService instance."""
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))
    return ProjectService(test_db)


@pytest.fixture
def model_service(test_db: Session):
    """Create ModelService instance."""
    return ModelService(test_db)


class TestUserService:
    """Tests for UserService."""

    def test_create_user(self, user_service: UserService):
        """Test creating a user."""
        user = user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="secure_password",
        )

        assert user.username == "testuser"
        assert user.nickname == "testuser"
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.id is not None

    def test_create_user_assigns_unique_nickname(self, user_service: UserService):
        """Nickname generation should resolve collisions deterministically."""
        first = user_service.create_user(
            username="nickowner",
            nickname="shared-nick",
            email="nickowner@example.com",
            display_name="Nick Owner",
            password="secure_password",
        )
        second = user_service.create_user(
            username="nickowner2",
            nickname="shared-nick",
            email="nickowner2@example.com",
            display_name="Nick Owner 2",
            password="secure_password",
        )

        assert first.nickname == "shared-nick"
        assert second.nickname.startswith("shared-nick-")

    def test_update_profile_renames_owner_directory_and_updates_project_paths(
        self,
        user_service: UserService,
        test_db: Session,
        monkeypatch,
        tmp_path,
    ):
        """Changing nickname should move owner directory and rewrite project directory_path."""
        monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

        user = user_service.create_user(
            username="renameowner",
            email="renameowner@example.com",
            display_name="Rename Owner",
            password="secure_password",
        )

        project_service = ProjectService(test_db)
        project = project_service.create_project(
            owner_id=user.id,
            title="Nickname Move",
        )

        old_root = tmp_path / "Projects" / user.nickname
        new_nickname = "rename-me"
        new_root = tmp_path / "Projects" / new_nickname
        assert old_root.exists()

        updated = user_service.update_profile(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            nickname=new_nickname,
        )

        refreshed = project_service.get_project_by_id(project.id)
        assert updated.nickname == new_nickname
        assert refreshed is not None
        assert refreshed.directory_path == f"Projects/{new_nickname}/{project.slug}"
        assert new_root.exists()
        assert not old_root.exists()

    def test_create_user_duplicate_username(self, user_service: UserService):
        """Test that duplicate username raises error."""
        user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="secure_password",
        )

        with pytest.raises(ValueError, match="already exists"):
            user_service.create_user(
                username="testuser",
                email="test2@example.com",
                display_name="Another User",
                password="another_password",
            )

    def test_create_user_duplicate_email(self, user_service: UserService):
        """Test that duplicate email raises error."""
        user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="secure_password",
        )

        with pytest.raises(ValueError, match="already exists"):
            user_service.create_user(
                username="testuser2",
                email="test@example.com",
                display_name="Another User",
                password="another_password",
            )

    def test_get_user_by_id(self, user_service: UserService):
        """Test getting user by ID."""
        created_user = user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="secure_password",
        )

        retrieved_user = user_service.get_user_by_id(created_user.id)

        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"
        assert retrieved_user.id == created_user.id

    def test_get_user_by_username(self, user_service: UserService):
        """Test getting user by username."""
        user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="secure_password",
        )

        retrieved_user = user_service.get_user_by_username("testuser")

        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"

    def test_get_user_by_email(self, user_service: UserService):
        """Test getting user by email."""
        user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="secure_password",
        )

        retrieved_user = user_service.get_user_by_email("test@example.com")

        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"

    def test_verify_password_correct(self, user_service: UserService):
        """Test password verification with correct password."""
        user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="correct_password",
        )

        verified_user = user_service.verify_password("testuser", "correct_password")

        assert verified_user is not None
        assert verified_user.username == "testuser"

    def test_verify_password_incorrect(self, user_service: UserService):
        """Test password verification with incorrect password."""
        user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="correct_password",
        )

        verified_user = user_service.verify_password("testuser", "wrong_password")

        assert verified_user is None

    def test_verify_password_nonexistent_user(self, user_service: UserService):
        """Test password verification for nonexistent user."""
        verified_user = user_service.verify_password("nonexistent", "password")

        assert verified_user is None

    def test_update_display_name(self, user_service: UserService):
        """Test updating user display name."""
        user = user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="secure_password",
        )

        updated_user = user_service.update_display_name(user.id, "New Display Name")

        assert updated_user.display_name == "New Display Name"

    def test_update_password(self, user_service: UserService):
        """Test updating user password."""
        user = user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="old_password",
        )

        user_service.update_password(user.id, "new_password")

        # Old password should not work
        assert user_service.verify_password("testuser", "old_password") is None

        # New password should work
        verified_user = user_service.verify_password("testuser", "new_password")
        assert verified_user is not None

    def test_delete_user(self, user_service: UserService):
        """Test deleting user."""
        user = user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="secure_password",
        )

        deleted = user_service.delete_user(user.id)

        assert deleted is True
        assert user_service.get_user_by_id(user.id) is None

    def test_list_users(self, user_service: UserService):
        """Test listing users."""
        for i in range(3):
            user_service.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                display_name=f"User {i}",
                password="password",
            )

        users = user_service.list_users()

        assert len(users) == 3


class TestProjectService:
    """Tests for ProjectService."""

    @pytest.fixture
    def user(self, user_service: UserService):
        """Create a test user."""
        return user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="password",
        )

    def test_create_project(self, project_service: ProjectService, user):
        """Test creating a project."""
        project = project_service.create_project(
            owner_id=user.id,
            title="Test Project",
        )

        assert project.title == "Test Project"
        assert project.owner_id == user.id
        assert project.id is not None
        assert project.slug == "test-project"
        assert project.category == "Uncategorized"

    def test_create_project_creates_directory_and_projectinfo(
        self,
        project_service: ProjectService,
        user,
        monkeypatch,
        tmp_path,
    ):
        """Project creation should create filesystem directory and ProjectInfo.md."""
        monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

        project = project_service.create_project(
            owner_id=user.id,
            title="Directory Project",
            category="private",
            description="Directory-backed project",
        )

        project_dir = tmp_path / "Projects" / user.nickname / project.slug
        info_path = project_dir / "ProjectInfo.md"

        assert project_dir.is_dir()
        assert info_path.exists()
        content = info_path.read_text(encoding="utf-8")
        assert "Directory Project" in content
        assert "Directory-backed project" in content

    def test_create_project_seeds_projectinfo_with_title_and_description(
        self,
        project_service: ProjectService,
        user,
        monkeypatch,
        tmp_path,
    ):
        """ProjectInfo.md should be seeded from create_project inputs."""
        monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

        title = "My Functional Project"
        description = "A precise seeded description"
        project = project_service.create_project(
            owner_id=user.id,
            title=title,
            category="private",
            description=description,
        )

        info_path = tmp_path / "Projects" / user.nickname / project.slug / "ProjectInfo.md"
        assert info_path.exists()
        content = info_path.read_text(encoding="utf-8")
        assert title in content
        assert description in content

    def test_create_project_nonexistent_owner(
        self, project_service: ProjectService
    ):
        """Test that creating project with nonexistent owner raises error."""
        with pytest.raises(ValueError, match="not found"):
            project_service.create_project(
                owner_id="nonexistent",
                title="Test Project",
            )

    def test_get_project_by_id(self, project_service: ProjectService, user):
        """Test getting project by ID."""
        created_project = project_service.create_project(
            owner_id=user.id,
            title="Test Project",
        )

        retrieved_project = project_service.get_project_by_id(created_project.id)

        assert retrieved_project is not None
        assert retrieved_project.title == "Test Project"

    def test_list_user_projects(self, project_service: ProjectService, user):
        """Test listing user's projects."""
        for i in range(3):
            project_service.create_project(
                owner_id=user.id,
                title=f"Project {i}",
            )

        projects = project_service.list_user_projects(user.id)

        assert len(projects) == 3

    def test_update_project(self, project_service: ProjectService, user):
        """Test updating project."""
        project = project_service.create_project(
            owner_id=user.id,
            title="Original Title",
        )

        updated_project = project_service.update_project(
            project.id,
            title="Updated Title",
        )

        assert updated_project.title == "Updated Title"
        assert updated_project.slug == "updated-title"

    def test_delete_project(self, project_service: ProjectService, user):
        """Test deleting project - default behavior is archive."""
        project = project_service.create_project(
            owner_id=user.id,
            title="Test Project",
        )

        deleted = project_service.delete_project(project.id)

        assert deleted is True
        # With default 'archive' policy, project should be archived not deleted
        archived = project_service.get_project_by_id(project.id)
        assert archived is not None
        assert archived.is_archived is True
        assert archived.category == "Uncategorized"

    def test_delete_project_removes_directory(
        self,
        project_service: ProjectService,
        user,
        monkeypatch,
        tmp_path,
    ):
        """Project deletion with archive policy preserves owner-scoped directory."""
        monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

        project = project_service.create_project(
            owner_id=user.id,
            title="Delete Directory Project",
            category="private",
        )

        project_dir = tmp_path / "Projects" / user.nickname / project.slug
        assert project_dir.exists()

        deleted = project_service.delete_project(project.id)

        assert deleted is True
        # With archive policy, directory remains under owner path.
        assert project_dir.exists()

    def test_check_project_ownership(
        self, project_service: ProjectService, user, user_service: UserService
    ):
        """Test checking project ownership."""
        project = project_service.create_project(
            owner_id=user.id,
            title="Test Project",
        )

        other_user = user_service.create_user(
            username="otheruser",
            email="other@example.com",
            display_name="Other User",
            password="password",
        )

        assert project_service.check_project_ownership(project.id, user.id) is True
        assert project_service.check_project_ownership(project.id, other_user.id) is False

    def test_delete_project_with_archive_policy(
        self,
        project_service: ProjectService,
        user,
        monkeypatch,
        tmp_path,
    ):
        """Project deletion with archive policy marks project archived in place."""
        monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

        project = project_service.create_project(
            owner_id=user.id,
            title="Archive Test Project",
            category="private",
        )
        # Set deletion_policy on the ORM object in the database
        from sqlalchemy import select
        from backend.models.project import Project
        orm_project = project_service.session.execute(
            select(Project).where(Project.id == project.id)
        ).scalar_one()
        orm_project.deletion_policy = "archive"
        project_service.session.commit()

        original_dir = tmp_path / "Projects" / user.nickname / project.slug
        assert original_dir.exists()

        deleted = project_service.delete_project(project.id)
        assert deleted is True

        # Project should still exist in database but be archived
        archived_project = project_service.get_project_by_id(project.id)
        assert archived_project is not None
        assert archived_project.category == "private"
        assert archived_project.is_archived is True

        # Directory remains at owner-scoped location.
        assert original_dir.exists()

    def test_delete_project_with_hard_delete_policy(
        self,
        project_service: ProjectService,
        user,
        monkeypatch,
        tmp_path,
    ):
        """Project deletion with hard_delete policy should permanently delete."""
        monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

        project = project_service.create_project(
            owner_id=user.id,
            title="Hard Delete Test Project",
            category="private",
        )
        # Set deletion_policy on the ORM object in the database
        from sqlalchemy import select
        from backend.models.project import Project
        orm_project = project_service.session.execute(
            select(Project).where(Project.id == project.id)
        ).scalar_one()
        orm_project.deletion_policy = "hard_delete"
        project_service.session.commit()

        project_dir = tmp_path / "Projects" / user.nickname / project.slug
        assert project_dir.exists()

        deleted = project_service.delete_project(project.id)
        assert deleted is True

        # Project should be completely gone from database
        assert project_service.get_project_by_id(project.id) is None

        # Directory should be deleted
        assert not project_dir.exists()

    def test_archive_project_default_policy(
        self,
        project_service: ProjectService,
        user,
        monkeypatch,
        tmp_path,
    ):
        """Default deletion policy should be archive."""
        monkeypatch.setenv("STORAGE_ROOT", str(tmp_path))

        project = project_service.create_project(
            owner_id=user.id,
            title="Default Policy Test",
        )
        # Don't explicitly set deletion_policy; should default to archive

        project_dir = tmp_path / "Projects" / user.nickname / project.slug
        assert project_dir.exists()

        deleted = project_service.delete_project(project.id)
        assert deleted is True

        # Should be archived (default behavior)
        archived_project = project_service.get_project_by_id(project.id)
        assert archived_project is not None
        assert archived_project.category == "Uncategorized"


class TestModelService:
    """Tests for ModelService."""

    @pytest.fixture
    def user(self, user_service: UserService):
        """Create a test user."""
        return user_service.create_user(
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            password="password",
        )

    @pytest.fixture
    def project(self, project_service: ProjectService, user):
        """Create a test project."""
        return project_service.create_project(
            owner_id=user.id,
            title="Test Project",
        )

    def test_create_model(self, model_service: ModelService, project, user):
        """Test creating a model."""
        model = model_service.create_model(
            project_id=project.id,
            uploaded_by_id=user.id,
            filename="model.stl",
            storage_key="s3://bucket/model.stl",
            tags=["printable", "test"],
        )

        assert model.filename == "model.stl"
        assert model.project_id == project.id
        assert model.uploaded_by_id == user.id
        assert model.tags == ["printable", "test"]

    def test_create_model_nonexistent_project(
        self, model_service: ModelService, user
    ):
        """Test creating model with nonexistent project raises error."""
        with pytest.raises(ValueError, match="not found"):
            model_service.create_model(
                project_id="nonexistent",
                uploaded_by_id=user.id,
                filename="model.stl",
                storage_key="s3://bucket/model.stl",
            )

    def test_create_model_nonexistent_uploader(self, model_service: ModelService, project):
        """Test creating model with nonexistent uploader raises error."""
        with pytest.raises(ValueError, match="not found"):
            model_service.create_model(
                project_id=project.id,
                uploaded_by_id="nonexistent",
                filename="model.stl",
                storage_key="s3://bucket/model.stl",
            )

    def test_get_model_by_id(self, model_service: ModelService, project, user):
        """Test getting model by ID."""
        created_model = model_service.create_model(
            project_id=project.id,
            uploaded_by_id=user.id,
            filename="model.stl",
            storage_key="s3://bucket/model.stl",
        )

        retrieved_model = model_service.get_model_by_id(created_model.id)

        assert retrieved_model is not None
        assert retrieved_model.filename == "model.stl"

    def test_list_project_models(self, model_service: ModelService, project, user):
        """Test listing models in a project."""
        for i in range(3):
            model_service.create_model(
                project_id=project.id,
                uploaded_by_id=user.id,
                filename=f"model{i}.stl",
                storage_key=f"s3://bucket/model{i}.stl",
            )

        models = model_service.list_project_models(project.id)

        assert len(models) == 3

    def test_list_user_uploaded_models(self, model_service: ModelService, project, user):
        """Test listing models uploaded by user."""
        for i in range(3):
            model_service.create_model(
                project_id=project.id,
                uploaded_by_id=user.id,
                filename=f"model{i}.stl",
                storage_key=f"s3://bucket/model{i}.stl",
            )

        models = model_service.list_user_uploaded_models(user.id)

        assert len(models) == 3

    def test_update_model(self, model_service: ModelService, project, user):
        """Test updating model metadata."""
        model = model_service.create_model(
            project_id=project.id,
            uploaded_by_id=user.id,
            filename="original.stl",
            storage_key="s3://bucket/model.stl",
            tags=["original"],
        )

        updated_model = model_service.update_model(
            model.id,
            filename="updated.stl",
            tags=["updated", "improved"],
        )

        assert updated_model.filename == "updated.stl"
        assert updated_model.tags == ["updated", "improved"]

    def test_delete_model(self, model_service: ModelService, project, user):
        """Test deleting model."""
        model = model_service.create_model(
            project_id=project.id,
            uploaded_by_id=user.id,
            filename="model.stl",
            storage_key="s3://bucket/model.stl",
        )

        deleted = model_service.delete_model(model.id)

        assert deleted is True
        assert model_service.get_model_by_id(model.id) is None

    def test_check_model_ownership(self, model_service: ModelService, project, user, user_service):
        """Test checking model ownership."""
        model = model_service.create_model(
            project_id=project.id,
            uploaded_by_id=user.id,
            filename="model.stl",
            storage_key="s3://bucket/model.stl",
        )

        other_user = user_service.create_user(
            username="otheruser",
            email="other@example.com",
            display_name="Other User",
            password="password",
        )

        assert model_service.check_model_ownership(model.id, user.id) is True
        assert model_service.check_model_ownership(model.id, other_user.id) is False

    def test_check_model_in_project(self, model_service: ModelService, project, user, project_service):
        """Test checking if model belongs to project."""
        model = model_service.create_model(
            project_id=project.id,
            uploaded_by_id=user.id,
            filename="model.stl",
            storage_key="s3://bucket/model.stl",
        )

        other_project = project_service.create_project(
            owner_id=user.id,
            title="Other Project",
        )

        assert model_service.check_model_in_project(model.id, project.id) is True
        assert model_service.check_model_in_project(model.id, other_project.id) is False
