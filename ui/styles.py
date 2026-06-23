"""Shared UI styling helpers (kept separate to avoid import cycles)."""

from __future__ import annotations

# Status -> colour mapping used by both the dashboard table and the preview grid.
STATUS_COLORS: dict[str, str] = {
    "Pending": "#9aa0a6",
    "Launched": "#1a73e8",
    "Running": "#188038",
    "Timeout": "#e37400",
    "Load Error": "#d93025",
    "Launch Failed": "#d93025",
    "Context Error": "#d93025",
    "Crashed": "#a50e0e",
    "Stopped": "#5f6368",
}


def status_color(status: str) -> str | None:
    """Return the hex colour associated with a status, or None."""
    return STATUS_COLORS.get(status)
