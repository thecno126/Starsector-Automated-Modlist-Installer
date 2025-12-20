"""Configuration file management with atomic writes to prevent corruption."""
import json
import tempfile
import os
from pathlib import Path

from .constants import CONFIG_FILE, CATEGORIES_FILE, PREFS_FILE


class ConfigManager:
    """Manages modlist, categories, and preferences JSON files."""
    
    def __init__(self, log_callback=None):
        self.config_file = CONFIG_FILE
        self.categories_file = CATEGORIES_FILE
        self.prefs_file = PREFS_FILE
        self.log_callback = log_callback
    
    def _log(self, message, **kwargs):
        if self.log_callback:
            self.log_callback(message, **kwargs)
    
    def _atomic_save_json(self, file_path, data, indent=2, ensure_ascii=False):
        """Atomic write: temp file + replace to prevent corruption on crash."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=file_path.parent,
                prefix=f'.tmp_{file_path.stem}_',
                suffix='.json'
            )
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
                os.replace(temp_path, file_path)
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        except Exception as e:
            self._log(f"Error saving {file_path.name}: {e}", error=True)
    
    def load_modlist_config(self):
        """Load modlist config, returns default if missing/corrupt."""
        if not self.config_file.exists():
            return self.reset_to_default()
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self._log(f"Error loading config: {e}", error=True)
            return self.reset_to_default()
    
    def save_modlist_config(self, data):
        """Save modlist config atomically."""
        self._atomic_save_json(self.config_file, data, ensure_ascii=False)
    
    def reset_to_default(self):
        """Reset config to default and save."""
        default_config = {
            "modlist_name": "ASTRA",
            "version": "1.0",
            "starsector_version": "0.98a-RC8",
            "description": "Starsector Modlist",
            "mods": []
        }
        self.save_modlist_config(default_config)
        return default_config
    
    def load_categories(self):
        """Load categories or create defaults."""
        if self.categories_file.exists():
            try:
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self._log(f"Error loading categories: {e}", error=True)
        
        default = ["Required", "Graphics", "Gameplay", "Content", "Quality of Life", "Utility", "Uncategorized"]
        self.save_categories(default)
        return default
    
    def save_categories(self, categories):
        """Save categories atomically."""
        self._atomic_save_json(self.categories_file, categories, ensure_ascii=False)
    
    def load_preferences(self):
        """Load user preferences (Starsector path, theme, etc.)."""
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self._log(f"Error loading preferences: {e}", error=True)
        return {}
    
    def save_preferences(self, prefs):
        """Save preferences atomically."""
        self._atomic_save_json(self.prefs_file, prefs)

