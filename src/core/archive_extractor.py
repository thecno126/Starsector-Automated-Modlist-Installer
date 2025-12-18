import zipfile
import shutil
from pathlib import Path

try:
    import py7zr
    HAS_7ZIP = True
except ImportError:
    HAS_7ZIP = False

from utils.mod_utils import (
    extract_mod_id_from_text,
    extract_mod_version_from_text,
    compare_versions
)
from utils.error_messages import suggest_fix_for_error, get_user_friendly_error


class ArchiveExtractor:
    
    def __init__(self, log_callback):
        self.log = log_callback
    
    def extract_archive(self, temp_file, mods_dir, is_7z, expected_mod_version=None):
        try:
            if is_7z:
                return self._extract_7z(temp_file, mods_dir, expected_mod_version)
            else:
                return self._extract_zip(temp_file, mods_dir, expected_mod_version)
        except PermissionError as e:
            self.log(f"  ✗ Permission denied: {e}", error=True)
            friendly_msg = get_user_friendly_error('permission_denied')
            self.log(f"\n{friendly_msg}", error=True)
            return False
        except OSError as e:
            if 'No space left' in str(e) or 'Disk full' in str(e):
                self.log(f"  ✗ Disk space error: {e}", error=True)
                friendly_msg = get_user_friendly_error('disk_space')
                self.log(f"\n{friendly_msg}", error=True)
            else:
                self.log(f"  ✗ Extraction error: {e}", error=True)
            return False
        except Exception as e:
            error_type = suggest_fix_for_error(e)
            if error_type:
                self.log(f"  ✗ Extraction failed: {type(e).__name__}", error=True)
                friendly_msg = get_user_friendly_error(error_type)
                self.log(f"\n{friendly_msg}", error=True)
            else:
                self.log(f"  ✗ Extraction error: {e}", error=True)
            return False
    
    def _extract_7z(self, temp_file, mods_dir, expected_mod_version=None):
        if not HAS_7ZIP:
            self.log("  ✗ Error: py7zr library not installed. Install with: pip install py7zr", error=True)
            return False
        
        try:
            with py7zr.SevenZipFile(temp_file, 'r') as archive:
                all_names = archive.getnames()
                members = [m for m in all_names if m and not m.endswith('/')]
                
                if not members:
                    self.log("  ✗ Error: Archive is empty", error=True)
                    return False

                already_result = self._check_if_installed(None, members, mods_dir, is_7z=True, 
                                                         expected_mod_version=expected_mod_version)
                if already_result:
                    return already_result

                # Zip-slip protection: validate all paths stay within mods_dir
                mods_dir_resolved = mods_dir.resolve()
                for member in all_names:
                    member_path = (mods_dir / member).resolve()
                    try:
                        member_path.relative_to(mods_dir_resolved)
                    except ValueError:
                        self.log(f"  ✗ Security: Attempted path traversal detected in archive (blocked)", error=True)
                        return False

                self.log("  Extracting...")
                archive.extractall(path=mods_dir)
                return True
                
        except py7zr.Bad7zFile:
            self.log(f"  ✗ Error: Corrupted 7z file", error=True)
            return False
    
    def _extract_zip(self, temp_file, mods_dir, expected_mod_version=None):
        with zipfile.ZipFile(temp_file, 'r') as zip_ref:
            members = [m for m in zip_ref.namelist() if m and not m.endswith('/')]
            
            if not members:
                self.log("  ✗ Error: Archive is empty", error=True)
                return False

            already_result = self._check_if_installed(zip_ref, members, mods_dir, 
                                                     expected_mod_version=expected_mod_version)
            
            # Handle update case: delete old version first
            if isinstance(already_result, tuple):
                folder_to_delete, is_update = already_result
                if is_update and folder_to_delete:
                    self.log(f"  🗑 Removing old version: {folder_to_delete.name}", info=True)
                    try:
                        shutil.rmtree(folder_to_delete)
                    except Exception as e:
                        self.log(f"  ✗ Error removing old version: {e}", error=True)
                        return False
            elif already_result:
                return already_result

            # Zip-slip protection: validate all paths
            mods_dir_resolved = mods_dir.resolve()
            for member in zip_ref.namelist():
                member_path = (mods_dir / member).resolve()
                try:
                    member_path.relative_to(mods_dir_resolved)
                except ValueError:
                    self.log(f"  ✗ Security: Attempted path traversal detected in archive (blocked)", error=True)
                    return False

            self.log("  Extracting...")
            zip_ref.extractall(mods_dir)
            return True
    
    def _check_if_installed(self, archive_ref, members, mods_dir, is_7z=False, expected_mod_version=None):
        # For ZIP: compare versions. For 7z: only check existence.
        # Returns: 'skipped' | (folder_path, True) for update | False for not installed
        top_level = set(Path(m).parts[0] for m in members if Path(m).parts)

        if len(top_level) == 1:
            # Archive has a single root folder
            root_dir = next(iter(top_level))
            mod_root = mods_dir / root_dir
            
            if not mod_root.exists():
                return False
            
            # For 7z, only check existence (version comparison too complex)
            if is_7z:
                self.log(f"  ℹ Skipped: Mod '{root_dir}' already installed", info=True)
                return 'skipped'
            
            # For ZIP, check version in mod_info.json
            mod_info_path_in_archive = f"{root_dir}/mod_info.json"
            installed_mod_info = mod_root / "mod_info.json"
            
            if mod_info_path_in_archive not in members or not installed_mod_info.exists():
                # No mod_info.json, just check existence
                self.log(f"  ℹ Skipped: Mod '{root_dir}' already installed", info=True)
                return 'skipped'
            
            try:
                # Read version info
                with open(installed_mod_info, 'r', encoding='utf-8') as f:
                    installed_content = f.read()
                
                with archive_ref.open(mod_info_path_in_archive) as archive_file:
                    new_content = archive_file.read().decode('utf-8')
                
                installed_version = extract_mod_version_from_text(installed_content)
                new_version = extract_mod_version_from_text(new_content)
                mod_id = extract_mod_id_from_text(new_content) or root_dir
                
                # Use expected_mod_version from modlist config if provided, otherwise use archive version
                version_to_install = expected_mod_version if expected_mod_version else new_version
                
                # Compare versions using centralized function
                version_comparison = compare_versions(version_to_install, installed_version)
                
                if version_comparison > 0:
                    # Newer version available
                    self.log(f"  ⬆ Update available: '{mod_id}' {installed_version} → {version_to_install}", info=True)
                    self.log(f"  Installing newer version...", info=True)
                    return (mod_root, True)
                
                # Same or older version
                status = "newer" if version_comparison < 0 else "already"
                self.log(f"  ℹ Skipped: '{mod_id}' v{installed_version} {status} installed", info=True)
                return 'skipped'
                
            except (IOError, UnicodeDecodeError) as e:
                self.log(f"  ⚠ Warning: Error reading mod metadata - {type(e).__name__}", info=True)
                self.log(f"  ℹ Skipped: Mod '{root_dir}' already installed (version comparison unavailable)", info=True)
                return 'skipped'
        else:
            # Archive has multiple files at root level
            for member in members:
                if (mods_dir / Path(member)).exists():
                    self.log("  ℹ Skipped: Installation would overlap existing files", info=True)
                    return 'skipped'
        
        return False
