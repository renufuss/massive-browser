"""cx_Freeze MSI build - no admin, no WiX/dotnet needed (uses stdlib msilib).

Builds a per-user installer (installs to %LOCALAPPDATA%\\Programs, so the app can
write its logs/screenshots next to the exe without admin). (c) 2026 Renufus.

    python setup_msi.py build_exe   # freeze + verify
    python setup_msi.py bdist_msi   # -> dist\\Multi Browser Launcher-1.0.0-win64.msi
"""

import os

from cx_Freeze import Executable, setup

_cache = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")

build_exe_options = {
    "packages": ["playwright", "PySide6", "asyncio"],
    "include_files": [(_cache, "ms-playwright"), ("assets/icon.ico", "assets/icon.ico")],
    "include_msvcr": True,
    "zip_include_packages": ["*"],
    "zip_exclude_packages": ["playwright", "PySide6"],  # spawn node / load Qt from disk
}

bdist_msi_options = {
    "upgrade_code": "{BE151A86-ABC0-4D54-8B60-AE4DF23EA5FF}",
    "initial_target_dir": r"[LocalAppDataFolder]\Programs\Multi Browser Launcher",
    "all_users": False,
    "add_to_path": False,
    "install_icon": "assets/icon.ico",
}

setup(
    name="Multi Browser Launcher",
    version="1.0.0",
    author="Renufus",
    description="Multi Browser Launcher - open many browsers at once",
    options={"build_exe": build_exe_options, "bdist_msi": bdist_msi_options},
    executables=[
        Executable(
            "main.py",
            base="gui",
            target_name="MultiBrowserLauncher.exe",
            icon="assets/icon.ico",
            copyright="Copyright (c) 2026 Renufus",
            shortcut_name="Multi Browser Launcher",
            shortcut_dir="ProgramMenuFolder",
        )
    ],
)
