# PyInstaller onedir spec. Bundles PySide6 + Playwright + the browser binaries
# so the built app needs no manual Python/Playwright install. (c) 2026 Renufus.
import os

from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.hooks import collect_all

pw_datas, pw_bins, pw_hidden = collect_all("playwright")

# Bundle the Playwright browser cache (chromium/firefox/webkit). Run
# `python -m playwright install` first so this folder exists.
_cache = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")
browsers = Tree(_cache, prefix="ms-playwright") if os.path.isdir(_cache) else []

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=pw_bins,
    datas=pw_datas + [("assets/icon.ico", "assets")],
    hiddenimports=pw_hidden,
    noarchive=False,
)
a.datas += browsers

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MultiBrowserLauncher",
    console=False,
    icon="assets/icon.ico",
    version="packaging/version.txt",
)
coll = COLLECT(exe, a.binaries, a.datas, name="MultiBrowserLauncher")
