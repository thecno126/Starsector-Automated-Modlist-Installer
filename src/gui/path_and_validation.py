"""
Path and Validation Controller - Handles path validation, disk space checks, and metadata refresh.

Extracted from MainWindow to improve code organization and maintainability.
"""

import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from datetime import datetime
import socket

from . import custom_dialogs
from core import MIN_FREE_SPACE_GB
from utils.path_validator import StarsectorPathValidator
from utils.error_messages import get_user_friendly_error
from utils.mod_utils import scan_installed_mods, check_missing_dependencies
from utils.backup_manager import BackupManager
from utils.theme import TriOSTheme


class PathAndValidation:
    """Handles path validation, checks, and metadata operations."""
    
    def __init__(self, parent):
        """Initialize the path and validation controller.
        
        Args:
            parent: Reference to MainWindow instance
        """
        self.parent = parent
        self._auto_detected = False
    
    def auto_detect_starsector(self):
        """Auto-detect Starsector installation using StarsectorPathValidator."""
        if self.parent.starsector_path.get():
            self._auto_detected = False
            return
        
        detected_path = StarsectorPathValidator.auto_detect()
        if detected_path:
            self.parent.starsector_path.set(str(detected_path))
            self._auto_detected = True
            self.parent.log(f"✓ Auto-detected Starsector installation: {detected_path}", info=True)
        else:
            self._auto_detected = False
            self.parent.log("⚠ Could not auto-detect Starsector. Please set path manually.", warning=True)
    
    def validate_starsector_path(self, path_str):
        """Validate Starsector installation path."""
        if not path_str:
            return False, "Path is empty"
        
        path = Path(path_str)
        if StarsectorPathValidator.validate(path):
            return True, "Valid"
        else:
            friendly_msg = get_user_friendly_error('invalid_path')
            return False, friendly_msg
    
    def check_disk_space(self, required_gb=MIN_FREE_SPACE_GB):
        """Check if there's enough free disk space."""
        if not self.parent.starsector_path.get():
            return True, ""
        
        has_space, free_gb = StarsectorPathValidator.check_disk_space(
            Path(self.parent.starsector_path.get()), required_gb
        )
        
        if not has_space:
            friendly_msg = get_user_friendly_error('disk_space')
            return False, friendly_msg
        return True, f"{free_gb:.1f}GB free"
    
    def select_starsector_path(self):
        """Open dialog to select Starsector folder."""
        folder = filedialog.askdirectory(
            title="Select Starsector installation folder",
            initialdir=self.parent.starsector_path.get() if self.parent.starsector_path.get() else str(Path.home())
        )
        
        if folder:
            is_valid, message = self.validate_starsector_path(folder)
            if is_valid:
                self.parent.starsector_path.set(folder)
                self.parent.save_preferences()
                self.update_path_status()
                self.parent.log(f"Starsector path set to: {folder}")
            else:
                custom_dialogs.showerror("Invalid Path", message)
    
    def on_path_changed(self):
        """Called when the path is manually edited by the user."""
        if hasattr(self.parent, '_path_validation_timer'):
            self.parent.root.after_cancel(self.parent._path_validation_timer)
        self.parent._path_validation_timer = self.parent.root.after(500, self.update_path_status)
    
    def update_path_status(self):
        """Update the path status label."""
        path = self.parent.starsector_path.get()
        
        if not path:
            self.parent.path_status_label.config(text="⚠ No Starsector installation detected", fg="#e67e22")
            return
        
        is_valid, message = self.validate_starsector_path(path)
        if is_valid:
            if self._auto_detected:
                self.parent.path_status_label.config(text="✓ Auto-detected", fg="#27ae60")
            else:
                self.parent.path_status_label.config(text="✓ Valid path", fg="#27ae60")
        else:
            self.parent.path_status_label.config(text=f"✗ {message}", fg="#e74c3c")
    
    def refresh_mod_metadata(self):
        """Manually refresh mod metadata from installed mods without full installation."""
        starsector_dir = self.parent.starsector_path.get()
        
        if not starsector_dir:
            custom_dialogs.showerror("Error", "Starsector path not set. Please configure it in settings.")
            return
        
        mods_dir = Path(starsector_dir) / "mods"
        
        if not mods_dir.exists():
            custom_dialogs.showerror("Error", f"Mods directory not found: {mods_dir}")
            return
        
        if self.parent.refresh_btn:
            self.parent.refresh_btn.config(state=tk.DISABLED, text="↻")
        
        self.parent.log("=" * 50)
        self.parent.log("Refreshing mod metadata from installed mods...")
        self.parent.log("Reloading modlist configuration...")
        
        try:
            self.parent.modlist_data = self.parent.config_manager.load_modlist_config()
            self.parent.installation_controller._update_mod_metadata_from_installed(mods_dir)
            self.parent.save_modlist_config()
            self.parent.mod_list_controller.display_modlist_info()
            self.parent.log("✓ Metadata refresh complete!")
            custom_dialogs.showsuccess("Success", "Mod metadata has been refreshed from installed mods")
        except Exception as e:
            self.parent.log(f"✗ Error refreshing metadata: {e}", error=True)
            custom_dialogs.showerror("Error", f"Failed to refresh metadata: {e}")
        finally:
            if self.parent.refresh_btn:
                self.parent.refresh_btn.config(state=tk.NORMAL, text="↻")
    
    def enable_all_installed_mods(self):
        """Enable all currently installed mods in Starsector by updating enabled_mods.json."""
        starsector_dir = self.parent.starsector_path.get()
        
        if not starsector_dir:
            custom_dialogs.showerror("Error", "Starsector path not set. Please configure it in settings.")
            return
        
        mods_dir = Path(starsector_dir) / "mods"
        
        if not mods_dir.exists():
            custom_dialogs.showerror("Error", f"Mods directory not found: {mods_dir}")
            return
        
        self.parent.log("=" * 50)
        self.parent.log("Enabling all installed mods...")
        
        try:
            all_installed_folders = []
            for folder, metadata in scan_installed_mods(mods_dir):
                all_installed_folders.append(folder.name)
                self.parent.log(f"  Found: {folder.name}", debug=True)
            
            if not all_installed_folders:
                custom_dialogs.showwarning("No Mods Found", "No mods were found in the mods directory.")
                return
            
            success = self.parent.mod_installer.update_enabled_mods(mods_dir, all_installed_folders, merge=False)
            
            if success:
                self.parent.log(f"✓ Enabled {len(all_installed_folders)} mod(s) in enabled_mods.json")
                custom_dialogs.showsuccess("Success", f"Successfully enabled {len(all_installed_folders)} mod(s).\n\nYour mods should now be active when you start Starsector.")
            else:
                custom_dialogs.showerror("Error", "Failed to update enabled_mods.json")
        except Exception as e:
            self.parent.log(f"✗ Error enabling mods: {e}", error=True)
            custom_dialogs.showerror("Error", f"Failed to enable mods: {e}")
    
    def restore_backup_dialog(self):
        """Show dialog to restore a backup."""
        starsector_dir = self.parent.starsector_path.get()
        if not starsector_dir:
            custom_dialogs.showerror("Error", "Starsector path not set. Please configure it in settings.")
            return
        
        try:
            backup_manager = BackupManager(starsector_dir)
            backups = backup_manager.list_backups()
            
            if not backups:
                custom_dialogs.showinfo("No Backups", "No backups found. Backups are created automatically before installation.")
                return
            
            dialog = tk.Toplevel(self.parent.root)
            dialog.title("Restore Backup")
            dialog.geometry("500x400")
            dialog.configure(bg=TriOSTheme.SURFACE)
            dialog.transient(self.parent.root)
            dialog.grab_set()
            
            tk.Label(dialog, text="Select a backup to restore:", font=("Arial", 12), 
                    bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).pack(pady=10)
            
            frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                                bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                                selectbackground=TriOSTheme.PRIMARY, selectforeground=TriOSTheme.SURFACE_DARK,
                                font=("Arial", 10))
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)
            
            for backup_path, metadata in backups:
                timestamp = metadata.get('timestamp', 'Unknown')
                try:
                    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                    formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    formatted = timestamp
                listbox.insert(tk.END, formatted)
            
            def on_restore():
                selection = listbox.curselection()
                if not selection:
                    custom_dialogs.showwarning("No Selection", "Please select a backup to restore.")
                    return
                
                idx = selection[0]
                backup_path, metadata = backups[idx]
                timestamp = metadata.get('timestamp', 'Unknown')
                
                if not custom_dialogs.askyesno("Confirm Restore", f"Restore backup from {timestamp}?\n\nThis will replace your current enabled_mods.json file."):
                    return
                
                success, error = backup_manager.restore_backup(backup_path)
                if success:
                    self.parent.log(f"✓ Backup restored from {timestamp}")
                    custom_dialogs.showsuccess("Success", "Backup restored successfully!\n\nYour mod configuration has been restored.")
                    dialog.destroy()
                else:
                    custom_dialogs.showerror("Restore Failed", f"Failed to restore backup:\n{error}")
            
            def on_delete():
                selection = listbox.curselection()
                if not selection:
                    custom_dialogs.showwarning("No Selection", "Please select a backup to delete.")
                    return
                
                idx = selection[0]
                backup_path, metadata = backups[idx]
                timestamp = metadata.get('timestamp', 'Unknown')
                
                if not custom_dialogs.askyesno("Confirm Delete", f"Delete backup from {timestamp}?"):
                    return
                
                success, error = backup_manager.delete_backup(backup_path)
                if success:
                    self.parent.log(f"✓ Deleted backup: {timestamp}")
                    listbox.delete(idx)
                    backups.pop(idx)
                    if not backups:
                        custom_dialogs.showinfo("No Backups", "All backups deleted.")
                        dialog.destroy()
                else:
                    custom_dialogs.showerror("Delete Failed", f"Failed to delete backup:\n{error}")
            
            btn_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
            btn_frame.pack(pady=10)
            
            from .ui_builder import _create_button
            restore_btn = _create_button(btn_frame, "Restore", on_restore, button_type="success")
            restore_btn.pack(side=tk.LEFT, padx=5)
            
            delete_btn = _create_button(btn_frame, "Delete", on_delete, button_type="danger")
            delete_btn.pack(side=tk.LEFT, padx=5)
            
            cancel_btn = _create_button(btn_frame, "Cancel", dialog.destroy, button_type="plain")
            cancel_btn.pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            self.parent.log(f"✗ Error accessing backups: {e}", error=True)
            custom_dialogs.showerror("Error", f"Failed to access backups:\n{e}")
    
    def run_pre_installation_checks(self, starsector_dir):
        """Run comprehensive pre-installation checks."""
        mods_dir = starsector_dir / "mods"
        
        # Check disk space
        has_space, space_msg = self.check_disk_space()
        if not has_space:
            self.parent.log(space_msg, warning=True)
            if not custom_dialogs.askyesno("Low Disk Space", f"{space_msg}\n\nContinue anyway?"):
                return False, "Installation cancelled due to low disk space"
        
        # Check write permissions
        try:
            test_file = mods_dir / ".write_test"
            mods_dir.mkdir(exist_ok=True)
            test_file.write_text("test")
            test_file.unlink()
            self.parent.log("✓ Write permissions verified", debug=True)
        except (PermissionError, OSError) as e:
            friendly_msg = get_user_friendly_error('permission_denied')
            return False, f"{friendly_msg}\n\nTechnical: {e}"
        
        # Check internet connection
        try:
            socket.create_connection(("www.google.com", 80), timeout=3)
            self.parent.log("✓ Internet connection verified", debug=True)
        except (socket.error, socket.timeout):
            self.parent.log("⚠ Internet connection may be unavailable", warning=True)
            if not custom_dialogs.askyesno("Connection Warning", "Could not verify internet connection.\n\nContinue anyway?"):
                return False, "Installation cancelled due to connection issues"
        
        # Check dependencies
        dependency_issues = self._check_dependencies(mods_dir)
        if dependency_issues:
            issues_text = "\n".join([f"  • {mod_name}: missing {', '.join(deps)}" 
                                     for mod_name, deps in dependency_issues.items()])
            self.parent.log(f"⚠ Dependency issues found:\n{issues_text}", warning=True)
            
            message = f"Some mods have missing dependencies:\n\n{issues_text}\n\nThese dependencies will be installed if they're in the modlist.\n\nContinue?"
            if not custom_dialogs.askyesno("Missing Dependencies", message):
                return False, "Installation cancelled due to missing dependencies"
        else:
            self.parent.log("✓ No dependency issues found", debug=True)
        
        return True, None
    
    def _check_dependencies(self, mods_dir):
        """Check for missing dependencies in the modlist."""
        for mod in self.parent.modlist_data.get('mods', []):
            mod_id = mod.get('mod_id')
            if not mod_id:
                continue
            if 'dependencies' not in mod:
                mod['dependencies'] = []
        
        installed_mod_ids = set()
        for folder, metadata in scan_installed_mods(mods_dir):
            mod_id = metadata.get('id')
            if mod_id:
                installed_mod_ids.add(mod_id)
        
        modlist_mod_ids = {m.get('mod_id') for m in self.parent.modlist_data.get('mods', []) if m.get('mod_id')}
        all_available_ids = installed_mod_ids | modlist_mod_ids
        
        missing_deps_by_id = check_missing_dependencies(self.parent.modlist_data.get('mods', []), all_available_ids)
        
        dependency_issues = {}
        for mod_id, missing_deps in missing_deps_by_id.items():
            mod = next((m for m in self.parent.modlist_data.get('mods', []) if m.get('mod_id') == mod_id), None)
            if mod:
                mod_name = mod.get('name', mod_id)
                dependency_issues[mod_name] = missing_deps
        
        return dependency_issues
