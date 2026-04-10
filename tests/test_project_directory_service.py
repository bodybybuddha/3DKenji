"""Tests for ProjectDirectoryService (T304) and markdown_service (T305/T306).

Covers:
- Service CRUD operations using a tmp directory
- Markdown parse / format round-trips
- Path traversal / security rejection tests
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from backend.services.markdown_service import (
    ensure_project_info_frontmatter,
    format_frontmatter,
    format_project_info,
    format_print_history,
    ensure_print_history_frontmatter,
    render_markdown,
    parse_print_history,
    split_frontmatter,
    format_print_session,
    normalize_date,
)
from backend.services.project_directory import (
    PathTraversalError,
    PathNotFoundError,
    UnsafeFilenameError,
    ProjectDirectoryService,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def svc(tmp_path: Path) -> ProjectDirectoryService:
    """Return a service bound to a fresh temp directory."""
    return ProjectDirectoryService(tmp_path / "my-project")


@pytest.fixture()
def svc_with_dir(svc: ProjectDirectoryService) -> ProjectDirectoryService:
    """Return a service whose project directory has been created."""
    svc.create_project_directory(title="Test Project")
    return svc


# ===========================================================================
# markdown_service tests
# ===========================================================================


class TestNormalizeDate:
    def test_canonical_format_unchanged(self):
        assert normalize_date("2025-03-15") == "2025-03-15"

    def test_dd_mm_yyyy(self):
        assert normalize_date("15/03/2025") == "2025-03-15"

    def test_unknown_format_returns_today(self):
        from datetime import date

        result = normalize_date("not-a-date")
        assert result == date.today().isoformat()

    def test_whitespace_stripped(self):
        assert normalize_date("  2025-01-01  ") == "2025-01-01"


class TestRenderMarkdown:
    def test_basic_heading(self):
        html = render_markdown("# Hello")
        assert "<h1>" in html
        assert "Hello" in html

    def test_empty_string(self):
        assert render_markdown("") == ""

    def test_script_tags_escaped(self):
        """HTML tags in source should be escaped, not rendered."""
        html = render_markdown("<script>alert('xss')</script>")
        assert "<script>" not in html
        assert "alert" in html  # text remains, tag is escaped


class TestProjectInfoFrontmatter:
    def test_split_frontmatter_extracts_metadata_and_body(self):
        text = textwrap.dedent("""\
            ---
            title: Test Project
            summary: Short summary
            tags:
              - calibration
              - benchy
            status: active
            ---

            # About
            Project body.
        """)
        metadata, body = split_frontmatter(text)
        assert metadata["title"] == "Test Project"
        assert metadata["summary"] == "Short summary"
        assert metadata["tags"] == ["calibration", "benchy"]
        assert metadata["status"] == "active"
        assert body.startswith("# About")

    def test_format_frontmatter_serializes_lists(self):
        text = format_frontmatter({"title": "Example", "tags": ["a", "b"]})
        assert "title: Example" in text
        assert "tags:" in text
        assert "  - a" in text
        assert "  - b" in text

    def test_format_project_info_contains_frontmatter_and_body(self):
        text = format_project_info(
            title="Example Project",
            description="A useful description",
            today="2026-04-10",
            tags=["3d-printing", "calibration"],
        )
        metadata, body = split_frontmatter(text)
        assert metadata["title"] == "Example Project"
        assert metadata["summary"] == "A useful description"
        assert metadata["tags"] == ["3d-printing", "calibration"]
        assert "# About" in body
        assert "A useful description" in body

    def test_render_markdown_does_not_render_frontmatter_when_split_first(self):
        text = format_project_info(
            title="Rendered Project",
            description="Rendered body",
            today="2026-04-10",
        )
        _, body = split_frontmatter(text)
        html = render_markdown(body)
        assert "Rendered body" in html
        assert "title:" not in html

    def test_ensure_project_info_frontmatter_preserves_existing_body(self):
        original = textwrap.dedent("""\
            # Legacy Project

            This is a migrated project.

            ## Notes
            Existing content.
        """)
        updated = ensure_project_info_frontmatter(original, title="Legacy Project")
        metadata, body = split_frontmatter(updated)
        assert metadata["title"] == "Legacy Project"
        assert metadata["summary"] == "This is a migrated project."
        assert metadata["tags"] == ["3d-printing"]
        assert "## Notes" in body
        assert "Existing content." in body


class TestParsePrintHistory:
    def test_empty_text_returns_empty_list(self):
        assert parse_print_history("") == []

    def test_no_sessions_returns_empty_list(self):
        assert parse_print_history("# Print History\n\nNo sessions yet.") == []

    def test_single_session_parsed(self):
        text = textwrap.dedent("""\
            # Print History

            ## 2025-03-15 – Session 1

            - **Filament**: Prusament PLA Galaxy Black (PLA, 1.75mm)
            - **Result**: Success

            ---
        """)
        sessions = parse_print_history(text)
        assert len(sessions) == 1
        s = sessions[0]
        assert s["date"] == "2025-03-15"
        assert s["session_n"] == 1
        assert s["fields"]["Filament"] == "Prusament PLA Galaxy Black (PLA, 1.75mm)"
        assert s["fields"]["Result"] == "Success"

    def test_multiple_sessions_order_preserved(self):
        """Sessions are returned in the order they appear in the file (newest first)."""
        text = textwrap.dedent("""\
            # Print History

            ## 2025-04-01 – Session 2

            - **Result**: Success

            ---

            ## 2025-03-01 – Session 1

            - **Result**: Failed

            ---
        """)
        sessions = parse_print_history(text)
        assert len(sessions) == 2
        assert sessions[0]["session_n"] == 2
        assert sessions[1]["session_n"] == 1

    def test_malformed_body_no_crash(self):
        """Malformed body text should not raise; fields dict may be empty."""
        text = "## 2025-01-01 – Session 1\n\nsome garbage\n\n---\n"
        sessions = parse_print_history(text)
        assert len(sessions) == 1
        assert sessions[0]["fields"] == {}


class TestFormatPrintSession:
    def test_output_contains_heading(self):
        md = format_print_session(
            session_n=1,
            session_date="2025-03-15",
            result="Success",
        )
        assert "## 2025-03-15 – Session 1" in md

    def test_date_normalised_on_write(self):
        md = format_print_session(session_n=1, session_date="15/03/2025")
        assert "2025-03-15" in md
        assert "15/03/2025" not in md

    def test_optional_notes_included(self):
        md = format_print_session(session_n=1, session_date="2025-01-01", notes="Great print!")
        assert "### Notes" in md
        assert "Great print!" in md

    def test_round_trip(self):
        """Format a session then parse it back; values should match."""
        md = format_print_session(
            session_n=3,
            session_date="2025-06-10",
            filament="Prusament PETG Orange",
            result="Partial",
        )
        full = "# Print History\n\n" + md
        sessions = parse_print_history(full)
        assert len(sessions) == 1
        assert sessions[0]["session_n"] == 3
        assert sessions[0]["date"] == "2025-06-10"
        assert sessions[0]["fields"]["Filament"] == "Prusament PETG Orange"


class TestPrintHistoryFrontmatter:
    def test_format_print_history_contains_frontmatter_and_body(self):
        text = format_print_history(
            title="Test Project",
            today="2026-04-10",
            printer_model="Prusa i3 MK3",
            notes="Main printer for tests",
        )
        metadata, body = split_frontmatter(text)
        assert metadata["project"] == "Test Project"
        assert metadata["created_date"] == "2026-04-10"
        assert metadata["printer_model"] == "Prusa i3 MK3"
        assert metadata["notes"] == "Main printer for tests"
        assert metadata["total_sessions"] == "0"  # Frontmatter values are strings
        assert "# Print History" in body

    def test_format_print_history_defaults_created_date_to_today(self):
        text = format_print_history(
            title="Test Project",
            today="2026-04-10",
        )
        metadata, _ = split_frontmatter(text)
        assert metadata["created_date"] == "2026-04-10"

    def test_ensure_print_history_frontmatter_preserves_sessions(self):
        original = textwrap.dedent("""\
            # Print History

            ## 2025-03-15 – Session 1

            - **Filament**: Prusament PLA
            - **Result**: Success

            ---
        """)
        updated = ensure_print_history_frontmatter(original, title="Test Project")
        metadata, body = split_frontmatter(updated)
        assert metadata["project"] == "Test Project"
        assert "## 2025-03-15 – Session 1" in body
        assert "Success" in body

    def test_get_print_history_includes_metadata(self, svc_with_dir: ProjectDirectoryService):
        svc_with_dir.create_project_directory(title="Test Project")
        history = svc_with_dir.get_print_history()
        assert "project" in history.metadata
        assert history.metadata["project"] == "Test Project"
        assert history.metadata["total_sessions"] == "0"  # Frontmatter values are strings
        assert history.metadata["created_date"] != ""


# ===========================================================================
# ProjectDirectoryService – basic operations
# ===========================================================================


class TestCreateProjectDirectory:
    def test_creates_root_and_subdirs(self, svc: ProjectDirectoryService, tmp_path: Path):
        svc.create_project_directory(title="My Widget")
        root = tmp_path / "my-project"
        assert root.is_dir()
        for subdir in ("models", "cad_files", "timelapse", "images"):
            assert (root / subdir).is_dir()

    def test_creates_projectinfo_md(self, svc: ProjectDirectoryService, tmp_path: Path):
        svc.create_project_directory(title="My Widget")
        path = tmp_path / "my-project" / "ProjectInfo.md"
        assert path.exists()
        content = path.read_text()
        assert "My Widget" in content
        assert content.startswith("---\n")

    def test_creates_printhistory_md(self, svc: ProjectDirectoryService, tmp_path: Path):
        svc.create_project_directory(title="My Widget")
        path = tmp_path / "my-project" / "PrintHistory.md"
        assert path.exists()
        assert "Print History" in path.read_text()

    def test_idempotent_does_not_overwrite(self, svc: ProjectDirectoryService, tmp_path: Path):
        svc.create_project_directory(title="Project A")
        pi_path = tmp_path / "my-project" / "ProjectInfo.md"
        pi_path.write_text("# Custom Content")
        svc.create_project_directory(title="Project A")
        # Should NOT overwrite
        assert pi_path.read_text() == "# Custom Content"


class TestListFiles:
    def test_empty_project_returns_subdirs(self, svc_with_dir: ProjectDirectoryService):
        entries = svc_with_dir.list_files()
        names = {e.name for e in entries}
        # Canonical sub-dirs show up; ProjectInfo.md and PrintHistory.md are hidden at root
        assert "models" in names
        assert "ProjectInfo.md" not in names
        assert "PrintHistory.md" not in names

    def test_lists_files_in_subdir(self, svc_with_dir: ProjectDirectoryService):
        (svc_with_dir._root / "models" / "test.stl").write_bytes(b"STL data")
        entries = list(svc_with_dir.list_files("models"))
        names = [e.name for e in entries]
        assert "test.stl" in names

    def test_hides_dot_files(self, svc_with_dir: ProjectDirectoryService):
        (svc_with_dir._root / ".hidden_file").write_bytes(b"secret")
        entries = list(svc_with_dir.list_files())
        names = {e.name for e in entries}
        assert ".hidden_file" not in names

    def test_missing_dir_raises(self, svc: ProjectDirectoryService):
        with pytest.raises(PathNotFoundError):
            svc.list_files()


class TestReadWriteDeleteFile:
    def test_write_then_read(self, svc_with_dir: ProjectDirectoryService):
        svc_with_dir.write_file("models/part.stl", b"STL content", create_parents=True)
        data = svc_with_dir.read_file("models/part.stl")
        assert data == b"STL content"

    def test_delete_removes_file(self, svc_with_dir: ProjectDirectoryService):
        svc_with_dir.write_file("models/temp.stl", b"data", create_parents=True)
        svc_with_dir.delete_file("models/temp.stl")
        assert not (svc_with_dir._root / "models" / "temp.stl").exists()

    def test_read_missing_raises(self, svc_with_dir: ProjectDirectoryService):
        with pytest.raises(PathNotFoundError):
            svc_with_dir.read_file("models/ghost.stl")

    def test_delete_missing_raises(self, svc_with_dir: ProjectDirectoryService):
        with pytest.raises(PathNotFoundError):
            svc_with_dir.delete_file("models/ghost.stl")


class TestProjectInfoHelpers:
    def test_get_returns_raw_and_html(self, svc_with_dir: ProjectDirectoryService):
        info = svc_with_dir.get_project_info()
        assert info.raw != ""
        assert "<h1>" in info.html
        assert info.metadata["title"] == "Test Project"
        assert "# About" in info.body

    def test_write_persists(self, svc_with_dir: ProjectDirectoryService):
        svc_with_dir.write_project_info("# Updated Title\n\nNew content.")
        info = svc_with_dir.get_project_info()
        assert "Updated Title" in info.raw

    def test_missing_file_returns_empty(self, svc: ProjectDirectoryService, tmp_path: Path):
        svc._root.mkdir(parents=True, exist_ok=True)  # root exists, but no ProjectInfo.md
        info = svc.get_project_info()
        assert info.raw == ""
        assert info.html == ""


class TestPrintHistoryHelpers:
    def test_append_session_prepends_to_file(self, svc_with_dir: ProjectDirectoryService):
        svc_with_dir.append_print_session(
            {"session_date": "2025-03-01", "filament": "PLA Black", "result": "Success"}
        )
        history = svc_with_dir.get_print_history()
        assert len(history.sessions) == 1
        assert history.sessions[0]["date"] == "2025-03-01"

    def test_second_append_is_first_in_list(self, svc_with_dir: ProjectDirectoryService):
        svc_with_dir.append_print_session({"session_date": "2025-01-01", "result": "Success"})
        svc_with_dir.append_print_session({"session_date": "2025-04-01", "result": "Failed"})
        history = svc_with_dir.get_print_history()
        # Newest (April) is at index 0 because it was appended last and prepended into file
        assert history.sessions[0]["date"] == "2025-04-01"
        assert history.sessions[0]["session_n"] == 2
        assert history.sessions[1]["session_n"] == 1

    def test_date_normalised_on_append(self, svc_with_dir: ProjectDirectoryService):
        svc_with_dir.append_print_session({"session_date": "15/03/2025", "result": "Success"})
        history = svc_with_dir.get_print_history()
        assert history.sessions[0]["date"] == "2025-03-15"

    def test_empty_history_returns_no_sessions(self, svc_with_dir: ProjectDirectoryService):
        history = svc_with_dir.get_print_history()
        assert history.sessions == []

    def test_appends_to_missing_file(self, svc: ProjectDirectoryService, tmp_path: Path):
        """Append should create PrintHistory.md if it does not exist."""
        svc._root.mkdir(parents=True, exist_ok=True)
        svc.append_print_session({"session_date": "2025-06-01", "result": "Success"})
        hist_path = svc._root / "PrintHistory.md"
        assert hist_path.exists()


# ===========================================================================
# Security tests (T306)
# ===========================================================================


class TestPathTraversalRejection:
    def test_absolute_path_rejected_read(self, svc_with_dir: ProjectDirectoryService):
        with pytest.raises(PathTraversalError):
            svc_with_dir.read_file("/etc/passwd")

    def test_dotdot_path_rejected_read(self, svc_with_dir: ProjectDirectoryService):
        with pytest.raises(PathTraversalError):
            svc_with_dir.read_file("../../etc/passwd")

    def test_absolute_path_rejected_write(self, svc_with_dir: ProjectDirectoryService):
        with pytest.raises(PathTraversalError):
            svc_with_dir.write_file("/tmp/evil.txt", b"evil")

    def test_dotdot_path_rejected_write(self, svc_with_dir: ProjectDirectoryService):
        with pytest.raises(PathTraversalError):
            svc_with_dir.write_file("../../../tmp/evil.txt", b"evil")

    def test_dotdot_path_rejected_delete(self, svc_with_dir: ProjectDirectoryService):
        with pytest.raises(PathTraversalError):
            svc_with_dir.delete_file("../../important.txt")

    def test_dotdot_path_rejected_list(self, svc_with_dir: ProjectDirectoryService):
        with pytest.raises(PathTraversalError):
            svc_with_dir.list_files("../../etc")

    def test_null_byte_in_path_rejected(self, svc_with_dir: ProjectDirectoryService):
        """Null bytes in filenames must be rejected."""
        with pytest.raises((PathTraversalError, UnsafeFilenameError)):
            svc_with_dir.read_file("models/file\x00evil.stl")


class TestSanitizeFilename:
    def test_normal_name_unchanged(self):
        assert ProjectDirectoryService.sanitize_filename("model.stl") == "model.stl"

    def test_slashes_replaced(self):
        result = ProjectDirectoryService.sanitize_filename("path/to/file.stl")
        assert "/" not in result
        assert result.endswith("file.stl")

    def test_leading_dot_stripped(self):
        result = ProjectDirectoryService.sanitize_filename(".hidden")
        assert not result.startswith(".")

    def test_null_byte_stripped(self):
        result = ProjectDirectoryService.sanitize_filename("file\x00.stl")
        assert "\x00" not in result

    def test_empty_after_sanitise_raises(self):
        with pytest.raises(UnsafeFilenameError):
            ProjectDirectoryService.sanitize_filename("...")
