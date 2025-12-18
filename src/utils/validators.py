"""Validation utilities: URLs and Starsector installation paths."""

import time
import requests
import platform
import shutil
from pathlib import Path
from typing import Optional, Union, Tuple

from core.constants import URL_VALIDATION_TIMEOUT_HEAD, CACHE_TIMEOUT


# ============================================================================
# URL Validation
# ============================================================================

class URLValidator:
    """URL validator with built-in caching to avoid redundant network requests."""
    
    def __init__(self):
        """Initialize validator with empty cache."""
        self._cache = {}
    
    def _is_cached(self, url: str) -> tuple[bool, bool | None]:
        """Check if URL validation result is cached and still valid.
        
        Args:
            url: URL to check
            
        Returns:
            tuple: (is_cached: bool, is_valid: bool or None)
        """
        if url in self._cache:
            is_valid, timestamp = self._cache[url]
            if time.time() - timestamp < CACHE_TIMEOUT:
                return (True, is_valid)
        return (False, None)
    
    def _cache_result(self, url: str, is_valid: bool) -> None:
        """Store URL validation result in cache.
        
        Args:
            url: URL to cache
            is_valid: Validation result
        """
        self._cache[url] = (is_valid, time.time())
    
    def validate(self, url: str, use_cache: bool = True) -> bool:
        """Validate URL by checking HTTP response.
        
        Uses HEAD request first, falls back to GET if needed.
        Results are cached to avoid redundant requests.
        
        Args:
            url: URL to validate
            use_cache: If True, use cached results (default: True)
            
        Returns:
            bool: True if URL is valid (2xx or 3xx status), False otherwise
        """
        if use_cache:
            is_cached, is_valid = self._is_cached(url)
            if is_cached:
                return is_valid
        
        try:
            resp = requests.head(url, timeout=URL_VALIDATION_TIMEOUT_HEAD, allow_redirects=True)
            if 200 <= resp.status_code < 400:
                result = True
            else:
                resp = requests.get(url, stream=True, timeout=URL_VALIDATION_TIMEOUT_HEAD, allow_redirects=True)
                result = 200 <= resp.status_code < 400
            
            self._cache_result(url, result)
            return result
        except Exception:
            self._cache_result(url, False)
            return False
    
    def clear_cache(self) -> None:
        """Clear all cached validation results."""
        self._cache.clear()
    
    def get_cache_size(self) -> int:
        """Get number of cached URLs.
        
        Returns:
            int: Number of URLs in cache
        """
        return len(self._cache)


# ============================================================================
# Starsector Path Validation
# ============================================================================

class StarsectorPathValidator:
    """Validator for Starsector installation paths with auto-detection."""
    
    @staticmethod
    def auto_detect() -> Optional[Path]:
        """Auto-detect Starsector installation by OS.
        
        Returns:
            Path or None: Valid Starsector installation path if found
        """
        system = platform.system()
        
        if system == "Windows":
            possible_paths = [
                Path(r"C:\Program Files (x86)\Fractal Softworks\Starsector"),
                Path(r"C:\Program Files\Fractal Softworks\Starsector"),
                Path.home() / "Games" / "Starsector",
            ]
        elif system == "Darwin":
            possible_paths = [
                Path("/Applications/Starsector.app"),
                Path.home() / "Applications" / "Starsector.app",
                Path.home() / "Games" / "Starsector.app",
            ]
        else:
            possible_paths = [
                Path.home() / "starsector",
                Path.home() / "Games" / "starsector",
                Path("/opt/starsector"),
            ]
        
        for path in possible_paths:
            if StarsectorPathValidator.validate(path):
                return path
        return None
    
    @staticmethod
    def validate(path: Union[str, Path, None]) -> bool:
        """Validate Starsector installation path. Creates mods folder if missing.
        
        Args:
            path: Path to validate
            
        Returns:
            bool: True if valid Starsector installation
        """
        if not path:
            return False
        
        path_obj = Path(path) if isinstance(path, str) else path
        if not path_obj.exists():
            return False
        
        # macOS: .app bundles need Contents/ folder
        if str(path_obj).endswith('.app'):
            if not (path_obj / "Contents").exists():
                return False
            StarsectorPathValidator._ensure_mods_folder(path_obj)
            return True
        
        # Windows/Linux: check for Starsector files
        has_data = (path_obj / "data").exists()
        has_exe = (path_obj / "starsector.exe").exists()
        has_sh = (path_obj / "starsector.sh").exists()
        
        if not (has_data or has_exe or has_sh):
            return False
        
        mods_folder = path_obj / "mods"
        if not mods_folder.exists():
            try:
                mods_folder.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                return False
        return True
    
    @staticmethod
    def _ensure_mods_folder(path: Path) -> bool:
        """Create mods folder if it doesn't exist.
        
        Args:
            path: Base path
            
        Returns:
            bool: True if mods folder exists or was created
        """
        mods_folder = path / "mods"
        if mods_folder.exists():
            return True
        try:
            mods_folder.mkdir(parents=True, exist_ok=True)
            return True
        except (OSError, PermissionError):
            return False
    
    @staticmethod
    def check_disk_space(path: Union[str, Path], required_gb: float = 5) -> Tuple[bool, float]:
        """Check free disk space at given path.
        
        Args:
            path: Path to check
            required_gb: Minimum required space in GB
            
        Returns:
            tuple: (has_space: bool, free_gb: float)
        """
        try:
            path_obj = Path(path) if isinstance(path, str) else path
            stat = shutil.disk_usage(path_obj)
            free_gb = stat.free / (1024 ** 3)
            return free_gb >= required_gb, free_gb
        except (OSError, AttributeError):
            return False, 0.0
    
    @staticmethod
    def get_mods_dir(path: Union[str, Path]) -> Path:
        """Get mods directory path.
        
        Args:
            path: Base Starsector path
            
        Returns:
            Path: Mods directory path
        """
        path_obj = Path(path) if isinstance(path, str) else path
        return path_obj / "mods"
