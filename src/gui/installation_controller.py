"""Installation workflow: download, extraction, finalization."""

import threading
import concurrent.futures
from pathlib import Path
from core import InstallationReport, MAX_DOWNLOAD_WORKERS
from utils.mod_utils import is_mod_up_to_date, resolve_mod_dependencies
from utils.mod_utils import scan_installed_mods, is_mod_name_match
from utils.backup_manager import BackupManager
from utils.symbols import LogSymbols, UISymbols


class InstallationController:
    def __init__(self, main_window):
        self.window = main_window
        self.mod_installer = main_window.mod_installer
    
    def _set_progress(self, value):
        """Thread-safe progress bar update."""
        self.window.install_progress_bar['value'] = value
        self.window.root.update_idletasks()
        
    def download_mods_parallel(self, mods_to_download, skip_gdrive_check=False, max_workers=None):
        download_results = []
        gdrive_failed = []
        
        self.window.downloaded_temp_files = []
        
        if max_workers is None:
            max_workers = MAX_DOWNLOAD_WORKERS
        
        self.window.current_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_to_mod = {
                self.window.current_executor.submit(self.mod_installer.download_archive, mod, skip_gdrive_check): mod
                for mod in mods_to_download
            }
            completed = 0
            for future in concurrent.futures.as_completed(future_to_mod):
                if not self.window.is_installing:
                    self.window.log("Installation canceled by user", error=True)
                    break
                
                while self.window.is_paused:
                    threading.Event().wait(0.1)
                    
                mod = future_to_mod[future]
                mod_name = mod.get('name', 'Unknown')
                self.window.root.after(0, lambda n=mod_name: self.window.current_mod_name.set(f"{UISymbols.DOWNLOADING} Downloading: {n}"))
                
                try:
                    result = future.result()
                    if result.temp_path == 'GDRIVE_HTML':
                        gdrive_failed.append(mod)
                        self.window.log(f"  {LogSymbols.WARNING}  Google Drive returned HTML (virus scan warning): {mod.get('name')}", error=True)
                    elif result.temp_path:
                        download_results.append((mod, result.temp_path, result.is_7z))
                        self.window.downloaded_temp_files.append(result.temp_path)
                        self.window.log(f"  {LogSymbols.SUCCESS} Downloaded: {mod.get('name')}")
                    else:
                        self.window.log(f"  {LogSymbols.ERROR} Failed to download: {mod.get('name')}", error=True)
                except Exception as e:
                    self.window.log(f"  {LogSymbols.ERROR} Download error for {mod.get('name')}: {e}", error=True)
                    
                completed += 1
                progress_value = (completed / len(mods_to_download)) * 50
                self.window.root.after(0, lambda v=progress_value: self._set_progress(v))
        finally:
            if self.window.current_executor:
                self.window.current_executor.shutdown(wait=True)
                self.window.current_executor = None
        
        return download_results, gdrive_failed

    def install_mods_internal(self, mods_to_install, skip_gdrive_check=False):
        report = InstallationReport()
        
        mods_dir = Path(self.window.starsector_path.get()) / "mods"
        total_mods = len(mods_to_install)

        self.window.log(f"\nStarting installation of {total_mods} mod{'s' if total_mods > 1 else ''}...")
        self.window.log(LogSymbols.SEPARATOR * 60)
        
        self.window.log("Creating backup of enabled_mods.json...")
        try:
            if self.window.backup_manager:
                result = self.window.backup_manager.create_backup(backup_mods=False)
                if result.success:
                    self.window.log(f"{LogSymbols.SUCCESS} Backup created: {result.path.name}")
                else:
                    self.window.log(f"{LogSymbols.WARNING} Backup failed: {result.error}", warning=True)
            else:
                self.window.log(f"{LogSymbols.WARNING} Backup manager not initialized", warning=True)
        except Exception as e:
            self.window.log(f"{LogSymbols.WARNING} Could not create backup: {e}", warning=True)

        # Update metadata from installed mods for accurate version checking
        self.window.log("Scanning installed mods for metadata...")
        self.update_mod_metadata_from_installed(mods_dir)
        
        installed_mods_dict = {}
        for folder, metadata in scan_installed_mods(mods_dir):
            mod_id = metadata.get('id')
            if mod_id:
                installed_mods_dict[mod_id] = metadata

        self.window.log("Resolving mod dependencies...")
        mods_to_install = resolve_mod_dependencies(mods_to_install, installed_mods_dict)
        self.window.log(f"  {LogSymbols.SUCCESS} Dependencies resolved, installation order optimized")

        # Filter: check which mods are already up-to-date
        mods_to_download = []
        pre_skipped = 0
        
        for mod in mods_to_install:
            mod_name = mod.get('name', 'Unknown')
            mod_version = mod.get('mod_version')
            
            check = is_mod_up_to_date(mod_name, mod_version, mods_dir)
            
            if check.is_current:
                version_str = f" (v{check.installed_version})" if check.installed_version else ""
                report.add_skipped(mod_name, "already up-to-date", check.installed_version)
                pre_skipped += 1
            else:
                if check.installed_version is not None:
                    status = f"update ({check.installed_version} {LogSymbols.ARROW_RIGHT} {mod_version})" if mod_version else "update"
                    if mod_version:
                        report.add_updated(mod_name, check.installed_version, mod_version)
                    self.window.log(f"  {LogSymbols.ARROW_RIGHT} Will {status}: '{mod_name}'")
                else:
                    self.window.log(f"  {LogSymbols.ARROW_RIGHT} Will install: '{mod_name}'")
                
                mods_to_download.append(mod)
        
        if pre_skipped > 0:
            if pre_skipped == len(mods_to_install):
                self.window.log(f"{LogSymbols.SUCCESS} All {pre_skipped} mods are already up-to-date!")
            else:
                self.window.log(f"{LogSymbols.NOT_INSTALLED} Skipped {pre_skipped} up-to-date mod(s)")
        
        if not mods_to_download:
            self.window.install_progress_bar['value'] = 100
            self.finalize_installation_with_report(report, mods_dir, [], total_mods)
            return

        self.window.log(f"\nStarting parallel downloads (workers={MAX_DOWNLOAD_WORKERS})...")
        download_results, gdrive_failed = self.download_mods_parallel(
            mods_to_download, 
            skip_gdrive_check=skip_gdrive_check
        )
        
        for mod in gdrive_failed:
            report.add_error(mod.get('name'), "Google Drive HTML response", mod.get('download_url'))
        
        if not self.window.is_installing:
            self.finalize_installation_cancelled()
            return
        
        extraction_results = self.extract_downloaded_mods_with_report(download_results, mods_dir, report)
        extracted, skipped, extraction_failures = extraction_results
        
        for mod in extraction_failures:
            if mod not in gdrive_failed:
                report.add_error(mod.get('name'), "Extraction failed", mod.get('download_url'))
        
        if not self.window.is_installing:
            return
        
        self.finalize_installation_with_report(
            report, mods_dir, download_results, total_mods,
            gdrive_failed=gdrive_failed, extraction_failures=extraction_failures
        )
    
    def finalize_installation_cancelled(self):
        self.window.log("Installation aborted")
        self.window.install_modlist_btn.config(state='normal', text="Install Modlist")
        self.window.pause_install_btn.config(state='disabled')
    
    def extract_downloaded_mods_with_report(self, download_results, mods_dir, report):
        # Returns: (extracted_count, skipped_count, extraction_failures_list)
        self.window.log("Starting sequential extraction...")
        extracted = 0
        skipped = 0
        extraction_failures = []
        
        if not download_results:
            self.window.log("All mods were skipped (already installed or failed to download)", info=True)
            self.window.root.after(0, lambda: self._set_progress(100))
            return (0, 0, [])
        
        for i, (mod, temp_path, is_7z) in enumerate(download_results, 1):
            if not self.window.is_installing:
                self.window.log("\nInstallation canceled during extraction", error=True)
                self.cleanup_remaining_downloads(download_results, i-1)
                break
                
            while self.window.is_paused:
                threading.Event().wait(0.1)
            
            mod_name = mod.get('name', 'Unknown')
            mod_version = self.window._get_mod_game_version(mod)
            
            self.window.root.after(0, lambda n=mod_name: self.window.current_mod_name.set(f"📦 Extracting: {n}"))
            
            version_str = f" v{mod_version}" if mod_version else ""
            self.window.log(f"\n[{i}/{len(download_results)}] Installing {mod_name}{version_str}...")
            
            try:
                metadata = self.auto_detect_game_version(mod, temp_path, is_7z)
                
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
                    self.window.log(f"  {LogSymbols.SUCCESS} {mod['name']} installed successfully", success=True)
                    extracted += 1
                    
                    if metadata:
                        self.mod_installer.update_mod_metadata_in_config(mod_name, metadata, self.window.config_manager)
                    
                    detected_version = metadata.get('version') if metadata else expected_mod_version
                    report.add_installed(mod_name, detected_version)
                else:
                    self.window.log(f"  {LogSymbols.ERROR} Failed to install {mod['name']}", error=True)
                    extraction_failures.append(mod)
                    skipped += 1
            except Exception as e:
                self.window.log(f"  {LogSymbols.ERROR} Unexpected extraction error for {mod.get('name')}: {e}", error=True)
                extraction_failures.append(mod)
                skipped += 1
            
            progress = 50 + ((extracted + skipped) / len(download_results)) * 50
            self.window.root.after(0, lambda v=progress: self._set_progress(v))
        
        return (extracted, skipped, extraction_failures)
    
    def cleanup_remaining_downloads(self, download_results, start_index):
        for _, remaining_temp_path, _ in download_results[start_index:]:
            try:
                Path(remaining_temp_path).unlink()
            except Exception:
                pass
    
    def auto_detect_game_version(self, mod, temp_path, is_7z):
        try:
            metadata = self.mod_installer.extract_mod_metadata(Path(temp_path), is_7z)
            if metadata:
                for m in self.window.modlist_data.get('mods', []):
                    if m['name'] == mod['name']:
                        if not m.get('game_version') and metadata.get('gameVersion'):
                            m['game_version'] = metadata['gameVersion']
                            self.window.log(f"  ℹ Auto-detected game version: {metadata['gameVersion']}", info=True)
                        if not m.get('mod_version') and metadata.get('version'):
                            m['mod_version'] = metadata['version']
                            self.window.log(f"  ℹ Auto-detected mod version: {metadata['version']}", info=True)
                        break
                return metadata
        except Exception as e:
            self.window.log(f"  ⚠ Could not auto-detect metadata: {e}", debug=True)
        return None
    
    def update_mod_metadata_from_installed(self, mods_dir):
        # Scan installed mods and update config with accurate metadata (mod_id, versions)
        updated_count = 0
        
        mods = self.window.modlist_data.get('mods', [])
        
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
                        self.window.log(f"  {LogSymbols.SUCCESS} Updated metadata: {mod.get('name')} (ID: {installed_id})", info=True)
                    
                    break
        
        if updated_count > 0:
            self.window.log(f"{LogSymbols.SUCCESS} Updated metadata for {updated_count} mod(s)")
    
    def finalize_installation_with_report(self, report, mods_dir, download_results, total_mods,
                                           gdrive_failed=None, extraction_failures=None):
        from . import dialogs as custom_dialogs
        
        gdrive_failed = gdrive_failed or []
        extraction_failures = extraction_failures or []
        
        self.window.install_progress_bar['value'] = 100
        self.window.current_mod_name.set("")
        
        self.window.log("\n" + report.generate_summary())
        
        # Note: Mod activation is now manual via "Enable All Mods" button
        # No longer prompting user during installation
        
        if not report.has_errors():
            self.window.log(f"{LogSymbols.SUCCESS} Installation Complete! Use 'Enable All Mods' button to activate them.", success=True)
        
        # Save modlist to persist any auto-detected game_version values from extraction
        self.window.save_modlist_config(log_message=False)
        
        self.window.is_installing = False
        self.window.install_modlist_btn.config(state='normal', text="Install Modlist")
        self.window.pause_install_btn.config(state='disabled')
        
        # Clear temp files tracker (all should be deleted by now)
        self.window.downloaded_temp_files = []
        
        # Refresh the UI to show updated game versions (after all installation is complete)
        self.window.root.after(0, self.window.display_modlist_info)

        # Show manual download instructions for Google Drive mods if any
        if gdrive_failed:
            self.window._propose_fix_google_drive_urls(gdrive_failed)
