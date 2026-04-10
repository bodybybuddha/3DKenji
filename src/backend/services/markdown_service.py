"""Markdown parsing and rendering helpers for project content.

Provides:
- render_markdown: converts CommonMark text to safe HTML
- ProjectInfo frontmatter parsing and formatting helpers
  - format_project_info: creates new ProjectInfo with seeded frontmatter + body
  - ensure_project_info_frontmatter: adds frontmatter to existing ProjectInfo
- PrintHistory frontmatter parsing and formatting helpers
  - format_print_history: creates new PrintHistory with seeded frontmatter
  - ensure_print_history_frontmatter: adds frontmatter to existing PrintHistory
  - parse_print_history: extracts structured sessions from PrintHistory.md
  - format_print_session: formats a single session into markdown
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import mistune

# ---------------------------------------------------------------------------
# Constants: default file templates
# ---------------------------------------------------------------------------

PROJECT_INFO_TEMPLATE = """\
---
title: {title}
summary: {summary}
tags:
    - {default_tag}
designer: 
source_url: 
license: 
status: active
---

# About
{description}

## Print Profile
- Slicer: 
- Layer Height: 0.2mm
- Infill: 15% Gyroid
- Supports: No
- Bed Temp: 
- Nozzle Temp: 
- Notes: 

## Notes


## Changelog
- {today}: Project created
"""

PRINT_HISTORY_TEMPLATE = """\
# Print History

"""

# ---------------------------------------------------------------------------
# Markdown renderer (singleton; mistune 3.x)
# ---------------------------------------------------------------------------

_renderer = mistune.HTMLRenderer(escape=True)  # escape=True prevents raw HTML in user content
_md = mistune.create_markdown(renderer=_renderer, plugins=["table"])

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML-like frontmatter from markdown body.

    Supports a small, intentional subset:
    - ``key: value`` scalar lines
    - ``key:`` followed by ``- item`` list entries
    """
    if not text:
        return {}, ""

    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    metadata = parse_frontmatter(match.group(1))
    body = text[match.end():]
    return metadata, body.lstrip("\n")


def parse_frontmatter(raw: str) -> dict[str, Any]:
    """Parse a small YAML-like frontmatter block into a dictionary."""
    metadata: dict[str, Any] = {}
    current_list_key: str | None = None

    for original_line in raw.splitlines():
        line = original_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if current_list_key and stripped.startswith("- "):
            metadata.setdefault(current_list_key, [])
            metadata[current_list_key].append(stripped[2:].strip())
            continue

        current_list_key = None
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            metadata[key] = []
            current_list_key = key
        else:
            metadata[key] = value

    return metadata


def format_frontmatter(metadata: dict[str, Any]) -> str:
    """Serialize frontmatter metadata using a stable YAML-like format."""
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            if value:
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append("  - ")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def format_project_info(
    title: str,
    description: str,
    today: str,
    *,
    summary: str | None = None,
    tags: list[str] | None = None,
    designer: str = "",
    source_url: str = "",
    license_name: str = "",
    status: str = "active",
) -> str:
    """Return seeded ProjectInfo markdown with frontmatter and body."""
    tag_values = tags if tags is not None else ["3d-printing"]
    safe_summary = summary or description or "Add a short project summary here."
    metadata = {
        "title": title,
        "summary": safe_summary,
        "tags": tag_values,
        "designer": designer,
        "source_url": source_url,
        "license": license_name,
        "status": status,
    }
    frontmatter = format_frontmatter(metadata)
    body = PROJECT_INFO_TEMPLATE.format(
        title=title,
        summary=safe_summary,
        default_tag=tag_values[0] if tag_values else "3d-printing",
        description=description or "Add a description here.",
        today=today,
    )
    _, body_only = split_frontmatter(body)
    return frontmatter + "\n\n" + body_only.lstrip("\n")


def ensure_project_info_frontmatter(text: str, *, title: str) -> str:
    """Return ProjectInfo content with normalized frontmatter prepended.

    Existing frontmatter is preserved and merged with default keys.
    Existing markdown body content is preserved verbatim.
    """
    metadata, body = split_frontmatter(text)
    body = body if body else text

    default_summary = "Add a short project summary here."
    body_lines = [line.strip() for line in body.splitlines() if line.strip()]
    for line in body_lines:
        if not line.startswith("#") and not line.startswith("-"):
            default_summary = line
            break

    merged = {
        "title": title,
        "summary": default_summary,
        "tags": ["3d-printing"],
        "designer": "",
        "source_url": "",
        "license": "",
        "status": "active",
    }
    merged.update(metadata)
    merged["title"] = title
    if not isinstance(merged.get("tags"), list) or not merged.get("tags"):
        merged["tags"] = ["3d-printing"]

    return format_frontmatter(merged) + "\n\n" + body.lstrip("\n")


def format_print_history(
    title: str,
    today: str,
    *,
    created_date: str | None = None,
    printer_model: str = "",
    notes: str = "",
) -> str:
    """Return seeded PrintHistory markdown with frontmatter and body.

    Parameters
    ----------
    title:
        Project title to include in frontmatter.
    today:
        Date string (YYYY-MM-DD) for the created_date if not explicitly provided.
    created_date:
        Date when print history started. Defaults to today.
    printer_model:
        Optional default printer model for this project.
    notes:
        Optional general notes about the print history.

    Returns
    -------
        Frontmatter + "# Print History" header + empty session list.
    """
    if created_date is None:
        created_date = today

    metadata = {
        "project": title,
        "created_date": created_date,
        "last_print_date": "",
        "total_sessions": 0,
        "printer_model": printer_model,
        "notes": notes,
    }
    frontmatter = format_frontmatter(metadata)
    body = "\n# Print History\n"
    return frontmatter + "\n" + body


def ensure_print_history_frontmatter(text: str, *, title: str) -> str:
    """Return PrintHistory content with normalized frontmatter prepended.

    Existing frontmatter is preserved and merged with default keys.
    Existing print session body content is preserved verbatim.
    """
    metadata, body = split_frontmatter(text)
    body = body if body else text

    merged = {
        "project": title,
        "created_date": date.today().isoformat(),
        "last_print_date": "",
        "total_sessions": 0,
        "printer_model": "",
        "notes": "",
    }
    merged.update(metadata)
    merged["project"] = title
    if not isinstance(merged.get("total_sessions"), int):
        try:
            merged["total_sessions"] = int(merged.get("total_sessions", 0))
        except (ValueError, TypeError):
            merged["total_sessions"] = 0

    return format_frontmatter(merged) + "\n" + body.lstrip("\n")


def render_markdown(text: str) -> str:
    """Render *text* as CommonMark HTML.

    HTML tags in the source are escaped to prevent XSS.
    Returns an HTML string (not a full document).
    """
    if not text:
        return ""
    return _md(text)


# ---------------------------------------------------------------------------
# PrintHistory parsing
# ---------------------------------------------------------------------------

# Pattern for session headings: ## YYYY-MM-DD – Session N
_SESSION_HEAD_RE = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2})\s*[–—-]\s*Session\s+(\d+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Normalise date strings written in various formats to YYYY-MM-DD
_DATE_FORMATS = [
    r"(\d{4})-(\d{2})-(\d{2})",   # YYYY-MM-DD (canonical)
    r"(\d{2})/(\d{2})/(\d{4})",   # DD/MM/YYYY
    r"(\d{1,2})-(\d{1,2})-(\d{4})",  # D-M-YYYY
]


def normalize_date(raw: str) -> str:
    """Return a canonical YYYY-MM-DD string from *raw*, or today if unparseable."""
    raw = raw.strip()

    # Try YYYY-MM-DD first
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return raw

    # Try DD/MM/YYYY
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if m:
        day, month, year = m.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # Fall back to today
    return date.today().isoformat()


def parse_print_history(text: str) -> list[dict[str, Any]]:
    """Parse *text* (full PrintHistory.md content) into a list of session dicts.

    Returns sessions ordered newest-first (as they appear in the file).
    Each dict contains at minimum:
      - ``date``      – YYYY-MM-DD string
      - ``session_n`` – integer session number
      - ``body``      – full markdown text of the session body (str)
      - ``fields``    – dict of ``**Label**: value`` pairs extracted from the body

    Malformed sections are silently included with whatever fields were parseable.
    """
    sessions: list[dict[str, Any]] = []
    if not text:
        return sessions

    # Split on session headings
    parts = _SESSION_HEAD_RE.split(text)
    # parts layout: [pre, date1, n1, body1, date2, n2, body2, ...]
    # stride of 3 starting at index 1
    i = 1
    while i + 2 <= len(parts):
        raw_date = parts[i]
        raw_n = parts[i + 1]
        body = parts[i + 2].strip()

        session: dict[str, Any] = {
            "date": normalize_date(raw_date),
            "session_n": int(raw_n),
            "body": body,
            "fields": _extract_bold_fields(body),
        }
        sessions.append(session)
        i += 3

    return sessions


def _extract_bold_fields(body: str) -> dict[str, str]:
    """Extract ``**Label**: value`` pairs from a session body."""
    fields: dict[str, str] = {}
    pattern = re.compile(r"\*\*([^*]+)\*\*:\s*(.+)")
    for m in pattern.finditer(body):
        key = m.group(1).strip()
        value = m.group(2).strip()
        fields[key] = value
    return fields


def format_print_session(
    session_n: int,
    session_date: str,
    filament: str = "",
    duration: str = "",
    printer: str = "",
    result: str = "",
    scale: str = "100%",
    weight: str = "",
    profile_changes: str = "None",
    notes: str = "",
) -> str:
    """Return formatted markdown for a single PrintHistory session entry.

    The date is always normalised to YYYY-MM-DD before writing.
    """
    canon_date = normalize_date(session_date)

    lines: list[str] = [
        f"## {canon_date} – Session {session_n}",
        "",
    ]

    # Structured fields
    field_pairs = [
        ("Filament", filament),
        ("Duration", duration),
        ("Printer", printer),
        ("Result", result),
        ("Scale", scale),
    ]
    if weight:
        field_pairs.append(("Weight", weight))
    field_pairs.append(("Changes from profile", profile_changes))

    for label, value in field_pairs:
        lines.append(f"- **{label}**: {value}")

    if notes:
        lines.append("")
        lines.append("### Notes")
        lines.append(notes)

    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)
