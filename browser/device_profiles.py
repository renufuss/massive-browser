"""Catalogue of 60+ realistic device profiles plus randomisation pools.

Every profile bundles a viewport, a matching user-agent, a navigator platform,
a default scale factor and touch/mobile flags. Locale, language, timezone and
colour-scheme are kept as separate pools so the factory can mix them in for
extra entropy (the spec asks each browser to randomise those independently).
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Re-usable user-agent templates
# --------------------------------------------------------------------------- #
CHROME_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
EDGE_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.2478.51"
)
FIREFOX_WIN = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"
)
CHROME_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
SAFARI_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
)
FIREFOX_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0"
)
CHROME_LINUX = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
FIREFOX_LINUX = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
)
IPHONE_SAFARI = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)
IPAD_SAFARI = (
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    """One immutable device fingerprint."""

    name: str
    category: str  # "Desktop" | "Mobile" | "Tablet"
    user_agent: str
    viewport_width: int
    viewport_height: int
    screen_width: int
    screen_height: int
    device_scale_factor: float
    is_mobile: bool
    has_touch: bool
    platform: str


# --------------------------------------------------------------------------- #
# Small builder helpers keep the table below readable & typo-resistant
# --------------------------------------------------------------------------- #
def _desktop(name: str, ua: str, w: int, h: int, dsf: float, platform: str) -> DeviceProfile:
    return DeviceProfile(name, "Desktop", ua, w, h, w, h, dsf, False, False, platform)


def _android(name: str, model: str, android: str, w: int, h: int, dsf: float) -> DeviceProfile:
    ua = (
        f"Mozilla/5.0 (Linux; Android {android}; {model}) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
    )
    return DeviceProfile(name, "Mobile", ua, w, h, w, h, dsf, True, True, "Linux armv8l")


def _iphone(name: str, w: int, h: int, dsf: float) -> DeviceProfile:
    return DeviceProfile(name, "Mobile", IPHONE_SAFARI, w, h, w, h, dsf, True, True, "iPhone")


def _ipad(name: str, w: int, h: int, dsf: float) -> DeviceProfile:
    return DeviceProfile(name, "Tablet", IPAD_SAFARI, w, h, w, h, dsf, True, True, "iPad")


# --------------------------------------------------------------------------- #
# The catalogue (22 desktop + ~46 mobile/tablet = 68 total)
# --------------------------------------------------------------------------- #
PROFILES: tuple[DeviceProfile, ...] = (
    # ---- Desktop -------------------------------------------------------- #
    _desktop("Windows 11 - Chrome FHD", CHROME_WIN, 1920, 1080, 1.0, "Win32"),
    _desktop("Windows 11 - Edge FHD", EDGE_WIN, 1920, 1080, 1.0, "Win32"),
    _desktop("Windows 10 - Firefox HD", FIREFOX_WIN, 1366, 768, 1.0, "Win32"),
    _desktop("Windows 11 - Chrome QHD", CHROME_WIN, 2560, 1440, 1.0, "Win32"),
    _desktop("Windows 11 - Edge Scaled", EDGE_WIN, 1536, 864, 1.25, "Win32"),
    _desktop("Windows 10 - Chrome WXGA+", CHROME_WIN, 1440, 900, 1.0, "Win32"),
    _desktop("Windows 11 - Chrome 4K", CHROME_WIN, 3840, 2160, 1.5, "Win32"),
    _desktop("Windows 10 - Edge HD", EDGE_WIN, 1280, 720, 1.0, "Win32"),
    _desktop("Windows 11 - Firefox WUXGA", FIREFOX_WIN, 1920, 1200, 1.0, "Win32"),
    _desktop("Windows 11 - Chrome HD+", CHROME_WIN, 1600, 900, 1.0, "Win32"),
    _desktop("Windows 11 - Chrome Laptop", CHROME_WIN, 1496, 967, 1.25, "Win32"),
    _desktop("macOS - Safari WXGA+", SAFARI_MAC, 1440, 900, 2.0, "MacIntel"),
    _desktop("macOS - Chrome WSXGA+", CHROME_MAC, 1680, 1050, 2.0, "MacIntel"),
    _desktop("macOS - Safari Retina", SAFARI_MAC, 2560, 1600, 2.0, "MacIntel"),
    _desktop("macOS - Firefox 14\"", FIREFOX_MAC, 1512, 982, 2.0, "MacIntel"),
    _desktop("macOS - Chrome MacBook Air", CHROME_MAC, 1280, 800, 2.0, "MacIntel"),
    _desktop("macOS - Safari MacBook Pro 16", SAFARI_MAC, 1728, 1117, 2.0, "MacIntel"),
    _desktop("Linux - Chrome FHD", CHROME_LINUX, 1920, 1080, 1.0, "Linux x86_64"),
    _desktop("Linux - Firefox HD+", FIREFOX_LINUX, 1600, 900, 1.0, "Linux x86_64"),
    _desktop("Linux - Chrome SXGA", CHROME_LINUX, 1280, 1024, 1.0, "Linux x86_64"),
    _desktop("Chromebook - Chrome HD", CHROME_LINUX, 1366, 768, 1.0, "Linux x86_64"),
    _desktop("Linux - Firefox HiDPI QHD", FIREFOX_LINUX, 2560, 1440, 1.5, "Linux x86_64"),
    # ---- Samsung -------------------------------------------------------- #
    _android("Samsung Galaxy S24", "SM-S921B", "14", 360, 780, 3.0),
    _android("Samsung Galaxy S24 Ultra", "SM-S928B", "14", 412, 915, 3.5),
    _android("Samsung Galaxy S23", "SM-S911B", "14", 360, 780, 3.0),
    _android("Samsung Galaxy S22", "SM-S901B", "13", 360, 780, 3.0),
    _android("Samsung Galaxy A55", "SM-A556B", "14", 384, 832, 2.75),
    _android("Samsung Galaxy A54", "SM-A546B", "14", 384, 854, 2.625),
    _android("Samsung Galaxy A35", "SM-A356B", "14", 384, 832, 2.75),
    _android("Samsung Galaxy Z Fold5", "SM-F946B", "14", 344, 882, 3.0),
    _android("Samsung Galaxy Z Flip5", "SM-F731B", "14", 360, 748, 3.0),
    _android("Samsung Galaxy Note20", "SM-N981B", "13", 412, 883, 2.625),
    _android("Samsung Galaxy S21 FE", "SM-G990B", "13", 360, 780, 3.0),
    # ---- Google Pixel --------------------------------------------------- #
    _android("Google Pixel 8", "Pixel 8", "14", 412, 915, 2.625),
    _android("Google Pixel 8 Pro", "Pixel 8 Pro", "14", 448, 998, 3.0),
    _android("Google Pixel 7", "Pixel 7", "14", 412, 915, 2.625),
    _android("Google Pixel 7a", "Pixel 7a", "14", 412, 915, 2.625),
    _android("Google Pixel 6", "Pixel 6", "13", 412, 915, 2.625),
    _android("Google Pixel 6a", "Pixel 6a", "13", 412, 915, 2.625),
    _android("Google Pixel Fold", "Pixel Fold", "14", 412, 884, 2.625),
    # ---- Other Android -------------------------------------------------- #
    _android("OnePlus 12", "CPH2581", "14", 412, 919, 3.0),
    _android("OnePlus 11", "CPH2449", "14", 412, 919, 3.0),
    _android("Xiaomi 14", "23127PN0CG", "14", 393, 873, 2.75),
    _android("Xiaomi Redmi Note 13", "23129RAA4G", "14", 393, 873, 2.75),
    _android("Oppo Find X7", "PHZ110", "14", 412, 915, 3.0),
    _android("Vivo X100", "V2309A", "14", 392, 872, 3.0),
    _android("Realme GT5", "RMX3820", "14", 384, 854, 2.8),
    _android("Motorola Edge 50", "XT2407", "14", 412, 915, 2.5),
    _android("Nothing Phone 2", "A065", "14", 412, 915, 2.625),
    _android("Asus Zenfone 10", "AI2302", "13", 360, 780, 3.0),
    _android("Sony Xperia 1 V", "XQ-DQ72", "13", 411, 960, 3.5),
    _android("Huawei P60", "LNA-AL00", "12", 360, 780, 3.0),
    # ---- iPhone --------------------------------------------------------- #
    _iphone("iPhone 15", 393, 852, 3.0),
    _iphone("iPhone 15 Pro", 393, 852, 3.0),
    _iphone("iPhone 15 Pro Max", 430, 932, 3.0),
    _iphone("iPhone 15 Plus", 430, 932, 3.0),
    _iphone("iPhone 14", 390, 844, 3.0),
    _iphone("iPhone 14 Pro", 393, 852, 3.0),
    _iphone("iPhone 13", 390, 844, 3.0),
    _iphone("iPhone 13 mini", 375, 812, 3.0),
    _iphone("iPhone SE (2022)", 375, 667, 2.0),
    _iphone("iPhone 12", 390, 844, 3.0),
    _iphone("iPhone 11", 414, 896, 2.0),
    # ---- iPad ----------------------------------------------------------- #
    _ipad("iPad Pro 11\"", 834, 1194, 2.0),
    _ipad("iPad Pro 12.9\"", 1024, 1366, 2.0),
    _ipad("iPad Air", 820, 1180, 2.0),
    _ipad("iPad Mini", 744, 1133, 2.0),
    _ipad("iPad 10th Gen", 820, 1180, 2.0),
)


# --------------------------------------------------------------------------- #
# Randomisation pools (mixed in on top of the chosen profile)
# --------------------------------------------------------------------------- #
# (locale, Accept-Language header)
LOCALES: tuple[tuple[str, str], ...] = (
    ("en-US", "en-US,en;q=0.9"),
    ("en-GB", "en-GB,en;q=0.9"),
    ("id-ID", "id-ID,id;q=0.9,en;q=0.8"),
    ("ja-JP", "ja-JP,ja;q=0.9,en;q=0.8"),
    ("de-DE", "de-DE,de;q=0.9,en;q=0.8"),
    ("fr-FR", "fr-FR,fr;q=0.9,en;q=0.8"),
    ("es-ES", "es-ES,es;q=0.9,en;q=0.8"),
    ("pt-BR", "pt-BR,pt;q=0.9,en;q=0.8"),
    ("zh-CN", "zh-CN,zh;q=0.9,en;q=0.8"),
    ("ko-KR", "ko-KR,ko;q=0.9,en;q=0.8"),
    ("ru-RU", "ru-RU,ru;q=0.9,en;q=0.8"),
    ("it-IT", "it-IT,it;q=0.9,en;q=0.8"),
    ("nl-NL", "nl-NL,nl;q=0.9,en;q=0.8"),
    ("tr-TR", "tr-TR,tr;q=0.9,en;q=0.8"),
    ("ar-SA", "ar-SA,ar;q=0.9,en;q=0.8"),
    ("hi-IN", "hi-IN,hi;q=0.9,en;q=0.8"),
    ("th-TH", "th-TH,th;q=0.9,en;q=0.8"),
    ("vi-VN", "vi-VN,vi;q=0.9,en;q=0.8"),
    ("pl-PL", "pl-PL,pl;q=0.9,en;q=0.8"),
    ("sv-SE", "sv-SE,sv;q=0.9,en;q=0.8"),
)

TIMEZONES: tuple[str, ...] = (
    "America/New_York", "America/Los_Angeles", "America/Chicago", "America/Denver",
    "America/Sao_Paulo", "America/Toronto", "Europe/London", "Europe/Paris",
    "Europe/Berlin", "Europe/Madrid", "Europe/Moscow", "Asia/Jakarta",
    "Asia/Tokyo", "Asia/Singapore", "Asia/Shanghai", "Asia/Seoul",
    "Asia/Kolkata", "Asia/Dubai", "Asia/Bangkok", "Australia/Sydney",
    "Pacific/Auckland", "Africa/Cairo",
)

COLOR_SCHEMES: tuple[str, ...] = ("light", "dark", "no-preference")


assert len(PROFILES) >= 50, "Specification requires at least 50 device profiles."
