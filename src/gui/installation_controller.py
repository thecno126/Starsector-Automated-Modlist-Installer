"""
Installation controller for managing mod download and extraction workflow.
Extracted from main_window.py to reduce complexity.
"""

import threading
import concurrent.futures
from pathlib import Path
from core import InstallationReport, MAX_DOWNLOAD_WORKERS
from core.installer import is_mod_up_to_date, resolve_mod_dependencies
from utils.mod_utils import scan_installed_mods, is_mod_name_match
from utils.backup_manager import BackupManager


class InstallationController:
    """Handles the complex installation workflow: download, extraction, and finalization."""
    
    def __init__(self, main_window):
        """Initialize with reference to main window for UI updates.
        
        Args:
            main_window: ModlistInstaller instance for accessing UI elements and logging
        """
        self.window = main_window
        self.mod_installer = main_window.mod_installer
        
    def download_mods_parallel(self, mods_to_download, skip_gdrive_check=False, max_workers=None):
        """Download mods in parallel using ThreadPoolExecutor.
        
        Args:
            mods_to_download: List of mod dictionaries to download
            skip_gdrive_check: If True, skip Google Drive HTML detection
            max_workers: Number of parallel download workers (default: MAX_DOWNLOAD_WORKERS)
            
        Returns:
            tuple: (download_results, gdrive_failed)
                download_results: List of (mod, temp_path, is_7z) tuples for successful downloads
                gdrive_failed: List of mods that failed due to Google Drive HTML
        """
        download_results = []
        gdrive_failed = []
        
        # Reset temp files tracker
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
                # Check if installation was canceled
                if not self.window.is_installing:
                    self.window.log("Installation canceled by user", error=True)
                    break
                
                while self.window.is_paused:
                    threading.Event().wait(0.1)
                    
                mod = future_to_mod[future]
                mod_name = mod.get('name', 'Unknown')
                self.window.current_mod_name.set(f"⬇ Downloading: {mod_name}")
                
                try:
                    temp_path, is_7z = future.result()
                    if temp_path == 'GDRIVE_HTML':
                        gdrive_failed.append(mod)
                        self.window.log(f"  ⚠️  Google Drive returned HTML (virus scan warning): {mod.get('name')}", error=True)
                    elif temp_path:
                        download_results.append((mod, temp_path, is_7z))
                        self.window.downloaded_temp_files.append(temp_path)  # Track for cleanup
                        self.window.log(f"  ✓ Downloaded: {mod.get('name')}")
                    else:
                        self.window.log(f"  ✗ Failed to download: {mod.get('name')}", error=True)
                except Exception as e:
                    self.window.log(f"  ✗ Download error for {mod.get('name')}: {e}", error=True)
                    
                completed += 1
                self.window.install_progress_bar['value'] = (completed / len(mods_to_download)) * 50
                self.window.root.update_idletasks()
        finally:
            if self.window.current_executor:
                self.window.current_executor.shutdown(wait=True)
                self.window.current_executor = None
        
        return download_results, gdrive_failed

    def install_mods_internal(self, mods_to_install, skip_gdrive_check=False):
        """Internal method to install a list of mods.
        
        Args:
            mods_to_install: List of mod dictionaries to install
            skip_gdrive_check: If True, skip Google Drive verification (already confirmed by user)
        """
        # Initialize installation report
        report = InstallationReport()
        
        mods_dir = Path(self.window.starsector_path.get()) / "mods"
        total_mods = len(mods_to_install)

        self.window.log(f"\nStarting installation of {total_mods} mod{'s' if total_mods > 1 else ''}...")
        self.window.log("─" * 60)
        
        # Create automatic backup before installation
        self.window.log("Creating backup of enabled_mods.json...")
        try:
            backup_manager = BackupManager(self.window.starsector_path.get())
            backup_path, success, error = backup_manager.create_backup(backup_mods=False)
            if success:
                self.window.log(f"✓ Backup created: {backup_path.name}")
                # Cleanup old backups (keep last 5)
                deleted = backup_manager.cleanup_old_backups(keep_count=5)
                if deleted > 0:
                    self.window.log(f"  Cleaned up {deleted} old backup(s)", debug=True)
            else:
                self.window.log(f"⚠ Backup failed: {error}", warning=True)
        except Exception as e:
            self.window.log(f"⚠ Could not create backup: {e}", warning=True)

        # Update metadata from installed mods BEFORE filtering
        # This ensures we have accurate mod_version for comparison
        self.window.log("Scanning installed mods for metadata...")
        self.update_mod_metadata_from_installed(mods_dir)
        
        # Scan currently installed mods for dependency resolution and version checking
        installed_mods_dict = {}
        for folder, metadata in scan_installed_mods(mods_dir):
            mod_id = metadata.get('id')
            if mod_id:
                installed_mods_dict[mod_id] = metadata

        # Resolve dependencies - reorder mods so dependencies are installed first
        self.window.log("Resolving mod dependencies...")
        mods_to_install = resolve_mod_dependencies(mods_to_install, installed_mods_dict)
        self.window.log(f"  ✓ Dependencies resolved, installation order optimized")

        # Pre-filter: Check which mods are already installed with correct version
        mods_to_download = []
        pre_skipped = 0
        
        for mod in mods_to_install:
            mod_name = mod.get('name', 'Unknown')
            mod_version = mod.get('mod_version')
            
            # Use new is_mod_up_to_date function which checks both installation and version
            is_up_to_date, installed_version = is_mod_up_to_date(mod_name, mod_version, mods_dir)
            
            if is_up_to_date:
                # Mod is installed and up-to-date
                version_str = f" (v{installed_version})" if installed_version else ""
                report.add_skipped(mod_name, "already up-to-date", installed_version)
                pre_skipped += 1
            else:
                # Mod needs to be downloaded (either not installed or outdated)
                if installed_version is not None:
                    # It's an update
                    status = f"update ({installed_version} → {mod_version})" if mod_version else "update"
                    if mod_version:
                        report.add_updated(mod_name, installed_version, mod_version)
                    self.window.log(f"  → Will {status}: '{mod_name}'")
                else:
                    # It's a new installation
                    self.window.log(f"  → Will install: '{mod_name}'")
                
                mods_to_download.append(mod)
        
        if pre_skipped > 0:
            if pre_skipped == len(mods_to_install):
                self.window.log(f"✓ All {pre_skipped} mods are already up-to-date!")
            else:
                self.window.log(f"○ Skipped {pre_skipped} up-to-date mod(s)")
        
        if not mods_to_download:
            self.window.install_progress_bar['value'] = 100
            self.finalize_installation_with_report(report, mods_dir, [], total_mods)
            return

        # Step 1: parallel downloads
        self.window.log(f"\nStarting parallel downloads (workers={MAX_DOWNLOAD_WORKERS})...")
        download_results, gdrive_failed = self.download_mods_parallel(
            mods_to_download, 
            skip_gdrive_check=skip_gdrive_check
        )
        
        # Track download errors in report
        for mod in gdrive_failed:
            report.add_error(mod.get('name'), "Google Drive HTML response", mod.get('download_url'))
        
        # Check if installation was canceled during downloads
        if not self.window.is_installing:
            self.finalize_installation_cancelled()
            return
        
        # Step 2: sequential extraction
        extraction_results = self.extract_downloaded_mods_with_report(download_results, mods_dir, report)
        extracted, skipped, extraction_failures = extraction_results
        
        # Track extraction failures in report
        for mod in extraction_failures:
            if mod not in gdrive_failed:  # Don't double-count Google Drive failures
                report.add_error(mod.get('name'), "Extraction failed", mod.get('download_url'))
        
        # Check if installation was canceled during extraction
        if not self.window.is_installing:
            return
        
        # Step 3: Update statistics and finalize with report
        self.finalize_installation_with_report(
            report, mods_dir, download_results, total_mods,
            gdrive_failed=gdrive_failed, extraction_failures=extraction_failures
        )
    
    def finalize_installation_cancelled(self):
        """Cleanup and reset UI after installation cancellation."""
        self.window.log("Installation aborted")
        self.window.install_modlist_btn.config(state='normal', text="Install Modlist")
        self.window.pause_install_btn.config(state='disabled')
    
    def extract_downloaded_mods_with_report(self, download_results, mods_dir, report):
        """Extract all downloaded mods sequentially with installation reporting.
        
        Args:
            download_results: List of (mod, temp_path, is_7z) tuples
            mods_dir: Path to Starsector mods directory
            report: InstallationReport instance for tracking
            
        Returns:
            tuple: (extracted_count, skipped_count, extraction_failures_list)
        """
        self.window.log("Starting sequential extraction...")
        extracted = 0
        skipped = 0
        extraction_failures = []
        
        if not download_results:
            self.window.log("All mods were skipped (already installed or failed to download)", info=True)
            self.window.install_progress_bar['value'] = 100
            return (0, 0, [])
        
        for i, (mod, temp_path, is_7z) in enumerate(download_results, 1):
            # Check cancellation
            if not self.window.is_installing:
                self.window.log("\nInstallation canceled during extraction", error=True)
                self.cleanup_remaining_downloads(download_results, i-1)
                break
                
            while self.window.is_paused:
                threading.Event().wait(0.1)
            
            mod_name = mod.get('name', 'Unknown')
            mod_version = self.window._get_mod_game_version(mod)
            
            # Update progress indicator
            self.window.current_mod_name.set(f"📦 Extracting: {mod_name}")
            
            version_str = f" v{mod_version}" if mod_version else ""
            self.window.log(f"\n[{i}/{len(download_results)}] Installing {mod_name}{version_str}...")
            
            try:
                # Auto-detect game_version BEFORE extraction
                metadata = self.auto_detect_game_version(mod, temp_path, is_7z)
                
                # Pass mod_version to enable version comparison during extraction
                expected_mod_version = mod.get('mod_version')
                success = self.mod_installer.extract_archive(Path(temp_path), mods_dir, is_7z, expected_mod_version)
                
                # Clean up temp file
                try:
                    Path(temp_path).unlink()
                except Exception:
                    pass
                
                if success == 'skipped':
                    skipped += 1
                    report.add_skipped(mod_name, "already installed", expected_mod_version)
                elif success:
                    self.window.log(f"  ✓ {mod['name']} installed successfully", success=True)
                    extracted += 1
                    
                    # Update metadata in config with detected info
                    if metadata:
                        self.mod_installer.update_mod_metadata_in_config(mod_name, metadata, self.window.config_manager)
                    
                    # Track in report
                    detected_version = metadata.get('version') if metadata else expected_mod_version
                    report.add_installed(mod_name, detected_version)
                else:
                    self.window.log(f"  ✗ Failed to install {mod['name']}", error=True)
                    extraction_failures.append(mod)
                    skipped += 1
            except Exception as e:
                self.window.log(f"  ✗ Unexpected extraction error for {mod.get('name')}: {e}", error=True)
                extraction_failures.append(mod)
                skipped += 1
            
            # Update progress bar
            progress = 50 + ((extracted + skipped) / len(download_results)) * 50
            self.window.install_progress_bar['value'] = progress
            self.window.root.update_idletasks()
        
        return (extracted, skipped, extraction_failures)
    
    def cleanup_remaining_downloads(self, download_results, start_index):
        """Clean up unprocessed downloaded files after cancellation.
        
        Args:
            download_results: List of (mod, temp_path, is_7z) tuples
            start_index: Index from which to start cleanup
        """
        for _, remaining_temp_path, _ in download_results[start_index:]:
            try:
                Path(remaining_temp_path).unlink()
            except Exception:
                pass
    
    def auto_detect_game_version(self, mod, temp_path, is_7z):
        """Auto-detect and update game_version and mod_version from mod archive.
        
        Args:
            mod: Mod dictionary
            temp_path: Path to downloaded archive
            is_7z: Whether archive is 7z format
            
        Returns:
            dict: Detected metadata or None
        """
        try:
            metadata = self.mod_installer.extract_mod_metadata(Path(temp_path), is_7z)
            if metadata:
                # Update in modlist_data
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
        """Auto-detect and update mod metadata (mod_id, name, versions) from installed mods.
        
        Scans all installed mods and updates the modlist config with accurate metadata.
        Uses mod_id as primary key for matching.
        
        Args:
            mods_dir: Path to Starsector mods directory
        """
        updated_count = 0
        
        # Get all mods from config
        mods = self.window.modlist_data.get('mods', [])
        
        # Scan all installed mod folders using centralized scanner
        for folder, metadata in scan_installed_mods(mods_dir):
            installed_id = metadata.get('id')
            installed_name = metadata.get('name')
            installed_version = metadata.get('version')
            installed_game_version = metadata.get('gameVersion')
            
            if not installed_id:
                continue
            
            # Find matching mod in config by mod_id or name
            for mod in mods:
                config_id = mod.get('mod_id')
                config_name = mod.get('name', '')
                
                # Match by mod_id (primary) or name normalization (fallback)
                is_match = False
                if config_id == installed_id:
                    is_match = True
                elif not config_id and config_name and installed_name:
                    # Fallback: use centralized matching function
                    if is_mod_name_match(config_name, folder.name, installed_name):
                        is_match = True
                
                if is_match:
                    # Update mod metadata
                    changed = False
                    
                    # Always update mod_id if missing
                    if not mod.get('mod_id'):
                        mod['mod_id'] = installed_id
                        changed = True
                    
                    # Update name ONLY if missing (never overwrite existing custom names)
                    if not mod.get('name') and installed_name:
                        mod['name'] = installed_name
                        changed = True
                    
                    # Update versions only if different
                    if installed_version and installed_version != 'unknown':
                        current_mod_version = mod.get('mod_version')
                        if current_mod_version != installed_version:
                            mod['mod_version'] = installed_version
                            changed = True
                    
                    if installed_game_version:
                        current_game_version = mod.get('game_version')
                        if current_game_version != installed_game_version:
                            mod['game_version'] = installed_game_version
                            # Remove legacy 'version' field
                            if 'version' in mod:
                                del mod['version']
                            changed = True
                    
                    if changed:
                        updated_count += 1
                        self.window.log(f"  ✓ Updated metadata: {mod.get('name')} (ID: {installed_id})", info=True)
                    
                    break
        
        if updated_count > 0:
            self.window.log(f"✓ Updated metadata for {updated_count} mod(s)")
    
    def finalize_installation_with_report(self, report, mods_dir, download_results, total_mods,
                                           gdrive_failed=None, extraction_failures=None):
        """Finalize installation with InstallationReport system.
        
        Args:
            report: InstallationReport instance with tracked stats
            mods_dir: Path to Starsector mods directory
            download_results: List of successfully downloaded mods
            total_mods: Total number of mods attempted
            gdrive_failed: Optional list of Google Drive failures (legacy)
            extraction_failures: Optional list of extraction failures (legacy)
        """
        from . import custom_dialogs
        
        gdrive_failed = gdrive_failed or []
        extraction_failures = extraction_failures or []
        
        # Final statistics
        self.window.install_progress_bar['value'] = 100
        self.window.current_mod_name.set("")  # Clear progress indicator
        
        # Display formatted report
        self.window.log("\n" + report.generate_summary())
        
        # Ask user confirmation before updating enabled_mods.json
        all_installed_folders = []
        for folder, metadata in scan_installed_mods(mods_dir):
            all_installed_folders.append(folder.name)
        
        if all_installed_folders:
            # Ask for confirmation
            result = custom_dialogs.askyesno(
                "Activate Mods",
                f"Do you want to activate all {len(all_installed_folders)} installed mods in Starsector? "
                f"This will update enabled_mods.json to enable all mods. "
                f"You can manage individual mods later via TriOS.",
                parent=self.window.root
            )
            
            if result:
                self.window.log("\n" + "─" * 60)
                
                # Use merge=False to replace the list entirely with all installed mods
                self.mod_installer.update_enabled_mods(mods_dir, all_installed_folders, merge=False)
                self.window.log(f"{len(all_installed_folders)} mod(s) activated in enabled_mods.json")
                
                # Show final completion message if no errors
                if not report.has_errors():
                    self.window.log("✓ Ready to play! Launch Starsector or manage mods via TriOS.", success=True)
            else:
                self.window.log("\n⚠ Mod activation skipped by user. You can manage mods via TriOS.", info=True)
        
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
