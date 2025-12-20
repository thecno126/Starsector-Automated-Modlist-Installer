import requests
import zipfile
import tempfile
import os
import json
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Union

try:
    import py7zr
    HAS_7ZIP = True
except ImportError:
    HAS_7ZIP = False

from .constants import REQUEST_TIMEOUT, CHUNK_SIZE, MAX_RETRIES
from .archive_extractor import ArchiveExtractor
from model_types import DownloadResult
from utils.symbols import LogSymbols
from utils.mod_utils import (
    normalize_mod_name,
    extract_all_metadata_from_text,
    compare_versions,
    is_mod_name_match,
    scan_installed_mods,
    is_mod_up_to_date,
    resolve_mod_dependencies,
    extract_major_version,
    read_mod_info_from_archive
)
from utils.error_messages import suggest_fix_for_error, get_user_friendly_error
from utils.network_utils import retry_with_backoff


class ModInstaller:
    
    def __init__(self, log_callback):
        self.log = log_callback
        self.extractor = ArchiveExtractor(log_callback)
    
    def update_mod_metadata_in_config(self, mod_name: str, detected_metadata: Dict[str, Any], config_manager) -> bool:
        if not detected_metadata:
            return False
        
        try:
            config = config_manager.load_modlist_config()
            updated = False
            
            for mod in config.get('mods', []):
                if mod.get('name') == mod_name:
                    for key, config_key in [('version', 'mod_version'), ('id', 'mod_id'), ('gameVersion', 'gameVersion')]:
                        if detected_metadata.get(key):
                            mod[config_key] = detected_metadata[key]
                            updated = True
                    break
            
            if updated:
                config_manager.save_modlist_config(config)
                self.log(f"  ℹ Updated metadata for {mod_name}", debug=True)
            
            return updated
            
        except Exception as e:
            self.log(f"  ⚠ Could not update metadata: {e}", debug=True)
            return False
    
    def install_mod(self, mod: Dict[str, Any], mods_dir: Path) -> bool:
        try:
            mod_version = mod.get('mod_version')
            version_str = f" v{mod_version}" if mod_version else ""
            self.log(f"  Downloading {mod['name']}{version_str}...")
            self.log(f"  From: {mod['download_url']}")
            
            result = self.download_archive(mod)
            if not result.temp_path:
                return False
            
            try:
                self.log(f"  Inspecting archive contents...")
                success = self.extract_archive(result.temp_path, mods_dir, result.is_7z, mod_version)
                if success:
                    self.log(f"  {LogSymbols.SUCCESS} {mod['name']} installed successfully")
                return success
            finally:
                if result.temp_path and Path(result.temp_path).exists():
                    try:
                        Path(result.temp_path).unlink()
                    except (OSError, PermissionError):
                        pass
            
        except requests.exceptions.RequestException as e:
            self.log(f"  {LogSymbols.ERROR} Download error: {e}", error=True)
        except zipfile.BadZipFile:
            self.log(f"  {LogSymbols.ERROR} Corrupted ZIP file", error=True)
        except Exception as e:
            self.log(f"  {LogSymbols.ERROR} Unexpected error: {e}", error=True)
        return False

    def download_archive(self, mod: Dict[str, Any], skip_gdrive_check: bool = False) -> DownloadResult:
        temp_path = None
        
        def attempt_download():
            nonlocal temp_path
            response = requests.get(mod['download_url'], stream=True, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            url_lower = mod['download_url'].lower()
            content_type = response.headers.get('Content-Type', '').lower()
            
            if not skip_gdrive_check and ('drive.google.com' in url_lower or 'drive.usercontent.google.com' in url_lower):
                if 'text/html' in content_type:
                    return DownloadResult('GDRIVE_HTML', False)
            
            is_7z = '.7z' in url_lower or '7z' in content_type
            temp_fd, temp_path = tempfile.mkstemp(suffix='.7z' if is_7z else '.zip', prefix='modlist_')
            
            with os.fdopen(temp_fd, 'wb') as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
            
            if not self._validate_archive_integrity(temp_path, is_7z):
                try:
                    os.unlink(temp_path)
                except (OSError, PermissionError):
                    pass
                raise ValueError("Downloaded file is not a valid archive")
            
            return DownloadResult(temp_path, is_7z)
        
        try:
            return retry_with_backoff(attempt_download, max_retries=MAX_RETRIES, 
                                     exceptions=(requests.exceptions.RequestException, ValueError))
        except requests.exceptions.RequestException as e:
            self.log(f"  {LogSymbols.ERROR} Download failed after {MAX_RETRIES} attempts: {type(e).__name__}", error=True)
            error_type = suggest_fix_for_error(e)
            if error_type:
                self.log(f"\n{get_user_friendly_error(error_type)}", error=True)
        except ValueError as e:
            self.log(f"  {LogSymbols.ERROR} {str(e)}", error=True)
            if 'not a valid archive' in str(e):
                self.log(f"\n{get_user_friendly_error('corrupted_archive')}", error=True)
        except Exception as e:
            self.log(f"  {LogSymbols.ERROR} Unexpected download error: {e}", error=True)
        
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except (OSError, PermissionError):
                pass
        return DownloadResult(None, False)
    
    def _validate_archive_integrity(self, file_path: str, is_7z: bool) -> bool:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return False
        
        file_size = os.path.getsize(file_path)
        
        if is_7z:
            if not HAS_7ZIP:
                return True
            try:
                with py7zr.SevenZipFile(file_path, 'r') as archive:
                    archive.getnames()
                return True
            except Exception:
                return file_size > 0
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                return zf.testzip() is None
        except zipfile.BadZipFile:
            return file_size > 0
        except Exception:
            return False
    
    def extract_archive(self, temp_file: str, mods_dir: Path, is_7z: bool, expected_mod_version: Optional[str] = None):
        return self.extractor.extract_archive(temp_file, mods_dir, is_7z, expected_mod_version)

    def extract_mod_metadata(self, archive_path: Union[str, Path], is_7z: bool = False) -> Optional[Dict[str, Any]]:
        """Extract metadata from mod_info.json in archive without full extraction.
        
        Args:
            archive_path: Path to archive file (str or Path object)
            is_7z: Whether archive is 7z format
            
        Returns:
            Dict with metadata or None if extraction fails
        """
        if isinstance(archive_path, str):
            archive_path = Path(archive_path)
        return read_mod_info_from_archive(archive_path, is_7z)

    def update_enabled_mods(self, mods_dir: Path, installed_mod_names: List[str], merge: bool = True) -> bool:
        try:
            enabled_mods_file = mods_dir / "enabled_mods.json"
            existing_ids = []
            
            if merge and enabled_mods_file.exists():
                try:
                    with open(enabled_mods_file, 'r', encoding='utf-8') as f:
                        existing_ids = json.load(f).get('enabledMods', [])
                        self.log(f"  Found {len(existing_ids)} previously enabled mod(s)", debug=True)
                except (json.JSONDecodeError, IOError) as e:
                    self.log(f"  ⚠ Could not read enabled_mods.json: {e}", info=True)
            
            new_ids = []
            for mod_name in installed_mod_names:
                for folder, metadata in scan_installed_mods(mods_dir, lambda f, c: f.name == mod_name):
                    if mod_id := metadata.get('id'):
                        new_ids.append(mod_id)
                        self.log(f"  ✓ Found mod ID '{mod_id}' for {mod_name}", debug=True)
                        break
            
            enabled_ids = [id for id in existing_ids if id not in new_ids] + new_ids if merge else new_ids
            
            temp_file = enabled_mods_file.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump({"enabledMods": enabled_ids}, f, indent=2)
            temp_file.replace(enabled_mods_file)
            
            return True
                
        except Exception as e:
            self.log(f"  ✗ Error updating enabled_mods.json: {e}", error=True)
            return False
    
    def detect_outdated_mods(self, mods_dir: Path, modlist_mods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        outdated_mods = []
        try:
            modlist_lookup = {mod.get('name'): mod for mod in modlist_mods if mod.get('game_version') or mod.get('version')}
            if not modlist_lookup:
                return []
            
            for folder, metadata in scan_installed_mods(mods_dir):
                installed_version = metadata.get('version')
                content = metadata.get('content')
                
                for modlist_name, modlist_mod in modlist_lookup.items():
                    if modlist_name.lower() in content.lower() or modlist_name.lower() in folder.name.lower():
                        expected_version = modlist_mod.get('version')
                        
                        if installed_version != 'unknown' and expected_version:
                            if compare_versions(installed_version, expected_version) < 0:
                                outdated_mods.append({
                                    'name': modlist_name,
                                    'folder': folder.name,
                                    'installed_version': installed_version,
                                    'expected_version': expected_version,
                                    'mod_id': metadata.get('id') or folder.name
                                })
                                self.log(f"  ⚠ Outdated: {modlist_name} ({installed_version} < {expected_version})", info=True)
                        break
            
            return outdated_mods
        except Exception as e:
            self.log(f"  ✗ Error detecting outdated mods: {e}", error=True)
            return []
    
    def detect_incompatible_game_versions(self, mods_dir: Path, expected_game_version: str) -> List[Dict[str, Any]]:
        if not expected_game_version:
            return []
        
        expected_major = extract_major_version(expected_game_version)
        if not expected_major:
            return []
        
        incompatible_mods = []
        try:
            for folder, metadata in scan_installed_mods(mods_dir):
                if mod_game_version := metadata.get('gameVersion'):
                    mod_major = extract_major_version(mod_game_version)
                    if mod_major and mod_major != expected_major:
                        incompatible_mods.append({
                            'name': metadata.get('name') or folder.name,
                            'folder': folder.name,
                            'mod_game_version': mod_game_version,
                            'expected_game_version': expected_game_version,
                            'mod_id': metadata.get('id') or folder.name
                        })
            return incompatible_mods
        except Exception as e:
            self.log(f"  ✗ Error detecting incompatible game versions: {e}", error=True)
            return []
