"""Configuration file management with atomic writes to prevent corruption."""
import json
import tempfile
import os
from pathlib import Path

from .constants import CONFIG_FILE, CATEGORIES_FILE, PREFS_FILE, PRESETS_DIR


class ConfigManager:
    """Manages modlist, categories, preferences, and preset configurations."""
    
    def __init__(self, log_callback=None):
        self.config_file = CONFIG_FILE
        self.modlist_config_path = CONFIG_FILE  # Alias for export function
        self.categories_file = CATEGORIES_FILE
        self.prefs_file = PREFS_FILE
        self.presets_dir = PRESETS_DIR
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
    
    # ============================================================================
    # Preset Management
    # ============================================================================
    
    def list_presets(self):
        """List all available presets.
        
        Returns:
            list: [(preset_name, preset_path, has_lunalib), ...] sorted by name
        """
        if not self.presets_dir.exists():
            return []
        
        presets = []
        for preset_path in self.presets_dir.iterdir():
            if preset_path.is_dir():
                modlist_file = preset_path / "modlist_config.json"
                lunalib_folder = preset_path / "LunaSettings"
                if modlist_file.exists():
                    presets.append((
                        preset_path.name,
                        preset_path,
                        lunalib_folder.is_dir()
                    ))
        
        return sorted(presets, key=lambda x: x[0])
    
    def create_preset(self, preset_name, modlist_data, lunalib_data=None):
        """Create a new preset.
        
        Args:
            preset_name: Name of the preset (will be folder name)
            modlist_data: Modlist config dict
            lunalib_data: Optional dict of LunaSettings (mod_id: settings)
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            # Sanitize preset name
            import re
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', preset_name)
            if not safe_name or safe_name.strip() == '':
                return (False, "Preset name cannot be empty")
            
            # Validate modlist data before saving
            is_valid, validation_error = self.validate_preset(modlist_data)
            if not is_valid:
                return (False, f"Invalid modlist data: {validation_error}")
            
            preset_path = self.presets_dir / safe_name
            preset_path.mkdir(parents=True, exist_ok=True)
            
            # Save modlist_config.json
            modlist_file = preset_path / "modlist_config.json"
            self._atomic_save_json(modlist_file, modlist_data, ensure_ascii=False)
            
            # Save LunaSettings folder if provided (dict of mod_id: settings)
            if lunalib_data:
                lunalib_folder = preset_path / "LunaSettings"
                lunalib_folder.mkdir(exist_ok=True)
                for mod_id, settings in lunalib_data.items():
                    config_file = lunalib_folder / f"{mod_id}.json.data"
                    self._atomic_save_json(config_file, settings, ensure_ascii=False, indent=3)
            
            self._log(f"Created preset: {safe_name}", info=True)
            return (True, None)
            
        except Exception as e:
            error_msg = f"Failed to create preset: {e}"
            self._log(error_msg, error=True)
            return (False, error_msg)
    
    def load_preset(self, preset_name):
        """Load a preset.
        
        Args:
            preset_name: Name of the preset
            
        Returns:
            tuple: (modlist_data or None, lunalib_data or None, error_message or None)
        """
        try:
            preset_path = self.presets_dir / preset_name
            
            if not preset_path.exists():
                return (None, None, f"Preset '{preset_name}' not found")
            
            modlist_file = preset_path / "modlist_config.json"
            if not modlist_file.exists():
                return (None, None, f"Preset '{preset_name}' is missing modlist_config.json")
            
            with open(modlist_file, 'r', encoding='utf-8') as f:
                modlist_data = json.load(f)
            
            # Validate loaded data
            is_valid, validation_error = self.validate_preset(modlist_data)
            if not is_valid:
                return (None, None, f"Invalid preset data: {validation_error}")
            
            # Load LunaLib settings folder if exists
            lunalib_data = None
            lunalib_folder = preset_path / "LunaSettings"
            if lunalib_folder.is_dir():
                try:
                    lunalib_data = {}
                    for config_file in lunalib_folder.glob("*.json.data"):
                        mod_id = config_file.stem.replace(".json", "")
                        with open(config_file, 'r', encoding='utf-8') as f:
                            lunalib_data[mod_id] = json.load(f)
                except Exception as e:
                    self._log(f"Warning: Could not load LunaSettings: {e}", warning=True)
            
            return (modlist_data, lunalib_data, None)
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in preset '{preset_name}': {e}"
            self._log(error_msg, error=True)
            return (None, None, error_msg)
        except Exception as e:
            error_msg = f"Failed to load preset: {e}"
            self._log(error_msg, error=True)
            return (None, None, error_msg)
    
    def validate_preset(self, modlist_data):
        """Validate preset structure.
        
        Args:
            modlist_data: Modlist config dict
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not isinstance(modlist_data, dict):
            return (False, "Modlist data must be a dictionary")
        
        # Required keys
        required_keys = ['modlist_name', 'mods']
        for key in required_keys:
            if key not in modlist_data:
                return (False, f"Missing required key: '{key}'")
        
        # Validate mods list
        if not isinstance(modlist_data['mods'], list):
            return (False, "'mods' must be a list")
        
        # Validate each mod entry
        for idx, mod in enumerate(modlist_data['mods']):
            if not isinstance(mod, dict):
                return (False, f"Mod at index {idx} is not a dictionary")
            
            # Each mod should have at least 'name' and 'download_url'
            if 'name' not in mod:
                return (False, f"Mod at index {idx} missing 'name'")
            if 'download_url' not in mod:
                return (False, f"Mod at index {idx} missing 'download_url'")
        
        return (True, None)
    
    def delete_preset(self, preset_name):
        """Delete a preset.
        
        Args:
            preset_name: Name of the preset to delete
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            preset_path = self.presets_dir / preset_name
            
            if not preset_path.exists():
                return (False, f"Preset '{preset_name}' not found")
            
            # Delete all files in preset directory
            import shutil
            shutil.rmtree(preset_path)
            
            self._log(f"Deleted preset: {preset_name}", info=True)
            return (True, None)
            
        except Exception as e:
            error_msg = f"Failed to delete preset: {e}"
            self._log(error_msg, error=True)
            return (False, error_msg)
    
    def export_current_modlist_as_preset(self, preset_name, include_lunalib=False, starsector_path=None, overwrite=False):
        """Export the current modlist_config.json as a new preset.
        
        Args:
            preset_name: Name for the new preset
            include_lunalib: Whether to include current LunaSettings folder from Starsector
            starsector_path: Path to Starsector installation (required if include_lunalib=True)
            overwrite: If True, overwrite existing preset
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            # Validate preset name
            if not preset_name or not preset_name.strip():
                return (False, "Preset name cannot be empty")
            
            preset_name = preset_name.strip()
            
            # Check if preset already exists
            preset_path = self.presets_dir / preset_name
            if preset_path.exists():
                if not overwrite:
                    return (False, f"Preset '{preset_name}' already exists")
                # Remove existing preset directory before overwriting
                import shutil
                try:
                    shutil.rmtree(preset_path)
                except Exception as e:
                    return (False, f"Failed to remove existing preset: {e}")
            
            # Load current modlist config
            if not self.modlist_config_path.exists():
                return (False, "No modlist_config.json found to export")
            
            try:
                with open(self.modlist_config_path, 'r', encoding='utf-8') as f:
                    modlist_data = json.load(f)
            except Exception as e:
                return (False, f"Failed to read modlist_config.json: {e}")
            
            # Validate modlist data
            is_valid, error_msg = self.validate_preset(modlist_data)
            if not is_valid:
                return (False, f"Invalid modlist configuration: {error_msg}")
            
            # Create preset directory
            preset_path.mkdir(parents=True, exist_ok=True)
            
            # Write modlist_config.json
            modlist_file = preset_path / "modlist_config.json"
            with open(modlist_file, 'w', encoding='utf-8') as f:
                json.dump(modlist_data, f, indent=2)
            
            # Include LunaLib settings if requested
            if include_lunalib and starsector_path:
                from pathlib import Path
                import shutil
                starsector_path = Path(starsector_path)
                
                # LunaLib stores settings in saves/common/LunaSettings/
                lunasettings_source = starsector_path / "saves" / "common" / "LunaSettings"
                
                if lunasettings_source.is_dir():
                    try:
                        lunasettings_dest = preset_path / "LunaSettings"
                        lunasettings_dest.mkdir(exist_ok=True)
                        
                        copied_count = 0
                        for config_file in lunasettings_source.glob("*.json.data"):
                            shutil.copy2(config_file, lunasettings_dest / config_file.name)
                            copied_count += 1
                        
                        self._log(f"Included {copied_count} LunaLib config files from {lunasettings_source}", info=True)
                    except Exception as e:
                        self._log(f"Warning: Could not copy LunaLib settings: {e}", warning=True)
                else:
                    self._log(f"Warning: LunaSettings folder not found at {lunasettings_source}", warning=True)
            
            self._log(f"Exported current modlist as preset: {preset_name}", info=True)
            return (True, None)
            
        except Exception as e:
            error_msg = f"Failed to export preset: {e}"
            self._log(error_msg, error=True)
            return (False, error_msg)
    
    def patch_lunalib_config(self, preset_name, starsector_path):
        """Patch LunaLib settings in Starsector installation from preset.
        
        Copies .json.data files from preset's LunaSettings folder to the game's
        saves/common/LunaSettings folder. Creates backup before patching.
        
        Args:
            preset_name: Name of the preset containing LunaSettings folder
            starsector_path: Path to Starsector installation
            
        Returns:
            tuple: (success: bool, error_message: str or None, backup_path: Path or None)
        """
        import shutil
        from datetime import datetime
        
        try:
            # Validate inputs
            if not preset_name or not preset_name.strip():
                return (False, "Preset name cannot be empty", None)
            
            starsector_path = Path(starsector_path)
            if not starsector_path.exists():
                return (False, f"Starsector path not found: {starsector_path}", None)
            
            # Check preset has LunaSettings folder
            preset_path = self.presets_dir / preset_name
            preset_lunasettings = preset_path / "LunaSettings"
            
            if not preset_lunasettings.is_dir():
                return (False, f"Preset '{preset_name}' does not contain LunaSettings folder", None)
            
            # Target is saves/common/LunaSettings in game
            game_lunasettings = starsector_path / "saves" / "common" / "LunaSettings"
            
            # Create game LunaSettings folder if doesn't exist
            game_lunasettings.mkdir(parents=True, exist_ok=True)
            
            # Create backup of existing settings
            backup_path = None
            existing_files = list(game_lunasettings.glob("*.json.data"))
            if existing_files:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_folder = game_lunasettings / f".backup_{timestamp}"
                backup_folder.mkdir(exist_ok=True)
                
                for config_file in existing_files:
                    shutil.copy2(config_file, backup_folder / config_file.name)
                
                backup_path = backup_folder
                self._log(f"Created backup of {len(existing_files)} files at: {backup_path}", info=True)
            
            # Copy preset settings to game
            copied_count = 0
            for config_file in preset_lunasettings.glob("*.json.data"):
                dest_file = game_lunasettings / config_file.name
                shutil.copy2(config_file, dest_file)
                copied_count += 1
            
            self._log(f"✓ Patched {copied_count} LunaLib config files to {game_lunasettings}", info=True)
            return (True, None, backup_path)
        
        except Exception as e:
            error_msg = f"Unexpected error during LunaLib patch: {e}"
            self._log(error_msg, error=True)
            return (False, error_msg, None)

