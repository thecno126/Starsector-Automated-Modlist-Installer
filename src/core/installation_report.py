"""
Installation progress tracking and reporting.
Extracted from installer.py to reduce file complexity.
"""

import time
from datetime import datetime


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
