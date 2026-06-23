"""Factory: random browser instances + their Playwright context options.

The single place that knows how to turn a random device profile into Playwright
``new_context`` keyword arguments. Add a new engine quirk here, nothing else
changes (Open/Closed).
"""

from __future__ import annotations

import json
import random
import uuid

from browser.device_profiles import COLOR_SCHEMES, LOCALES, PROFILES, TIMEZONES
from browser.models import BrowserInstance
from config.settings import ENGINES


class BrowserFactory:
    """Builds :class:`BrowserInstance` objects and their context options.

    One factory per run, with a single randomly-chosen name prefix so every
    instance shares a coherent name series (e.g. ``Monitor-001`` ...).
    """

    def __init__(self, name_prefix: str, rng: random.Random | None = None) -> None:
        self._prefix = name_prefix
        self._rng = rng or random.Random()

    def create_instance(self, index: int) -> BrowserInstance:
        """Create one fully-randomised (but not yet launched) instance."""
        locale, accept_language = self._rng.choice(LOCALES)
        return BrowserInstance(
            index=index,
            instance_id=uuid.uuid4().hex[:8],
            name=f"{self._prefix}-{index:03d}",
            engine=self._rng.choice(ENGINES),
            profile=self._rng.choice(PROFILES),
            locale=locale,
            accept_language=accept_language,
            timezone=self._rng.choice(TIMEZONES),
            color_scheme=self._rng.choice(COLOR_SCHEMES),
        )

    def build_context_options(self, instance: BrowserInstance) -> dict:
        """Engine-aware kwargs for ``browser.new_context``.

        ``is_mobile`` is Chromium-only; ``device_scale_factor``/``has_touch`` are
        unsupported on Firefox. They are added conditionally to avoid errors.
        """
        p = instance.profile
        options: dict = {
            "viewport": {"width": p.viewport_width, "height": p.viewport_height},
            "screen": {"width": p.screen_width, "height": p.screen_height},
            "user_agent": p.user_agent,
            "locale": instance.locale,
            "timezone_id": instance.timezone,
            "color_scheme": instance.color_scheme,
            "extra_http_headers": {"Accept-Language": instance.accept_language},
        }
        if instance.engine in ("chromium", "webkit"):
            options["device_scale_factor"] = p.device_scale_factor
            options["has_touch"] = p.has_touch
        if instance.engine == "chromium":
            options["is_mobile"] = p.is_mobile
        return options

    def build_init_script(self, instance: BrowserInstance) -> str:
        """JS injected before page scripts to align navigator with the profile."""
        languages = [part.split(";")[0] for part in instance.accept_language.split(",")]
        return (
            "(() => {"
            f"  try {{ Object.defineProperty(navigator, 'platform', "
            f"{{ get: () => {json.dumps(instance.profile.platform)} }}); }} catch (e) {{}}"
            f"  try {{ Object.defineProperty(navigator, 'languages', "
            f"{{ get: () => {json.dumps(languages)} }}); }} catch (e) {{}}"
            "})();"
        )
