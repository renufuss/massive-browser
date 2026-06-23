"""Plain data models shared across the browser package.

These dataclasses carry no behaviour; they are passed between the factory, the
manager and the UI. Keeping them dependency-free avoids import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RandomConfig:
    """The randomised fingerprint applied to one browser context."""

    viewport_width: int
    viewport_height: int
    screen_width: int
    screen_height: int
    device_scale_factor: float
    is_mobile: bool
    has_touch: bool
    user_agent: str
    platform: str
    locale: str
    accept_language: str
    timezone: str
    color_scheme: str


@dataclass(slots=True)
class BrowserInstance:
    """Runtime state for a single launched browser.

    The first block of fields is serialisable metadata (safe to read from the
    GUI thread / export to CSV). The trailing ``browser``/``context``/``page``
    handles are live Playwright objects owned by the asyncio worker thread.
    """

    index: int
    instance_id: str
    name: str
    engine: str
    profile_name: str
    config: RandomConfig
    status: str = "Pending"
    start_time: str = ""
    error: str = ""

    # Live Playwright handles (None until launched, reset to None on close).
    browser: Any = None
    context: Any = None
    page: Any = None
