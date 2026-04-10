"""Markdown parsing and rendering helpers for project content.

Provides:
- render_markdown: converts CommonMark text to safe HTML
- parse_print_history: extracts structured sessions from PrintHistory.md
- format_print_session: formats a session dict into a PrintHistory.md entry
- Default template text for ProjectInfo.md and PrintHistory.md
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
# {title}

## About
{description}

## Source
- URL: 
- License: 
- Designer: 

## Print Profile
- Slicer: 
- Layer Height: 0.2mm
- Infill: 15% Gyroid
- Supports: No
- Bed Temp: 
- Nozzle Temp: 
- Notes: 

## Tags


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
