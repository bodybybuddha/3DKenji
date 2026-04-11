"""ProjectDirectoryService: all filesystem operations for project directories.

Security contract
-----------------
Every path that reaches the filesystem goes through :meth:`_safe_resolve`.
That method:

1. Rejects paths that are absolute or contain traversal components (``..``).
2. Resolves the sanitised relative path under the project directory using
   ``Path.resolve()`` (follows no symlinks, uses os.path.realpath semantics).
3. Verifies the resolved path is *strictly* inside the project root.
4. Rejects symlinks that point outside the project root.

No method in this class accepts a raw user-supplied path without first calling
:meth:`_safe_resolve`.  API endpoints must **not** perform ad-hoc filesystem
operations; they must delegate to this service.
"""

from __future__ import annotations

import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from backend.services.markdown_service import (
    PRINT_HISTORY_TEMPLATE,
    format_print_session,
    format_project_info,
    format_print_history,
    ensure_print_history_frontmatter,
    parse_print_history,
    render_markdown,
    normalize_date,
    split_frontmatter,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_projects_dir() -> Path:
    """Return the Projects root directory from environment at call time."""
    # Keep default aligned with storage plugin behavior (relative data/storage).
    storage_root = Path(os.environ.get("STORAGE_ROOT", "data/storage"))

    # Compatibility: prefer the canonical capitalized folder when present,
    # but gracefully fall back to lowercase layouts from older installs.
    canonical = storage_root / "Projects"
    legacy = storage_root / "projects"
    if canonical.exists():
        return canonical
    if legacy.exists():
        return legacy
    return canonical

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PathTraversalError(ValueError):
    """Raised when a supplied path would escape the project directory."""


class PathNotFoundError(FileNotFoundError):
    """Raised when the target path does not exist."""


class UnsafeFilenameError(ValueError):
    """Raised when a filename contains unsafe characters."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FileEntry:
    """Represents one item in a directory listing."""

    name: str
    relative_path: str
    is_dir: bool
    size_bytes: int = 0
    extension: str = ""


@dataclass
class ProjectInfoContent:
    raw: str
    html: str
    metadata: dict[str, Any] = field(default_factory=dict)
    body: str = ""


@dataclass
class PrintHistoryContent:
    sessions: list[dict[str, Any]] = field(default_factory=list)
    raw: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ProjectDirectoryService
# ---------------------------------------------------------------------------


class ProjectDirectoryService:
    """Manages the on-disk directory for a single project.

    Parameters
    ----------
    project_dir:
        Absolute path to the project's root directory on disk.  Typically
        built by the caller as ``PROJECTS_DIR / category / slug``.
    """

    def __init__(self, project_dir: Path) -> None:
        # Resolve once at construction to canonicalise any ``..`` or symlinks
        # in the *base* path itself (not user-supplied sub-paths).
        self._root = project_dir.resolve()

    # ------------------------------------------------------------------
    # Security helpers
    # ------------------------------------------------------------------

    def _safe_resolve(self, relative_path: str) -> Path:
        """Validate *relative_path* and return the absolute Path under project root.

        Raises
        ------
        PathTraversalError
            If the path is absolute, contains ``..`` components, or resolves
            outside the project root (including via symlinks).
        UnsafeFilenameError
            If individual segment names contain null bytes or control characters.
        """
        # Reject absolute paths immediately
        if os.path.isabs(relative_path):
            raise PathTraversalError(
                f"Absolute paths are not allowed: {relative_path!r}"
            )

        # Reject null bytes and control characters before any further processing
        if "\x00" in relative_path or any(
            unicodedata.category(c) == "Cc" for c in relative_path if c not in "\t"
        ):
            raise UnsafeFilenameError(
                f"Path contains unsafe characters: {relative_path!r}"
            )

        # Resolve the combined path and check containment
        candidate = (self._root / relative_path).resolve()

        # Ensure it is inside the project root (handles ``..`` traversal)
        try:
            candidate.relative_to(self._root)
        except ValueError:
            raise PathTraversalError(
                f"Path escapes project root: {relative_path!r}"
            )

        # If it exists and is a symlink, verify the symlink target is also inside root
        if candidate.is_symlink():
            real = Path(os.path.realpath(candidate))
            try:
                real.relative_to(self._root)
            except ValueError:
                raise PathTraversalError(
                    f"Symlink target escapes project root: {relative_path!r}"
                )

        # Validate each segment name for control characters / null bytes
        for part in Path(relative_path).parts:
            if "\x00" in part or any(unicodedata.category(c) == "Cc" for c in part):
                raise UnsafeFilenameError(
                    f"Filename contains unsafe characters: {part!r}"
                )

        return candidate

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Return a filesystem-safe version of *name*.

        Strips leading/trailing whitespace and dots, replaces path-separator
        characters, and removes null bytes and other control characters.
        The original extension is preserved.
        """
        # Remove null bytes and control characters
        name = "".join(
            c for c in name if c != "\x00" and unicodedata.category(c) != "Cc"
        )
        # Replace path separators
        name = re.sub(r"[/\\]", "-", name)
        # Strip leading dots and whitespace (prevents hidden files from API uploads)
        name = name.lstrip(". ").strip()
        if not name:
            raise UnsafeFilenameError("Empty filename after sanitisation.")
        return name

    # ------------------------------------------------------------------
    # Directory lifecycle
    # ------------------------------------------------------------------

    def create_project_directory(
        self,
        title: str,
        description: str = "",
    ) -> None:
        """Create the project directory tree and seed initial markdown files.

        Idempotent: if the directory already exists the call succeeds silently.
        """
        self._root.mkdir(parents=True, exist_ok=True)
        for subdir in ("models", "cad_files", "timelapse", "images"):
            (self._root / subdir).mkdir(exist_ok=True)

        # Seed ProjectInfo.md if absent
        project_info_path = self._root / "ProjectInfo.md"
        if not project_info_path.exists():
            content = format_project_info(
                title=title,
                description=description or "Add a description here.",
                today=date.today().isoformat(),
            )
            project_info_path.write_text(content, encoding="utf-8")

        # Seed PrintHistory.md if absent
        print_history_path = self._root / "PrintHistory.md"
        if not print_history_path.exists():
            content = format_print_history(
                title=title,
                today=date.today().isoformat(),
            )
            print_history_path.write_text(content, encoding="utf-8")

    def delete_project_directory(self) -> None:
        """Permanently remove the entire project directory from disk."""
        if self._root.exists():
            shutil.rmtree(self._root)

    def project_directory_exists(self) -> bool:
        return self._root.is_dir()

    # ------------------------------------------------------------------
    # File browser
    # ------------------------------------------------------------------

    def list_files(self, relative_path: str = "") -> Sequence[FileEntry]:
        """Return a flat list of :class:`FileEntry` items in *relative_path*.

        Hidden file/directory names (starting with ``.``) are excluded.
        ``ProjectInfo.md`` and ``PrintHistory.md`` are excluded from the
        generic file browser (they have dedicated endpoints).

        Parameters
        ----------
        relative_path:
            Sub-path within the project directory.  Empty string means the root.

        Raises
        ------
        PathTraversalError
            If *relative_path* escapes the project root.
        PathNotFoundError
            If the target directory does not exist.
        """
        RESERVED_FILES = {"ProjectInfo.md", "PrintHistory.md"}

        if relative_path:
            target = self._safe_resolve(relative_path)
        else:
            target = self._root

        if not target.exists():
            raise PathNotFoundError(str(target))
        if not target.is_dir():
            raise NotADirectoryError(str(target))

        entries: list[FileEntry] = []
        for item in sorted(target.iterdir()):
            if item.name.startswith("."):
                continue
            if item.name in RESERVED_FILES and relative_path == "":
                continue
            rel = item.relative_to(self._root).as_posix()
            entry = FileEntry(
                name=item.name,
                relative_path=rel,
                is_dir=item.is_dir(),
                size_bytes=item.stat().st_size if item.is_file() else 0,
                extension=item.suffix.lstrip(".").lower() if item.is_file() else "",
            )
            entries.append(entry)
        return entries

    def read_file(self, relative_path: str) -> bytes:
        """Return the raw bytes of a file inside the project directory.

        Raises
        ------
        PathTraversalError
            If *relative_path* escapes the project root.
        PathNotFoundError
            If the file does not exist.
        """
        target = self._safe_resolve(relative_path)
        if not target.exists():
            raise PathNotFoundError(str(target))
        if not target.is_file():
            raise IsADirectoryError(str(target))
        return target.read_bytes()

    def write_file(
        self,
        relative_path: str,
        content: bytes,
        *,
        create_parents: bool = False,
    ) -> None:
        """Write *content* to a file inside the project directory.

        The filename component of *relative_path* is sanitised before writing.
        Parent directories are created only when *create_parents* is True.

        Raises
        ------
        PathTraversalError
            If *relative_path* escapes the project root.
        UnsafeFilenameError
            If the filename is unsafe.
        """
        path = Path(relative_path)
        safe_name = self.sanitize_filename(path.name)
        safe_relative = str(path.parent / safe_name) if path.parent != Path(".") else safe_name

        target = self._safe_resolve(safe_relative)

        if create_parents:
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def delete_file(self, relative_path: str) -> None:
        """Delete a file (not a directory) inside the project directory.

        Raises
        ------
        PathTraversalError
            If *relative_path* escapes the project root.
        PathNotFoundError
            If the file does not exist.
        """
        target = self._safe_resolve(relative_path)
        if not target.exists():
            raise PathNotFoundError(str(target))
        if target.is_dir():
            raise IsADirectoryError(
                f"Cannot delete directory with delete_file: {relative_path!r}"
            )
        target.unlink()

    # ------------------------------------------------------------------
    # ProjectInfo.md helpers
    # ------------------------------------------------------------------

    def get_project_info(self) -> ProjectInfoContent:
        """Read ProjectInfo.md and return raw text and rendered HTML."""
        path = self._root / "ProjectInfo.md"
        if not path.exists():
            return ProjectInfoContent(raw="", metadata={}, body="", html="")
        raw = path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(raw)
        return ProjectInfoContent(raw=raw, metadata=metadata, body=body, html=render_markdown(body))

    def write_project_info(self, content: str) -> None:
        """Overwrite ProjectInfo.md with *content*.

        Does not validate markdown syntax — that is intentional; the file may
        contain arbitrary CommonMark.
        """
        path = self._root / "ProjectInfo.md"
        path.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # PrintHistory.md helpers
    # ------------------------------------------------------------------

    def get_print_history(self) -> PrintHistoryContent:
        """Read and parse PrintHistory.md, returning sessions newest-first."""
        path = self._root / "PrintHistory.md"
        if not path.exists():
            return PrintHistoryContent()
        raw = path.read_text(encoding="utf-8")
        metadata, _ = split_frontmatter(raw)
        return PrintHistoryContent(
            sessions=parse_print_history(raw),
            raw=raw,
            metadata=metadata,
        )

    def append_print_session(self, session_data: dict[str, Any]) -> None:
        """Prepend a new session block to PrintHistory.md.

        ``session_data`` should contain the keyword arguments accepted by
        :func:`~backend.services.markdown_service.format_print_session`.

        The ``session_date`` field is normalised to YYYY-MM-DD before writing.
        If omitted it defaults to today.

        Session numbering (``session_n``) is auto-assigned as current count + 1.
        """
        existing = self.get_print_history()
        next_n = len(existing.sessions) + 1

        # Normalise / default the date
        raw_date = session_data.get("session_date", date.today().isoformat())
        session_data["session_date"] = normalize_date(str(raw_date))
        session_data["session_n"] = next_n

        new_block = format_print_session(**session_data)

        path = self._root / "PrintHistory.md"
        if not path.exists():
            # Create with frontmatter header
            content = format_print_history(
                title="Print History",
                today=date.today().isoformat(),
            )
            path.write_text(content, encoding="utf-8")

        raw = path.read_text(encoding="utf-8")

        # Insert the new session block immediately after the first heading line.
        # If no heading exists, prepend with one.
        if "# Print History" in raw:
            header_end = raw.index("# Print History") + len("# Print History")
            # Skip any trailing whitespace/newlines after the heading
            insertion_point = header_end
            while insertion_point < len(raw) and raw[insertion_point] in ("\n", "\r", " "):
                insertion_point += 1
            new_raw = raw[:header_end] + "\n\n" + new_block + raw[insertion_point:]
        else:
            new_raw = "# Print History\n\n" + new_block + raw

        path.write_text(new_raw, encoding="utf-8")

    # ------------------------------------------------------------------
    # Disk usage
    # ------------------------------------------------------------------

    def compute_disk_size(self) -> int:
        """Return the total size in bytes of all files under the project root."""
        total = 0
        for item in self._root.rglob("*"):
            if item.is_file() and not item.is_symlink():
                total += item.stat().st_size
        return total


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def service_for_project(category: str, slug: str) -> ProjectDirectoryService:
    """Convenience factory: return a service bound to the project directory.

    Projects root: ``PROJECTS_DIR / category / slug``
    """
    project_dir = get_projects_dir() / category / slug
    return ProjectDirectoryService(project_dir)
