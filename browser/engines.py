"""Browser engines/brands the launcher can drive, plus machine detection.

Playwright only *bundles* three engines: Chromium, Firefox, WebKit. Branded
Chromium browsers (Edge, Chrome, Opera, Brave, Vivaldi) are launched against the
copy installed on the machine -- via Playwright's ``channel`` (Edge/Chrome) or an
``executable_path`` (the rest). They are NOT bundled, so we only add the ones we
actually find installed; the three bundled engines are always available.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Engine:
    name: str  # display/brand, e.g. "Edge"
    browser_type: str  # Playwright type: "chromium" | "firefox" | "webkit"
    channel: str | None = None  # Playwright channel, e.g. "msedge", "chrome"
    executable: str | None = None  # explicit browser exe (Opera/Brave/Vivaldi)


# Always available -- bundled with the app.
BUNDLED: tuple[Engine, ...] = (
    Engine("Chromium", "chromium"),
    Engine("Firefox", "firefox"),
    Engine("WebKit", "webkit"),
)


def _first_existing(*paths: str) -> str | None:
    for path in paths:
        expanded = os.path.expandvars(path)
        if os.path.isfile(expanded):
            return expanded
    return None


def available_engines() -> list[Engine]:
    """The bundled three plus any branded Chromium browser found installed."""
    engines = list(BUNDLED)
    pf = "%ProgramFiles%"
    pf86 = "%ProgramFiles(x86)%"
    lad = "%LOCALAPPDATA%"

    if _first_existing(
        rf"{pf86}\Microsoft\Edge\Application\msedge.exe",
        rf"{pf}\Microsoft\Edge\Application\msedge.exe",
    ) or shutil.which("msedge"):
        engines.append(Engine("Edge", "chromium", channel="msedge"))

    if _first_existing(
        rf"{pf}\Google\Chrome\Application\chrome.exe",
        rf"{pf86}\Google\Chrome\Application\chrome.exe",
        rf"{lad}\Google\Chrome\Application\chrome.exe",
    ) or shutil.which("chrome"):
        engines.append(Engine("Chrome", "chromium", channel="chrome"))

    opera = _first_existing(rf"{lad}\Programs\Opera\opera.exe", rf"{pf}\Opera\opera.exe")
    if opera:
        engines.append(Engine("Opera", "chromium", executable=opera))

    brave = _first_existing(
        rf"{pf}\BraveSoftware\Brave-Browser\Application\brave.exe",
        rf"{pf86}\BraveSoftware\Brave-Browser\Application\brave.exe",
    )
    if brave:
        engines.append(Engine("Brave", "chromium", executable=brave))

    vivaldi = _first_existing(
        rf"{lad}\Vivaldi\Application\vivaldi.exe",
        rf"{pf}\Vivaldi\Application\vivaldi.exe",
    )
    if vivaldi:
        engines.append(Engine("Vivaldi", "chromium", executable=vivaldi))

    return engines
