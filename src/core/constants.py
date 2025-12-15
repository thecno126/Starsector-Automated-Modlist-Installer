"""
Constants and configuration for the Modlist Installer application.
Includes InstallationReport class for tracking installation progress.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

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


# ============================================================================
# Installation Report
# ============================================================================

class InstallationReport:
    """Tracks installation progress and results for detailed reporting."""
    
    def __init__(self):
        self.errors = []
        self.skipped = []
        self.installed = []
        self.updated = []
        self.start_time = time.time()
    
    def add_error(self, mod_name, error_msg, url):
        """Record an installation error."""
        self.errors.append({
            'mod': mod_name,
            'error': error_msg,
            'url': url,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    
    def add_skipped(self, mod_name, reason, version=None):
        """Record a skipped mod (already installed and up-to-date)."""
        self.skipped.append({
            'mod': mod_name,
            'reason': reason,
            'version': version
        })
    
    def add_installed(self, mod_name, version=None):
        """Record a newly installed mod."""
        self.installed.append({
            'mod': mod_name,
            'version': version
        })
    
    def add_updated(self, mod_name, old_version, new_version):
        """Record an updated mod."""
        self.updated.append({
            'mod': mod_name,
            'old_version': old_version,
            'new_version': new_version
        })
    
    def get_duration(self):
        """Get installation duration in seconds."""
        return time.time() - self.start_time
    
    def generate_summary(self):
        """Generate a formatted summary report."""
        duration = self.get_duration()
        minutes, seconds = divmod(int(duration), 60)
        
        summary = [
            "\n" + "─" * 60,
            f"✓ Installation Complete ({minutes}m {seconds}s)",
            "─" * 60,
            f"✓ {len(self.installed)} installed | ↑ {len(self.updated)} updated | ○ {len(self.skipped)} skipped | ✗ {len(self.errors)} errors"
        ]
        
        if self.installed:
            summary.append("\nNewly Installed:")
            for item in self.installed:
                version = f" v{item['version']}" if item['version'] else ""
                summary.append(f"  ✓ {item['mod']}{version}")
        
        if self.updated:
            summary.append("\nUpdated:")
            for item in self.updated:
                summary.append(f"  ↑ {item['mod']}: {item['old_version']} → {item['new_version']}")
        
        if self.errors:
            summary.append("\nErrors:")
            for item in self.errors:
                summary.append(f"  ✗ {item['mod']}: {item['error']}")
                summary.append(f"    URL: {item['url']}")
        
        return "\n".join(summary)
    
    def has_errors(self):
        """Check if any errors occurred."""
        return len(self.errors) > 0
    
    def get_total_processed(self):
        """Get total number of mods processed."""
        return len(self.installed) + len(self.updated) + len(self.skipped) + len(self.errors)
