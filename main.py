"""Multi Browser Launcher - application entry point.

Copyright (c) 2026 Renufus. All rights reserved.

Run with:  python main.py
"""

from __future__ import annotations

import os
import sys

# Frozen build: point Playwright at the browsers bundled inside the app, before
# anything imports playwright.
if getattr(sys, "frozen", False):
    os.environ.setdefault(
        "PLAYWRIGHT_BROWSERS_PATH",
        os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "ms-playwright"),
    )


def _selftest() -> int:
    # ponytail: frozen-build smoke check -- can the bundled Playwright find and
    # launch a browser? Run: MultiBrowserLauncher.exe --selftest
    import asyncio

    from playwright.async_api import async_playwright

    import tempfile

    async def _run() -> None:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            await browser.close()

    asyncio.run(_run())
    msg = "SELFTEST OK | PLAYWRIGHT_BROWSERS_PATH=" + str(os.environ.get("PLAYWRIGHT_BROWSERS_PATH"))
    print(msg)
    # Marker file so a windowed (no-console) build can still be verified.
    try:
        with open(os.path.join(tempfile.gettempdir(), "mbl_selftest.txt"), "w", encoding="utf-8") as fh:
            fh.write(msg)
    except OSError:
        pass
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from config.settings import APP_NAME, APP_VERSION, ensure_directories, resource_path
    from ui.main_window import MainWindow

    ensure_directories()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Renufus")
    icon = resource_path("assets/icon.ico")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
