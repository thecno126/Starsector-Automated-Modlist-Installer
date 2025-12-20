# -*- coding: utf-8 -*-
"""Application constants, paths, and InstallationReport tracker."""
import sys
import time
from pathlib import Path
from datetime import datetime
from utils.symbols import LogSymbols


# Base directory resolution (script vs PyInstaller bundle)
if hasattr(sys, '_MEIPASS'):
    # PyInstaller: _MEIPASS is temp extraction folder
    if sys.platform == "darwin" and '.app' in sys.executable:
        # macOS .app: executable is Contents/MacOS/app_name, go up to parent of .app
        BASE_DIR = Path(sys.executable).resolve().parent.parent.parent.parent
    else:
        # Windows/Linux: executable directory
        BASE_DIR = Path(sys.executable).resolve().parent
else:
    # Script mode: project root (3 levels up from src/core/constants.py)
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Paths
CONFIG_FILE = BASE_DIR / "config" / "modlist_config.json"
CATEGORIES_FILE = BASE_DIR / "config" / "categories.json"
PREFS_FILE = BASE_DIR / "config" / "installer_prefs.json"
LOG_FILE = BASE_DIR / "modlist_installer.log"
CACHE_DIR = BASE_DIR / "mod_cache"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Network timeouts & download
URL_VALIDATION_TIMEOUT_HEAD = 6
REQUEST_TIMEOUT = 30
CHUNK_SIZE = 8192
MIN_FREE_SPACE_GB = 5

# Retry & backoff
MAX_RETRIES = 3
RETRY_DELAY = 2
BACKOFF_MULTIPLIER = 2
CACHE_TIMEOUT = 3600

# Thread pools
MAX_DOWNLOAD_WORKERS = 3
MAX_VALIDATION_WORKERS = 5

# UI dimensions
UI_BOTTOM_BUTTON_HEIGHT = 32
UI_MIN_WINDOW_WIDTH = 950
UI_MIN_WINDOW_HEIGHT = 670
UI_DEFAULT_WINDOW_WIDTH = 1050
UI_DEFAULT_WINDOW_HEIGHT = 720
UI_RIGHT_PANEL_WIDTH = 100
UI_RIGHT_PANEL_MINSIZE = 100
UI_LEFT_PANEL_MINSIZE = 550


class InstallationReport:
    """Tracks installation progress: errors, skipped, installed, updated mods."""
    
    def __init__(self):
        self.errors = []
        self.skipped = []
        self.installed = []
        self.updated = []
        self.start_time = time.time()
    
    def add_error(self, mod_name, error_msg, url):
        self.errors.append({
            'mod': mod_name,
            'error': error_msg,
            'url': url,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    
    def add_skipped(self, mod_name, reason, version=None):
        self.skipped.append({'mod': mod_name, 'reason': reason, 'version': version})
    
    def add_installed(self, mod_name, version=None):
        self.installed.append({'mod': mod_name, 'version': version})
    
    def add_updated(self, mod_name, old_version, new_version):
        self.updated.append({'mod': mod_name, 'old_version': old_version, 'new_version': new_version})
    
    def get_duration(self):
        return time.time() - self.start_time
    
    def generate_summary(self):
        """Generate formatted summary report."""
        duration = self.get_duration()
        minutes, seconds = divmod(int(duration), 60)
        
        # Summary stats
        installed_count = len(self.installed)
        updated_count = len(self.updated)
        skipped_count = len(self.skipped)
        errors_count = len(self.errors)
        
        summary = [
            "\n" + "-" * 60,
            f"{LogSymbols.SUCCESS} Installation Complete ({minutes}m {seconds}s)",
            "-" * 60,
            f"{LogSymbols.SUCCESS} {installed_count} installed | "
            f"{LogSymbols.UPDATED} {updated_count} updated | "
            f"{LogSymbols.NOT_INSTALLED} {skipped_count} skipped | "
            f"{LogSymbols.ERROR} {errors_count} errors"
        ]
        
        if self.installed:
            summary.append("\nNewly Installed:")
            for item in self.installed:
                version = f" v{item['version']}" if item['version'] else ""
                summary.append(f"  {LogSymbols.SUCCESS} {item['mod']}{version}")
        
        if self.updated:
            summary.append("\nUpdated:")
            for item in self.updated:
                summary.append(f"  {LogSymbols.UPDATED} {item['mod']}: {item['old_version']} → {item['new_version']}")
        
        if self.errors:
            summary.append("\nErrors:")
            for item in self.errors:
                summary.append(f"  {LogSymbols.ERROR} {item['mod']}: {item['error']}")
                summary.append(f"    URL: {item['url']}")
        
        return "\n".join(summary)
    
    def has_errors(self):
        return len(self.errors) > 0
    
    def get_total_processed(self):
        return len(self.installed) + len(self.updated) + len(self.skipped) + len(self.errors)
