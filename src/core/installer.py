"""
Mod installation logic for the Modlist Installer.
Handles downloading and extracting mod archives.
"""

import requests
import zipfile
import tempfile
import os
import re
import shutil
from pathlib import Path

try:
    import py7zr
    HAS_7ZIP = True
except ImportError:
    HAS_7ZIP = False

from .constants import REQUEST_TIMEOUT, CHUNK_SIZE


def validate_mod_urls(mods, progress_callback=None):
    """
    Validate all mod URLs before installation using parallel requests.
    
    Args:
        mods: List of mod dictionaries with 'download_url' and 'name'
        progress_callback: Optional callback function(current, total, mod_name)
        
    Returns:
        dict: {
            'github': [mod, ...],  # GitHub URLs
            'google_drive': [mod, ...],  # Google Drive URLs
            'other': {'domain': [mod, ...], ...},  # Other domains
            'failed': [{'mod': mod, 'status': code, 'error': str}, ...]  # Inaccessible URLs
        }
    """
    import concurrent.futures
    from urllib.parse import urlparse
    
    results = {
        'github': [],
        'google_drive': [],
        'other': {},
        'failed': []
    }
    
    def check_url(mod, index):
        """Check a single URL. Returns (index, category, mod, domain, status, error)."""
        if progress_callback:
            progress_callback(index + 1, len(mods), mod.get('name', 'Unknown'))
        
        url = mod.get('download_url', '')
        if not url:
            return (index, 'failed', mod, None, 0, 'No download URL')
        
        # Parse domain
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
        except:
            domain = 'unknown'
        
        # Categorize by domain
        is_github = 'github.com' in domain
        is_gdrive = 'drive.google.com' in domain or 'drive.usercontent.google.com' in domain
        
        try:
            # Try HEAD request first (fast), fallback to GET if blocked
            try:
                response = requests.head(url, timeout=3, allow_redirects=True)
                # Some servers block HEAD requests with 403, try GET if that happens
                if response.status_code == 403:
                    raise requests.exceptions.RequestException("HEAD blocked, trying GET")
            except (requests.exceptions.RequestException, requests.exceptions.Timeout):
                # Fallback to GET request with minimal data (first byte only)
                response = requests.get(url, timeout=3, allow_redirects=True, 
                                       headers={'Range': 'bytes=0-0'}, stream=True)
                response.close()  # Close immediately, we just need the status
            
            if response.status_code >= 200 and response.status_code < 300:
                if is_github:
                    return (index, 'github', mod, domain, response.status_code, None)
                elif is_gdrive:
                    return (index, 'google_drive', mod, domain, response.status_code, None)
                else:
                    return (index, 'other', mod, domain, response.status_code, None)
            else:
                return (index, 'failed', mod, domain, response.status_code, f'HTTP {response.status_code}')
        except requests.exceptions.Timeout:
            return (index, 'failed', mod, domain, 0, 'Timeout (3s)')
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if len(error_msg) > 50:
                error_msg = error_msg[:47] + '...'
            return (index, 'failed', mod, domain, 0, error_msg)
    
    # Run checks in parallel (max 5 simultaneous requests)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(check_url, mod, i) for i, mod in enumerate(mods)]
        
        for future in concurrent.futures.as_completed(futures):
            index, category, mod, domain, status, error = future.result()
            
            if category == 'github':
                results['github'].append(mod)
            elif category == 'google_drive':
                results['google_drive'].append(mod)
            elif category == 'other':
                if domain not in results['other']:
                    results['other'][domain] = []
                results['other'][domain].append(mod)
            elif category == 'failed':
                results['failed'].append({
                    'mod': mod,
                    'status': status,
                    'error': error
                })
    
    # Retry failed mods once (timeout/connection errors only, not 404s)
    if results['failed']:
        retry_candidates = []
        permanent_failures = []
        
        for fail in results['failed']:
            # Retry if timeout or connection error (status 0), skip if HTTP error (404, 403, etc.)
            if fail['status'] == 0:
                retry_candidates.append(fail)
            else:
                permanent_failures.append(fail)
        
        if retry_candidates:
            if progress_callback:
                progress_callback(len(mods), len(mods), f"Retrying {len(retry_candidates)} failed...")
            
            # Retry with same logic
            results['failed'] = permanent_failures  # Keep only permanent failures
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                retry_futures = [executor.submit(check_url, fail['mod'], i) 
                                for i, fail in enumerate(retry_candidates)]
                
                for future in concurrent.futures.as_completed(retry_futures):
                    index, category, mod, domain, status, error = future.result()
                    
                    if category == 'github':
                        results['github'].append(mod)
                    elif category == 'google_drive':
                        results['google_drive'].append(mod)
                    elif category == 'other':
                        if domain not in results['other']:
                            results['other'][domain] = []
                        results['other'][domain].append(mod)
                    elif category == 'failed':
                        results['failed'].append({
                            'mod': mod,
                            'status': status,
                            'error': error
                        })
    
    return results


def _compare_versions(version1, version2):
    """
    Compare two version strings.
    
    Args:
        version1: First version string (e.g., "1.2.3" or "2.0a")
        version2: Second version string
        
    Returns:
        int: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
    """
    if version1 == version2:
        return 0
    
    # Extract numeric parts and compare
    def parse_version(v):
        # Remove common prefixes and extract numbers
        v = str(v).lower().replace('v', '').replace('version', '').strip()
        # Split by dots, hyphens, or letters
        parts = re.findall(r'\d+|[a-z]+', v)
        result = []
        for part in parts:
            if part.isdigit():
                result.append(int(part))
            else:
                # Convert letters to numbers (a=1, b=2, etc.)
                result.append(ord(part[0]) - ord('a') + 1)
        return result
    
    v1_parts = parse_version(version1)
    v2_parts = parse_version(version2)
    
    # Pad shorter version with zeros
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))
    
    for p1, p2 in zip(v1_parts, v2_parts):
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    
    return 0


class ModInstaller:
    """Handles the installation of mods from URLs."""
    
    def __init__(self, log_callback):
        """
        Initialize the mod installer.
        
        Args:
            log_callback: Function to call for logging messages
        """
        self.log = log_callback
        self.download_failures = {}  # Track failed downloads: {mod_name: {'url': url, 'attempts': count}}
    
    def _extract_version_from_text(self, content):
        """
        Extract version string directly from raw mod_info.json text.
        Searches for "version" field (not "gameVersion") and extracts the value.
        
        This bypasses JSON parsing entirely, making it robust against malformed JSON.
        
        Args:
            content: Raw text content of mod_info.json
            
        Returns:
            str: Version string (e.g., "1.5.0", "0.12.1b", "2.0a")
        """
        # First try: object format like version: {major: 0, minor: 12, patch: "1b"}
        # This must come BEFORE the simple string match to avoid capturing gameVersion
        version_block = re.search(r'"?version"?\s*:\s*\{([^}]+)\}', content, re.IGNORECASE)
        if version_block:
            block = version_block.group(1)
            major = re.search(r'"?major"?\s*:\s*["\']?([0-9]+)', block, re.IGNORECASE)
            minor = re.search(r'"?minor"?\s*:\s*["\']?([0-9]+)', block, re.IGNORECASE)
            patch = re.search(r'"?patch"?\s*:\s*["\']?([0-9a-zA-Z]+)', block, re.IGNORECASE)
            
            if major:
                parts = [major.group(1)]
                if minor:
                    parts.append(minor.group(1))
                if patch:
                    parts.append(patch.group(1))
                return '.'.join(parts)
        
        # Second try: simple version string like "version": "1.5.0" or version: "1.5.0"
        # Use negative lookbehind to exclude "gameVersion"
        match = re.search(r'(?<!game)"?version"?\s*:\s*["\']?([0-9]+[0-9a-zA-Z._-]*)', content, re.IGNORECASE)
        if match:
            version = match.group(1).rstrip('",}] ')
            return version
        
        return 'unknown'
    
    def _extract_id_from_text(self, content):
        """
        Extract mod ID directly from raw mod_info.json text.
        Searches for "id" and extracts the value.
        
        Args:
            content: Raw text content of mod_info.json
            
        Returns:
            str: Mod ID or None if not found
        """
        # Look for "id" followed by value
        # Handles: "id": "value", id: "value", id:'value'
        match = re.search(r'id["\s:]+["\']([^"\']+)["\']', content, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def install_mod(self, mod, mods_dir):
        """
        Install a single mod (download + extract). For parallel workflows,
        prefer calling download_archive() in threads then extract_archive() sequentially.
        """
        try:
            mod_version = mod.get('version')
            if mod_version:
                self.log(f"  Downloading {mod['name']} v{mod_version}...")
            else:
                self.log(f"  Downloading {mod['name']}...")
            
            self.log(f"  From: {mod['download_url']}")
            
            temp_file, is_7z = self.download_archive(mod)
            if temp_file is None:
                return False
            try:
                self.log(f"  Inspecting archive contents...")
                success = self.extract_archive(temp_file, mods_dir, is_7z)
                if success:
                    self.log(f"  ✓ {mod['name']} installed successfully")
                return success
            finally:
                try:
                    if temp_file and Path(temp_file).exists():
                        Path(temp_file).unlink()
                except Exception:
                    pass
            
        except requests.exceptions.RequestException as e:
            self.log(f"  ✗ Download error: {e}", error=True)
            return False
        except zipfile.BadZipFile:
            self.log(f"  ✗ Error: Corrupted ZIP file", error=True)
            return False
        except Exception as e:
            self.log(f"  ✗ Unexpected error: {e}", error=True)
            return False

    def download_archive(self, mod):
        """Download mod archive to a temporary file. Returns (path, is_7z) or (None, False) on error."""
        try:
            response = requests.get(mod['download_url'], stream=True, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            url_lower = mod['download_url'].lower()
            content_type = response.headers.get('Content-Type', '').lower()
            is_7z = '.7z' in url_lower or '7z' in content_type
            temp_fd = None
            suffix = '.7z' if is_7z else '.zip'
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix='modlist_')
            with os.fdopen(temp_fd, 'wb') as f:
                temp_fd = None
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
            return temp_path, is_7z
        except requests.exceptions.RequestException as e:
            self.log(f"  ✗ Download error: {e}", error=True)
            # Track failure for Google Drive URLs
            self._track_download_failure(mod)
            try:
                if temp_fd is not None:
                    os.close(temp_fd)
            except Exception:
                pass
            return None, False
        except Exception as e:
            self.log(f"  ✗ Unexpected error during download: {e}", error=True)
            self._track_download_failure(mod)
            try:
                if temp_fd is not None:
                    os.close(temp_fd)
            except Exception:
                pass
            return None, False
    
    def _track_download_failure(self, mod):
        """Track download failures for Google Drive URLs."""
        url = mod['download_url']
        if 'drive.google.com' in url or 'drive.usercontent.google.com' in url:
            mod_name = mod.get('name', 'Unknown')
            if mod_name not in self.download_failures:
                self.download_failures[mod_name] = {'url': url, 'attempts': 0}
            self.download_failures[mod_name]['attempts'] += 1
    
    def get_failed_google_drive_mods(self):
        """Get list of Google Drive mods that failed after multiple attempts."""
        failed = []
        for mod_name, info in self.download_failures.items():
            if info['attempts'] >= 3:
                failed.append({'name': mod_name, 'url': info['url']})
        return failed
    
    def reset_failure_tracking(self):
        """Reset the download failure tracking."""
        self.download_failures = {}
    
    def extract_archive(self, temp_file, mods_dir, is_7z):
        """
        Extract an archive file to the mods directory.
        
        Args:
            temp_file: Path to the temporary archive file
            mods_dir: Path to the Starsector mods directory
            is_7z: Boolean indicating if the file is a 7z archive
            
        Returns:
            bool or str: True if extraction succeeded, 'skipped' if skipped, False otherwise
        """
        try:
            if is_7z:
                return self._extract_7z(temp_file, mods_dir)
            else:
                return self._extract_zip(temp_file, mods_dir)
        except Exception as e:
            self.log(f"  ✗ Extraction error: {e}", error=True)
            return False
    
    def _extract_7z(self, temp_file, mods_dir):
        """Extract a 7z archive."""
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

                # Check if mod already installed (7z doesn't support easy JSON reading, skip version check)
                already_result = self._is_already_installed_simple(members, mods_dir)
                if already_result:
                    return already_result

                # Validate all members for zip-slip protection
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
    
    def _extract_zip(self, temp_file, mods_dir):
        """Extract a ZIP archive with zip-slip protection."""
        with zipfile.ZipFile(temp_file, 'r') as zip_ref:
            members = [m for m in zip_ref.namelist() if m and not m.endswith('/')]
            
            if not members:
                self.log("  ✗ Error: Archive is empty", error=True)
                return False

            # Check if mod already installed and get folder to delete if updating
            already_result = self._is_already_installed_zip(zip_ref, members, mods_dir)
            
            # If it's a tuple, it means we need to delete the old version first
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
                # String result means 'skipped'
                return already_result

            # Validate all members for zip-slip protection
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
    
    def _is_already_installed_simple(self, members, mods_dir):
        """
        Simple check if mod folder exists (for 7z archives).
        
        Args:
            members: List of file paths in the archive
            mods_dir: Path to the Starsector mods directory
            
        Returns:
            str or bool: 'skipped' if already installed, False otherwise
        """
        top_level = set(Path(m).parts[0] for m in members if Path(m).parts)

        if len(top_level) == 1:
            root_dir = next(iter(top_level))
            mod_root = mods_dir / root_dir
            if mod_root.exists():
                self.log(f"  ℹ Skipped: Mod '{root_dir}' already installed", info=True)
                return 'skipped'
        else:
            for member in members:
                dest = mods_dir / Path(member)
                if dest.exists():
                    self.log("  ℹ Skipped: Installation would overlap existing files", info=True)
                    return 'skipped'
        
        return False
    
    def _is_already_installed_zip(self, zip_ref, members, mods_dir):
        """
        Check if a mod is already installed by comparing mod_info.json versions.
        
        Args:
            zip_ref: ZipFile object
            members: List of file paths in the archive
            mods_dir: Path to the Starsector mods directory
            
        Returns:
            str: 'skipped' if same/older version
            tuple: (folder_path, True) if update needed (newer version)
            bool: False if not installed
        """
        top_level = set(Path(m).parts[0] for m in members if Path(m).parts)

        if len(top_level) == 1:
            # Archive has a single root folder
            root_dir = next(iter(top_level))
            mod_root = mods_dir / root_dir
            
            if mod_root.exists():
                # Check if mod_info.json exists in both archive and installed mod
                mod_info_path_in_archive = f"{root_dir}/mod_info.json"
                installed_mod_info = mod_root / "mod_info.json"
                
                if mod_info_path_in_archive in members and installed_mod_info.exists():
                    try:
                        # Read installed mod_info.json (raw text)
                        with open(installed_mod_info, 'r', encoding='utf-8') as f:
                            installed_content = f.read()
                        
                        # Read new mod_info.json from archive (raw text)
                        with zip_ref.open(mod_info_path_in_archive) as archive_file:
                            new_content = archive_file.read().decode('utf-8')
                        
                        # Extract versions directly from raw text (no JSON parsing needed)
                        installed_version = self._extract_version_from_text(installed_content)
                        new_version = self._extract_version_from_text(new_content)
                        
                        # Extract mod ID directly from raw text (fallback to folder name)
                        mod_id = self._extract_id_from_text(new_content) or root_dir
                        
                        # Compare versions
                        version_comparison = _compare_versions(new_version, installed_version)
                        
                        if version_comparison > 0:
                            # New version is higher - return folder to delete
                            self.log(f"  ⬆ Update available: '{mod_id}' {installed_version} → {new_version}", info=True)
                            self.log(f"  Installing newer version...", info=True)
                            return (mod_root, True)  # Return folder to delete + update flag
                        elif version_comparison < 0:
                            # New version is lower - skip
                            self.log(f"  ℹ Skipped: '{mod_id}' v{installed_version} is newer than archive v{new_version}", info=True)
                            return 'skipped'
                        else:
                            # Same version - skip
                            self.log(f"  ℹ Skipped: '{mod_id}' v{installed_version} already installed", info=True)
                            return 'skipped'
                            
                    except (IOError, UnicodeDecodeError) as e:
                        # File reading issues
                        self.log(f"  ⚠ Warning: Error reading mod metadata - {type(e).__name__}", info=True)
                        self.log(f"  ℹ Skipped: Mod '{root_dir}' already installed (version comparison unavailable)", info=True)
                        return 'skipped'
                else:
                    # No mod_info.json, just check existence
                    self.log(f"  ℹ Skipped: Mod '{root_dir}' already installed", info=True)
                    return 'skipped'
        else:
            # Archive has multiple files at root level
            for member in members:
                dest = mods_dir / Path(member)
                if dest.exists():
                    self.log("  ℹ Skipped: Installation would overlap existing files", info=True)
                    return 'skipped'
        
        return False
