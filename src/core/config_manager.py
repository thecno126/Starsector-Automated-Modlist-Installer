"""Configuration and data management for modlist."""
import json
import tempfile
import os
from pathlib import Path

from .constants import CONFIG_FILE, CATEGORIES_FILE, PREFS_FILE


class ConfigManager:
    """Manages configuration files (modlist, categories, preferences)."""
    
    def __init__(self):
        self.config_file = CONFIG_FILE
        self.categories_file = CATEGORIES_FILE
        self.prefs_file = PREFS_FILE
    
    def _atomic_save_json(self, file_path, data, indent=2, ensure_ascii=False):
        """Save JSON data to file atomically to prevent corruption.
        
        Args:
            file_path: Path object for the target file
            data: Data to serialize to JSON
            indent: JSON indentation (default: 2)
            ensure_ascii: Whether to escape non-ASCII characters (default: False)
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: write to temp file then replace
            temp_fd, temp_path = tempfile.mkstemp(
                dir=file_path.parent,
                prefix=f'.tmp_{file_path.stem}_',
                suffix='.json'
            )
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
                # Atomic replace (preserves file if crash during write)
                os.replace(temp_path, file_path)
            except Exception:
                # Cleanup temp file if something failed
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise
        except Exception as e:
            print(f"Error saving {file_path.name}: {e}")
    
    def load_modlist_config(self):
        """Load modlist configuration from JSON file.
        
        Returns:
            dict: Modlist configuration data
        """
        if not self.config_file.exists():
            return self.reset_to_default()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.reset_to_default()
    
    def save_modlist_config(self, data):
        """Save modlist configuration to JSON file atomically.
        
        Args:
            data: Modlist configuration data to save
        """
        self._atomic_save_json(self.config_file, data, ensure_ascii=False)
    
    
    def reset_to_default(self):
        """Reset configuration to default values and save.
        
        Returns:
            dict: Default modlist configuration
        """
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
        """Load categories from file or create default ones.
        
        Returns:
            list: List of category names
        """
        if self.categories_file.exists():
            try:
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading categories: {e}")
        
        # Default categories
        default = ["Required", "Graphics", "Gameplay", "Content", "Quality of Life", "Utility", "Uncategorized"]
        self.save_categories(default)
        return default
    
    def save_categories(self, categories):
        """Save categories to file atomically.
        
        Args:
            categories: List of category names
        """
        self._atomic_save_json(self.categories_file, categories, ensure_ascii=False)
    
    
    def load_preferences(self):
        """Load user preferences (last Starsector path, theme, etc.)
        
        Returns:
            dict: User preferences
        """
        if self.prefs_file.exists():
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading preferences: {e}")
        return {}
    
    def save_preferences(self, prefs):
        """Save user preferences atomically.
        
        Args:
            prefs: Dictionary of preferences to save
        """
        self._atomic_save_json(self.prefs_file, prefs)

