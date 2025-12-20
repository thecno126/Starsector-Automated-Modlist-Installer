import json
import shutil
from pathlib import Path
from datetime import datetime
from model_types import BackupResult
from utils.symbols import LogSymbols


class BackupManager:
    """Manages backup and restore of enabled_mods.json with automatic retention policy."""
    
    DEFAULT_RETENTION_COUNT = 4
    
    def __init__(self, starsector_path, log_callback=None, retention_count=None):
        """Initialize BackupManager.
        
        Args:
            starsector_path: Path to Starsector installation
            log_callback: Optional callback function for logging (signature: log(message, **kwargs))
            retention_count: Number of backups to keep (default: 4)
        """
        self.starsector_path = Path(starsector_path)
        self.backup_dir = self.starsector_path / "modlist_backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.log_callback = log_callback
        self.retention_count = retention_count if retention_count is not None else self.DEFAULT_RETENTION_COUNT
    
    def _log(self, message, **kwargs):
        """Internal logging helper."""
        if self.log_callback:
            self.log_callback(message, **kwargs)
    
    def create_backup(self, backup_mods=False) -> BackupResult:
        """Backup enabled_mods.json and optionally list installed mods."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        try:
            # Always backup enabled_mods.json
            enabled_mods_src = self.starsector_path / "mods" / "enabled_mods.json"
            if enabled_mods_src.exists():
                shutil.copy2(enabled_mods_src, backup_path / "enabled_mods.json")
            
            # Optionally backup mods folder (create list of installed mods)
            if backup_mods:
                mods_dir = self.starsector_path / "mods"
                if mods_dir.exists():
                    mod_list = []
                    for item in mods_dir.iterdir():
                        if item.is_dir():
                            mod_list.append(item.name)
                    
                    # Save list of installed mods
                    with open(backup_path / "installed_mods.json", 'w', encoding='utf-8') as f:
                        json.dump({"mods": mod_list, "timestamp": timestamp}, f, indent=2)
            
            # Save backup metadata
            metadata = {
                "timestamp": timestamp,
                "backup_mods": backup_mods,
                "starsector_path": str(self.starsector_path)
            }
            with open(backup_path / "backup_info.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            self._log(f"{LogSymbols.SUCCESS} Created backup: {backup_path.name}", success=True)
            
            # Automatically cleanup old backups
            deleted_count = self.cleanup_old_backups(keep_count=self.retention_count)
            if deleted_count > 0:
                self._log(f"  Cleaned up {deleted_count} old backup(s) (keeping last {self.retention_count})", info=True)
            
            return BackupResult(backup_path, True, None)
            
        except Exception as e:
            self._log(f"{LogSymbols.ERROR} Backup creation failed: {e}", error=True)
            return BackupResult(None, False, str(e))
    
    def list_backups(self):
        """Returns list of (backup_path, metadata_dict), newest first."""
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir() and backup_path.name.startswith("backup_"):
                metadata_file = backup_path / "backup_info.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        backups.append((backup_path, metadata))
                    except (json.JSONDecodeError, IOError):
                        # Skip invalid backups
                        continue
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x[1].get('timestamp', ''), reverse=True)
        return backups
    
    def restore_backup(self, backup_path):
        """Restore enabled_mods.json from backup. Returns (success, error)."""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            self._log(f"{LogSymbols.ERROR} Backup not found: {backup_path}", error=True)
            return False, "Backup directory not found"
        
        try:
            # Restore enabled_mods.json
            enabled_mods_backup = backup_path / "enabled_mods.json"
            if enabled_mods_backup.exists():
                enabled_mods_dest = self.starsector_path / "mods" / "enabled_mods.json"
                shutil.copy2(enabled_mods_backup, enabled_mods_dest)
                self._log(f"{LogSymbols.SUCCESS} Restored backup: {backup_path.name}", success=True)
            else:
                self._log(f"{LogSymbols.ERROR} enabled_mods.json not found in backup", error=True)
                return False, "enabled_mods.json not found in backup"
            
            return True, None
            
        except Exception as e:
            self._log(f"{LogSymbols.ERROR} Restore failed: {e}", error=True)
            return False, str(e)
    
    def delete_backup(self, backup_path):
        """Delete a specific backup. Returns (success, error)."""
        backup_path = Path(backup_path)
        
        try:
            if backup_path.exists() and backup_path.parent == self.backup_dir:
                shutil.rmtree(backup_path)
                self._log(f"{LogSymbols.SUCCESS} Deleted backup: {backup_path.name}", info=True)
                return True, None
            else:
                return False, "Invalid backup path"
        except Exception as e:
            self._log(f"{LogSymbols.ERROR} Delete backup failed: {e}", error=True)
            return False, str(e)
    
    def cleanup_old_backups(self, keep_count=None):
        """Delete old backups, keeping most recent. Returns deleted count.
        
        Args:
            keep_count: Number of backups to keep (default: use retention_count from init)
        """
        if keep_count is None:
            keep_count = self.retention_count
            
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            return 0
        
        deleted_count = 0
        for backup_path, _ in backups[keep_count:]:
            success, _ = self.delete_backup(backup_path)
            if success:
                deleted_count += 1
        
        return deleted_count
