"""Theme mode normalization and operating-system appearance detection helpers."""

from __future__ import annotations

import configparser
import importlib
import os
import platform
import plistlib
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastest_route.presentation.gui.app.views.theme_support.tokens import (
        GuiAppearance,
        GuiThemeMode,
    )


def normalize_theme_mode(*, preference: str) -> GuiThemeMode:
    """Normalize theme preferences into explicit light, dark, or auto mode."""
    normalized = preference.strip().lower()
    if normalized in {"auto", "system"}:
        return "auto"
    if normalized == "dark":
        return "dark"
    if normalized == "light":
        return "light"
    return "auto"


def should_follow_system_theme(*, preference: str) -> bool:
    """Check whether a configured theme preference should follow OS appearance."""
    return normalize_theme_mode(preference=preference) == "auto"


def detect_system_appearance() -> GuiAppearance | None:
    """Detect the OS appearance preference for light or dark mode."""
    system = platform.system().lower()
    if system == "darwin":
        return _detect_macos_appearance()
    if system == "windows":
        return _detect_windows_appearance()
    return _detect_linux_appearance()


def _appearance_from_text(value: str) -> GuiAppearance | None:
    """Infer a light or dark appearance value from free-form theme text."""
    normalized = value.strip().lower()
    if not normalized:
        return None
    if "dark" in normalized:
        return "dark"
    if "light" in normalized:
        return "light"
    return None


def _detect_macos_appearance() -> GuiAppearance | None:
    """Detect macOS appearance from the global preferences plist."""
    plist_path = Path.home() / "Library" / "Preferences" / ".GlobalPreferences.plist"
    try:
        payload = plistlib.loads(plist_path.read_bytes())
    except (OSError, plistlib.InvalidFileException):
        return None
    if not isinstance(payload, dict):
        return None
    style = payload.get("AppleInterfaceStyle")
    if not isinstance(style, str):
        return "light"
    detected = _appearance_from_text(style)
    return detected if detected is not None else "light"


def _detect_windows_appearance() -> GuiAppearance | None:
    """Detect Windows appearance using the user theme registry keys."""
    winreg_module = _load_winreg_module()
    if winreg_module is None:
        return None

    hkey_current_user = getattr(winreg_module, "HKEY_CURRENT_USER", None)
    open_key = getattr(winreg_module, "OpenKey", None)
    query_value_ex = getattr(winreg_module, "QueryValueEx", None)
    close_key = getattr(winreg_module, "CloseKey", None)
    if hkey_current_user is None:
        return None
    if not callable(open_key) or not callable(query_value_ex) or not callable(close_key):
        return None

    try:
        key = open_key(
            hkey_current_user,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        query_result = query_value_ex(key, "AppsUseLightTheme")
        close_key(key)
        if not isinstance(query_result, tuple) or not query_result:
            return None
        value = query_result[0]
        if isinstance(value, int) and value == 0:
            return "dark"
        if isinstance(value, int) and value == 1:
            return "light"
        return None
    except OSError:
        return None


def _detect_linux_appearance() -> GuiAppearance | None:
    """Detect Linux appearance from environment hints and GTK settings files."""
    env_theme = os.environ.get("GTK_THEME", "")
    env_detected = _appearance_from_text(env_theme)
    if env_detected is not None:
        return env_detected

    settings_paths = [
        Path.home() / ".config" / "gtk-4.0" / "settings.ini",
        Path.home() / ".config" / "gtk-3.0" / "settings.ini",
        Path("/etc/gtk-4.0/settings.ini"),
        Path("/etc/gtk-3.0/settings.ini"),
    ]
    parser = configparser.ConfigParser()
    for settings_path in settings_paths:
        try:
            if not settings_path.is_file():
                continue
            parser.clear()
            parser.read(settings_path, encoding="utf-8")
        except (OSError, configparser.Error):
            continue
        if not parser.has_section("Settings"):
            continue

        prefers_dark = parser.get("Settings", "gtk-application-prefer-dark-theme", fallback="")
        prefers_dark_normalized = prefers_dark.strip().lower()
        if prefers_dark_normalized in {"1", "true", "yes", "on"}:
            return "dark"
        if prefers_dark_normalized in {"0", "false", "no", "off"}:
            return "light"

        theme_name = parser.get("Settings", "gtk-theme-name", fallback="")
        theme_detected = _appearance_from_text(theme_name)
        if theme_detected is not None:
            return theme_detected
    return None


def _load_winreg_module() -> ModuleType | None:
    """Load the Windows registry module when available."""
    try:
        module = importlib.import_module("winreg")
    except ModuleNotFoundError:
        return None
    if not isinstance(module, ModuleType):
        return None
    return module
