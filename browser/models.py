"""Runtime state for a single launched browser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from browser.device_profiles import DeviceProfile


@dataclass(slots=True)
class BrowserInstance:
    """Identity + randomised config + live Playwright handles for one browser.

    The chosen ``profile`` carries viewport/screen/UA/platform/scale/touch; the
    four loose fields are the per-run random picks layered on top of it.
    """

    index: int
    instance_id: str
    name: str
    engine: str
    profile: DeviceProfile
    locale: str
    accept_language: str
    timezone: str
    color_scheme: str

    status: str = "Pending"
    start_time: str = ""
    error: str = ""

    # Live Playwright handles (None until launched, reset to None on close).
    browser: Any = None
    context: Any = None
    page: Any = None
