"""
Constants and configuration for the Modlist Installer application.
"""

import sys
from pathlib import Path

# Determine the base directory for config files
# PyInstaller sets _MEIPASS to the temp extraction folder
if hasattr(sys, '_MEIPASS'):
    # Running as PyInstaller bundle - use parent of _MEIPASS or executable location
    if sys.platform == "darwin" and '.app' in sys.executable:
        # macOS .app bundle - go up to folder containing .app
        BASE_DIR = Path(sys.executable).resolve().parent.parent.parent.parent
    else:
        # Windows/Linux - executable directory
        BASE_DIR = Path(sys.executable).resolve().parent
else:
    # Running as script - use project root (3 levels up from constants.py)
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# File paths
CONFIG_FILE = BASE_DIR / "config" / "modlist_config.json"
CATEGORIES_FILE = BASE_DIR / "config" / "categories.json"
LOG_FILE = BASE_DIR / "modlist_installer.log"
PREFS_FILE = BASE_DIR / "config" / "installer_prefs.json"
CACHE_DIR = BASE_DIR / "mod_cache"

# Ensure cache directory exists
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Ensure config directory exists
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Network & Download settings
URL_VALIDATION_TIMEOUT_HEAD = 6
REQUEST_TIMEOUT = 30
CHUNK_SIZE = 8192
MIN_FREE_SPACE_GB = 5

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
BACKOFF_MULTIPLIER = 2  # exponential backoff multiplier
CACHE_TIMEOUT = 3600  # 1 hour in seconds

# Thread pool settings
MAX_DOWNLOAD_WORKERS = 3
MAX_VALIDATION_WORKERS = 5

# UI settings
UI_BOTTOM_BUTTON_HEIGHT = 35
UI_MIN_WINDOW_WIDTH = 950
UI_MIN_WINDOW_HEIGHT = 670
UI_DEFAULT_WINDOW_WIDTH = 1050
UI_DEFAULT_WINDOW_HEIGHT = 720
UI_RIGHT_PANEL_WIDTH = 100
UI_RIGHT_PANEL_MINSIZE = 100
UI_LEFT_PANEL_MINSIZE = 550
