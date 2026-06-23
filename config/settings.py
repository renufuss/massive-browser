"""Central application settings, paths and the run-configuration value object.

Keeping every tunable value and filesystem path in one module makes the rest of
the codebase free of magic strings and easy to test (Single Responsibility).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------- #
# Filesystem layout
# --------------------------------------------------------------------------- #
BASE_DIR: Path = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR: Path = BASE_DIR / "screenshots"
LOGS_DIR: Path = BASE_DIR / "logs"
REPORTS_DIR: Path = BASE_DIR / "reports"

# --------------------------------------------------------------------------- #
# Domain constants
# --------------------------------------------------------------------------- #
# Playwright engines the launcher will randomly choose from.
ENGINES: tuple[str, ...] = ("chromium", "firefox", "webkit")

# Instance-name prefixes; one is chosen at random per run so that every
# launched browser is named e.g. "Browser-001", "QA-Test-001" or "Monitor-001".
NAME_PREFIXES: tuple[str, ...] = ("Browser", "QA-Test", "Monitor")

# Default navigation timeout (milliseconds).
DEFAULT_TIMEOUT_MS: int = 30_000

# Sensible UI limits.
MAX_BROWSERS: int = 200
MAX_DELAY_SECONDS: float = 120.0
MAX_AUTOCLOSE_MINUTES: float = 1440.0  # 24h


@dataclass(slots=True)
class RunConfig:
    """Immutable description of a single "START" run, built from user input."""

    url: str
    count: int
    headless: bool
    delay_seconds: float
    auto_close_minutes: float = 0.0
    timeout_ms: int = DEFAULT_TIMEOUT_MS


def ensure_directories() -> None:
    """Create the output directories if they do not yet exist (idempotent)."""
    for directory in (SCREENSHOTS_DIR, LOGS_DIR, REPORTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)
