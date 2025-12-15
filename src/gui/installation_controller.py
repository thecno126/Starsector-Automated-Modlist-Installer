"""
Installation Controller - Handles mod installation, downloads, and extraction.

Extracted from MainWindow to improve code organization and maintainability.
"""

import tkinter as tk
from pathlib import Path
import threading
import concurrent.futures
import time
import os

from core import (
    MAX_DOWNLOAD_WORKERS,
    ModInstaller,
    InstallationReport
)
from core.installer import validate_mod_urls, is_mod_up_to_date, resolve_mod_dependencies
from .dialogs import show_google_drive_confirmation_dialog
from . import custom_dialogs
from utils.mod_utils import scan_installed_mods, is_mod_name_match
from utils.backup_manager import BackupManager


class InstallationController:
    """Handles all installation-related operations."""
    
    def __init__(self, parent):
        """Initialize the installation controller.
        
        Args:
            parent: Reference to MainWindow instance for UI updates and logging
        """
        self.parent = parent
        self.mod_installer = parent.mod_installer
        
        # Installation state
        self.is_installing = False
        self.is_paused = False
        self.download_futures = []
        self.current_executor = None
        self.downloaded_temp_files = []
        self.current_mod_name = parent.current_mod_name
    
    def start_installation(self):
        """Start the installation process."""
        if self.is_installing:
            return
        
        if not self.parent.starsector_path.get():
            response = custom_dialogs.askyesno(
                "Starsector Path Required",
                "Starsector installation folder not set.\n\nWould you like to select it now?"
            )
            if response:
                from tkinter import filedialog
                folder = filedialog.askdirectory(title="Select Starsector folder")
                if folder:
                    is_valid, message = self.parent.validate_starsector_path(folder)
                    if is_valid:
                        self.parent.starsector_path.set(folder)
                        self.parent.save_preferences()
                        self.parent.log(f"Starsector path set: {folder}")
                    else:
                        custom_dialogs.showerror("Invalid Path", message)
                        return
                else:
                    return
            else:
                return
        
        starsector_dir = Path(self.parent.starsector_path.get())
        
        is_valid, message = self.parent.validate_starsector_path(str(starsector_dir))
        if not is_valid:
            custom_dialogs.showerror("Invalid Path", message)
            return
        
        if not self.parent.modlist_data:
            custom_dialogs.showerror("Error", "No modlist configuration loaded")
            return
        
        # Run comprehensive pre-installation checks
        self.parent.log("\n" + "─" * 60)
        self.parent.log("Running pre-installation checks...")
        check_success, check_error = self.parent._run_pre_installation_checks(starsector_dir)
        if not check_success:
            custom_dialogs.showerror("Pre-Installation Check Failed", check_error)
            return
        self.parent.log("✓ All pre-installation checks passed")
        
        # Validate URLs asynchronously
        self.parent.log("Validating mod URLs (this may take a moment)...")
        self.parent.install_modlist_btn.config(text="Validating URLs...")
        
        self._validate_urls_async()
    
    def _validate_urls_async(self):
        """Run URL validation in background thread and wait for results."""
        validation_result = {'data': None, 'error': None}
        
        def run_validation():
            try:
                validation_result['data'] = validate_mod_urls(
                    self.parent.modlist_data['mods'], 
                    progress_callback=None
                )
            except Exception as e:
                validation_result['error'] = str(e)
        
        validation_thread = threading.Thread(target=run_validation, daemon=True)
        validation_thread.start()
        
        max_wait = 60
        start_time = time.time()
        
        def check_validation_status():
            if validation_result['error']:
                custom_dialogs.showerror("Validation Error", f"Failed to validate URLs: {validation_result['error']}")
                self.parent.install_modlist_btn.config(text="Install Modlist")
                return
            
            if validation_result['data']:
                self.parent.install_modlist_btn.config(text="Install Modlist")
                self._continue_installation_after_validation(validation_result['data'])
                return
            
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                custom_dialogs.showerror("Validation Timeout", "URL validation took too long. Try again or check your internet connection.")
                self.parent.install_modlist_btn.config(text="Install Modlist")
                return
            
            self.parent.root.after(100, check_validation_status)
        
        self.parent.root.after(100, check_validation_status)
    
    def _continue_installation_after_validation(self, results):
        """Continue installation after URL validation completes."""
        if not results:
            return
        
        if not self._show_validation_summary(results):
            return
        
        starsector_dir = Path(self.parent.starsector_path.get())
        mods_dir = starsector_dir / "mods"
        
        if mods_dir.exists():
            self.parent.log("\nChecking for outdated mods...")
            outdated = self.mod_installer.detect_outdated_mods(mods_dir, self.parent.modlist_data['mods'])
            
            if outdated:
                self.parent.log(f"\n⚠ Found {len(outdated)} outdated mod(s):", warning=True)
                for mod_info in outdated:
                    self.parent.log(f"  • {mod_info['name']}: v{mod_info['installed_version']} → v{mod_info['expected_version']}", warning=True)
                
                msg = f"{len(outdated)} mod(s) will be updated:\n\n"
                for mod_info in outdated[:5]:
                    msg += f"• {mod_info['name']}: v{mod_info['installed_version']} → v{mod_info['expected_version']}\n"
                if len(outdated) > 5:
                    msg += f"... +{len(outdated) - 5} more\n"
                
                custom_dialogs.showinfo("Outdated Mods", msg)
        else:
            self.parent.log(f"\nMods directory not found at {mods_dir}, skipping version checks", debug=True)
        
        self.is_installing = True
        self.is_paused = False
        self.parent.install_modlist_btn.config(state=tk.DISABLED, text="Installing...")
        self.parent.pause_install_btn.config(state=tk.NORMAL)
        self.parent.install_progress_bar['value'] = 0
        
        thread = threading.Thread(target=self.install_mods, daemon=True)
        thread.start()
    
    def _show_validation_summary(self, results):
        """Show validation results summary and prompt user to continue."""
        github_mods = results['github']
        gdrive_mods = results['google_drive']
        other_domains = results['other']
        failed_list = results['failed']
        
        total_other = sum(len(mods) for mods in other_domains.values())
        self.parent.log(f"GitHub: {len(github_mods)}, Google Drive: {len(gdrive_mods)}, Other: {total_other}, Failed: {len(failed_list)}")
        
        if github_mods or gdrive_mods or other_domains or failed_list:
            action = custom_dialogs.show_validation_report(
                self.parent.root,
                github_mods,
                gdrive_mods,
                other_domains,
                failed_list
            )
            
            if action == 'cancel':
                self.parent.log("Installation cancelled by user")
                return False
        
        return True
    
    def install_mods(self):
        """Install the mods from the modlist using parallel downloads and sequential extraction."""
        self._install_mods_internal(self.parent.modlist_data['mods'])
    
    def install_specific_mods(self, mod_names, temp_mods=None, skip_gdrive_check=False):
        """Install only specific mods by name.
        
        Args:
            mod_names: List of mod names to install
            temp_mods: Optional list of mod dictionaries with temporary URLs
            skip_gdrive_check: If True, skip Google Drive verification
        """
        if temp_mods:
            mods_to_install = temp_mods
        else:
            mods_to_install = [mod for mod in self.parent.modlist_data['mods'] if mod.get('name') in mod_names]
        
        if not mods_to_install:
            custom_dialogs.showerror("Error", "No mods found to install")
            return
        
        self.is_installing = True
        self.is_paused = False
        self.parent.install_modlist_btn.config(state=tk.DISABLED, text="Installing...")
        self.parent.pause_install_btn.config(state=tk.NORMAL)
        self.parent.install_progress_bar['value'] = 0
        
        def run_specific_installation():
            self._install_mods_internal(mods_to_install, skip_gdrive_check=skip_gdrive_check)
        
        thread = threading.Thread(target=run_specific_installation, daemon=True)
        thread.start()
    
    def _install_mods_internal(self, mods_to_install, skip_gdrive_check=False):
        """Internal method to install a list of mods."""
        report = InstallationReport()
        mods_dir = Path(self.parent.starsector_path.get()) / "mods"
        total_mods = len(mods_to_install)

        self.parent.log(f"\nStarting installation of {total_mods} mod{'s' if total_mods > 1 else ''}...")
        self.parent.log("─" * 60)
        
        # Create automatic backup
        self.parent.log("Creating backup of enabled_mods.json...")
        try:
            backup_manager = BackupManager(self.parent.starsector_path.get())
            backup_path, success, error = backup_manager.create_backup(backup_mods=False)
            if success:
                self.parent.log(f"✓ Backup created: {backup_path.name}")
                deleted = backup_manager.cleanup_old_backups(keep_count=5)
                if deleted > 0:
                    self.parent.log(f"  Cleaned up {deleted} old backup(s)", debug=True)
            else:
                self.parent.log(f"⚠ Backup failed: {error}", warning=True)
        except Exception as e:
            self.parent.log(f"⚠ Could not create backup: {e}", warning=True)

        # Update metadata from installed mods
        self.parent.log("Scanning installed mods for metadata...")
        self._update_mod_metadata_from_installed(mods_dir)
        
        # Scan currently installed mods
        installed_mods_dict = {}
        for folder, metadata in scan_installed_mods(mods_dir):
            mod_id = metadata.get('id')
            if mod_id:
                installed_mods_dict[mod_id] = metadata

        # Resolve dependencies
        self.parent.log("Resolving mod dependencies...")
        mods_to_install = resolve_mod_dependencies(mods_to_install, installed_mods_dict)
        self.parent.log(f"  ✓ Dependencies resolved, installation order optimized")

        # Pre-filter: Check which mods are already installed
        mods_to_download = []
        pre_skipped = 0
        
        for mod in mods_to_install:
            mod_name = mod.get('name', 'Unknown')
            mod_version = mod.get('mod_version')
            
            is_up_to_date, installed_version = is_mod_up_to_date(mod_name, mod_version, mods_dir)
            
            if is_up_to_date:
                version_str = f" (v{installed_version})" if installed_version else ""
                report.add_skipped(mod_name, "already up-to-date", installed_version)
                pre_skipped += 1
            else:
                if installed_version is not None:
                    status = f"update ({installed_version} → {mod_version})" if mod_version else "update"
                    if mod_version:
                        report.add_updated(mod_name, installed_version, mod_version)
                    self.parent.log(f"  → Will {status}: '{mod_name}'")
                else:
                    self.parent.log(f"  → Will install: '{mod_name}'")
                
                mods_to_download.append(mod)
        
        if pre_skipped > 0:
            if pre_skipped == len(mods_to_install):
                self.parent.log(f"✓ All {pre_skipped} mods are already up-to-date!")
            else:
                self.parent.log(f"○ Skipped {pre_skipped} up-to-date mod(s)")
        
        if not mods_to_download:
            self.parent.install_progress_bar['value'] = 100
            self._finalize_installation_with_report(report, mods_dir, [], total_mods)
            return

        # Parallel downloads
        self.parent.log(f"\nStarting parallel downloads (workers={MAX_DOWNLOAD_WORKERS})...")
        download_results, gdrive_failed = self._download_mods_parallel(
            mods_to_download, 
            skip_gdrive_check=skip_gdrive_check
        )
        
        for mod in gdrive_failed:
            report.add_error(mod.get('name'), "Google Drive HTML response", mod.get('download_url'))
        
        if not self.is_installing:
            self._finalize_installation_cancelled()
            return
        
        # Sequential extraction
        extraction_results = self._extract_downloaded_mods_with_report(download_results, mods_dir, report)
        extracted, skipped, extraction_failures = extraction_results
        
        for mod in extraction_failures:
            if mod not in gdrive_failed:
                report.add_error(mod.get('name'), "Extraction failed", mod.get('download_url'))
        
        if not self.is_installing:
            return
        
        # Finalize
        self._finalize_installation_with_report(
            report, mods_dir, download_results, total_mods,
            gdrive_failed=gdrive_failed, extraction_failures=extraction_failures
        )
    
    def _download_mods_parallel(self, mods_to_download, skip_gdrive_check=False, max_workers=None):
        """Download mods in parallel using ThreadPoolExecutor."""
        download_results = []
        gdrive_failed = []
        self.downloaded_temp_files = []
        
        if max_workers is None:
            max_workers = MAX_DOWNLOAD_WORKERS
        
        self.current_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_to_mod = {
                self.current_executor.submit(self.mod_installer.download_archive, mod, skip_gdrive_check): mod
                for mod in mods_to_download
            }
            completed = 0
            for future in concurrent.futures.as_completed(future_to_mod):
                if not self.is_installing:
                    self.parent.log("Installation canceled by user", error=True)
                    break
                
                while self.is_paused:
                    threading.Event().wait(0.1)
                    
                mod = future_to_mod[future]
                mod_name = mod.get('name', 'Unknown')
                self.current_mod_name.set(f"⬇ Downloading: {mod_name}")
                
                try:
                    temp_path, is_7z = future.result()
                    if temp_path == 'GDRIVE_HTML':
                        gdrive_failed.append(mod)
                        self.parent.log(f"  ⚠️  Google Drive returned HTML (virus scan warning): {mod.get('name')}", error=True)
                    elif temp_path:
                        download_results.append((mod, temp_path, is_7z))
                        self.downloaded_temp_files.append(temp_path)
                        self.parent.log(f"  ✓ Downloaded: {mod.get('name')}")
                    else:
                        self.parent.log(f"  ✗ Failed to download: {mod.get('name')}", error=True)
                except Exception as e:
                    self.parent.log(f"  ✗ Download error for {mod.get('name')}: {e}", error=True)
                    
                completed += 1
                self.parent.install_progress_bar['value'] = (completed / len(mods_to_download)) * 50
                self.parent.root.update_idletasks()
        finally:
            if self.current_executor:
                self.current_executor.shutdown(wait=True)
                self.current_executor = None
        
        return download_results, gdrive_failed
    
    def _extract_downloaded_mods_with_report(self, download_results, mods_dir, report):
        """Extract all downloaded mods sequentially with installation reporting."""
        self.parent.log("Starting sequential extraction...")
        extracted = 0
        skipped = 0
        extraction_failures = []
        
        if not download_results:
            self.parent.log("All mods were skipped (already installed or failed to download)", info=True)
            self.parent.install_progress_bar['value'] = 100
            return (0, 0, [])
        
        for i, (mod, temp_path, is_7z) in enumerate(download_results, 1):
            if not self.is_installing:
                self.parent.log("\nInstallation canceled during extraction", error=True)
                self._cleanup_remaining_downloads(download_results, i-1)
                break
                
            while self.is_paused:
                threading.Event().wait(0.1)
            
            mod_name = mod.get('name', 'Unknown')
            mod_version = self._get_mod_game_version(mod)
            
            self.current_mod_name.set(f"📦 Extracting: {mod_name}")
            
            version_str = f" v{mod_version}" if mod_version else ""
            self.parent.log(f"\n[{i}/{len(download_results)}] Installing {mod_name}{version_str}...")
            
            try:
                metadata = self._auto_detect_game_version(mod, temp_path, is_7z)
                expected_mod_version = mod.get('mod_version')
                success = self.mod_installer.extract_archive(Path(temp_path), mods_dir, is_7z, expected_mod_version)
                
                try:
                    Path(temp_path).unlink()
                except Exception:
                    pass
                
                if success == 'skipped':
                    skipped += 1
                    report.add_skipped(mod_name, "already installed", expected_mod_version)
                elif success:
                    self.parent.log(f"  ✓ {mod['name']} installed successfully", success=True)
                    extracted += 1
                    
                    if metadata:
                        self.mod_installer.update_mod_metadata_in_config(mod_name, metadata, self.parent.config_manager)
                    
                    detected_version = metadata.get('version') if metadata else expected_mod_version
                    report.add_installed(mod_name, detected_version)
                else:
                    self.parent.log(f"  ✗ Failed to install {mod['name']}", error=True)
                    extraction_failures.append(mod)
                    skipped += 1
            except Exception as e:
                self.parent.log(f"  ✗ Unexpected extraction error for {mod.get('name')}: {e}", error=True)
                extraction_failures.append(mod)
                skipped += 1
            
            progress = 50 + ((extracted + skipped) / len(download_results)) * 50
            self.parent.install_progress_bar['value'] = progress
            self.parent.root.update_idletasks()
        
        return (extracted, skipped, extraction_failures)
    
    def _cleanup_remaining_downloads(self, download_results, start_index):
        """Clean up unprocessed downloaded files after cancellation."""
        for _, remaining_temp_path, _ in download_results[start_index:]:
            try:
                Path(remaining_temp_path).unlink()
            except Exception:
                pass
    
    def _auto_detect_game_version(self, mod, temp_path, is_7z):
        """Auto-detect and update game_version and mod_version from mod archive."""
        try:
            metadata = self.mod_installer.extract_mod_metadata(Path(temp_path), is_7z)
            if metadata:
                for m in self.parent.modlist_data.get('mods', []):
                    if m['name'] == mod['name']:
                        if not m.get('game_version') and metadata.get('gameVersion'):
                            m['game_version'] = metadata['gameVersion']
                            self.parent.log(f"  ℹ Auto-detected game version: {metadata['gameVersion']}", info=True)
                        if not m.get('mod_version') and metadata.get('version'):
                            m['mod_version'] = metadata['version']
                            self.parent.log(f"  ℹ Auto-detected mod version: {metadata['version']}", info=True)
                        break
                return metadata
        except Exception as e:
            self.parent.log(f"  ⚠ Could not auto-detect metadata: {e}", debug=True)
        return None
    
    def _update_mod_metadata_from_installed(self, mods_dir):
        """Auto-detect and update mod metadata from installed mods."""
        updated_count = 0
        mods = self.parent.modlist_data.get('mods', [])
        
        for folder, metadata in scan_installed_mods(mods_dir):
            installed_id = metadata.get('id')
            installed_name = metadata.get('name')
            installed_version = metadata.get('version')
            installed_game_version = metadata.get('gameVersion')
            
            if not installed_id:
                continue
            
            for mod in mods:
                config_id = mod.get('mod_id')
                config_name = mod.get('name', '')
                
                is_match = False
                if config_id == installed_id:
                    is_match = True
                elif not config_id and config_name and installed_name:
                    if is_mod_name_match(config_name, folder.name, installed_name):
                        is_match = True
                
                if is_match:
                    changed = False
                    
                    if not mod.get('mod_id'):
                        mod['mod_id'] = installed_id
                        changed = True
                    
                    if not mod.get('name') and installed_name:
                        mod['name'] = installed_name
                        changed = True
                    
                    if installed_version and installed_version != 'unknown':
                        current_mod_version = mod.get('mod_version')
                        if current_mod_version != installed_version:
                            mod['mod_version'] = installed_version
                            changed = True
                    
                    if installed_game_version:
                        current_game_version = mod.get('game_version')
                        if current_game_version != installed_game_version:
                            mod['game_version'] = installed_game_version
                            if 'version' in mod:
                                del mod['version']
                            changed = True
                    
                    if changed:
                        updated_count += 1
                        self.parent.log(f"  ✓ Updated metadata: {mod.get('name')} (ID: {installed_id})", info=True)
                    
                    break
        
        if updated_count > 0:
            self.parent.log(f"✓ Updated metadata for {updated_count} mod(s)")
    
    def _finalize_installation_with_report(self, report, mods_dir, download_results, total_mods,
                                           gdrive_failed=None, extraction_failures=None):
        """Finalize installation with InstallationReport system."""
        gdrive_failed = gdrive_failed or []
        extraction_failures = extraction_failures or []
        
        self.parent.install_progress_bar['value'] = 100
        self.current_mod_name.set("")
        
        self.parent.log("\n" + report.generate_summary())
        
        # Ask user confirmation before updating enabled_mods.json
        all_installed_folders = []
        for folder, metadata in scan_installed_mods(mods_dir):
            all_installed_folders.append(folder.name)
        
        if all_installed_folders:
            result = custom_dialogs.askyesno(
                "Activate Mods",
                f"Do you want to activate all {len(all_installed_folders)} installed mods in Starsector? "
                f"This will update enabled_mods.json to enable all mods. "
                f"You can manage individual mods later via TriOS.",
                parent=self.parent.root
            )
            
            if result:
                self.parent.log("\n" + "─" * 60)
                self.mod_installer.update_enabled_mods(mods_dir, all_installed_folders, merge=False)
                self.parent.log(f"{len(all_installed_folders)} mod(s) activated in enabled_mods.json")
                
                if not report.has_errors():
                    self.parent.log("✓ Ready to play! Launch Starsector or manage mods via TriOS.", success=True)
            else:
                self.parent.log("\n⚠ Mod activation skipped by user. You can manage mods via TriOS.", info=True)
        
        self.parent.save_modlist_config(log_message=False)
        
        self.is_installing = False
        self.parent.install_modlist_btn.config(state=tk.NORMAL, text="Install Modlist")
        self.parent.pause_install_btn.config(state=tk.DISABLED)
        
        self.downloaded_temp_files = []
        
        self.parent.root.after(0, self.parent.display_modlist_info)

        if gdrive_failed:
            self._propose_fix_google_drive_urls(gdrive_failed)
    
    def _finalize_installation_cancelled(self):
        """Cleanup and reset UI after installation cancellation."""
        self.parent.log("Installation aborted")
        self.parent.install_modlist_btn.config(state=tk.NORMAL, text="Install Modlist")
        self.parent.pause_install_btn.config(state=tk.DISABLED)
    
    def _propose_fix_google_drive_urls(self, failed_mods):
        """Propose to fix Google Drive URLs after installation is complete."""
        def on_confirm(mods_to_download):
            for mod, original_mod in zip(mods_to_download, failed_mods):
                if mod['download_url'] != original_mod['download_url']:
                    self.parent.log(f"🔧 Fixed Google Drive URL: {mod.get('name')}", info=True)
            
            self.install_specific_mods(
                [mod['name'] for mod in mods_to_download],
                temp_mods=mods_to_download,
                skip_gdrive_check=True
            )
        
        def on_cancel():
            self._show_installation_complete_message()
        
        def show_dialog():
            try:
                show_google_drive_confirmation_dialog(
                    self.parent.root,
                    failed_mods,
                    on_confirm,
                    on_cancel
                )
            except tk.TclError:
                self._show_installation_complete_message()
        
        self.parent.root.after(0, show_dialog)
    
    def _show_installation_complete_message(self):
        """Display the installation complete banner."""
        self.parent.log("\n✓ Installation workflow complete.", success=True)
    
    def _get_mod_game_version(self, mod):
        """Extract game version from mod dictionary."""
        return mod.get('game_version') or mod.get('version', '')
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during mod installation."""
        import tempfile
        import glob
        
        deleted_count = 0
        
        for temp_file in self.downloaded_temp_files:
            try:
                if os.path.isfile(temp_file):
                    os.unlink(temp_file)
                    deleted_count += 1
            except (OSError, PermissionError):
                pass
        
        self.downloaded_temp_files = []
        
        temp_dir = tempfile.gettempdir()
        pattern = os.path.join(temp_dir, "modlist_*")
        
        for temp_file in glob.glob(pattern):
            try:
                if os.path.isfile(temp_file):
                    os.unlink(temp_file)
                    deleted_count += 1
            except (OSError, PermissionError):
                pass
        
        if deleted_count > 0:
            self.parent.log(f"Cleaned up {deleted_count} temporary file(s)")
    
    def toggle_pause(self):
        """Toggle pause state during installation."""
        if not self.is_installing:
            return
        
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.parent.pause_install_btn.config(text="Resume")
            self.parent.log("Installation paused", info=True)
        else:
            self.parent.pause_install_btn.config(text="Pause")
            self.parent.log("Installation resumed", info=True)
