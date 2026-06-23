"""Factory that turns randomness into concrete browser instances + context options.

The factory is the single place that knows *how* to translate a randomly chosen
device profile into Playwright ``new_context`` keyword arguments. Centralising
this honours the Open/Closed principle: add a new engine quirk here, nothing
else changes.
"""

from __future__ import annotations

import json
import random
import uuid

from browser.device_profiles import COLOR_SCHEMES, LOCALES, PROFILES, TIMEZONES
from browser.models import BrowserInstance, RandomConfig
from config.settings import ENGINES


class BrowserFactory:
    """Builds :class:`BrowserInstance` objects and their Playwright options.

    A fresh factory is created per run with a single randomly-chosen name
    prefix, so every instance in one run shares a coherent name series
    (e.g. ``Monitor-001`` ... ``Monitor-010``).
    """

    def __init__(self, name_prefix: str, rng: random.Random | None = None) -> None:
        self._prefix = name_prefix
        self._rng = rng or random.Random()

    # ------------------------------------------------------------------ #
    # Instance creation
    # ------------------------------------------------------------------ #
    def create_instance(self, index: int) -> BrowserInstance:
        """Create one fully-randomised (but not yet launched) instance."""
        engine = self._rng.choice(ENGINES)
        profile = self._rng.choice(PROFILES)
        locale, accept_language = self._rng.choice(LOCALES)
        timezone = self._rng.choice(TIMEZONES)
        color_scheme = self._rng.choice(COLOR_SCHEMES)

        config = RandomConfig(
            viewport_width=profile.viewport_width,
            viewport_height=profile.viewport_height,
            screen_width=profile.screen_width,
            screen_height=profile.screen_height,
            device_scale_factor=profile.device_scale_factor,
            is_mobile=profile.is_mobile,
            has_touch=profile.has_touch,
            user_agent=profile.user_agent,
            platform=profile.platform,
            locale=locale,
            accept_language=accept_language,
            timezone=timezone,
            color_scheme=color_scheme,
        )

        return BrowserInstance(
            index=index,
            instance_id=uuid.uuid4().hex[:8],
            name=f"{self._prefix}-{index:03d}",
            engine=engine,
            profile_name=profile.name,
            config=config,
        )

    # ------------------------------------------------------------------ #
    # Playwright option translation
    # ------------------------------------------------------------------ #
    def build_context_options(self, instance: BrowserInstance) -> dict:
        """Return engine-aware keyword arguments for ``browser.new_context``.

        Some context options are engine-specific. ``is_mobile`` is Chromium
        only, while ``device_scale_factor``/``has_touch`` are unsupported on
        Firefox. We therefore add them conditionally to avoid runtime errors.
        """
        cfg = instance.config
        options: dict = {
            "viewport": {"width": cfg.viewport_width, "height": cfg.viewport_height},
            "screen": {"width": cfg.screen_width, "height": cfg.screen_height},
            "user_agent": cfg.user_agent,
            "locale": cfg.locale,
            "timezone_id": cfg.timezone,
            "color_scheme": cfg.color_scheme,
            "extra_http_headers": {"Accept-Language": cfg.accept_language},
        }

        if instance.engine in ("chromium", "webkit"):
            options["device_scale_factor"] = cfg.device_scale_factor
            options["has_touch"] = cfg.has_touch
        if instance.engine == "chromium":
            options["is_mobile"] = cfg.is_mobile

        return options

    def build_init_script(self, instance: BrowserInstance) -> str:
        """JS injected before page scripts to align navigator with the profile.

        Wrapped in try/catch so a stricter engine never breaks navigation.
        """
        cfg = instance.config
        languages = [part.split(";")[0] for part in cfg.accept_language.split(",")]
        return (
            "(() => {"
            f"  try {{ Object.defineProperty(navigator, 'platform', "
            f"{{ get: () => {json.dumps(cfg.platform)} }}); }} catch (e) {{}}"
            f"  try {{ Object.defineProperty(navigator, 'languages', "
            f"{{ get: () => {json.dumps(languages)} }}); }} catch (e) {{}}"
            "})();"
        )
