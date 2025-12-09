"""
Path validation utilities for Starsector installation.
Extracted from main_window.py to reduce complexity.
"""

from pathlib import Path
import os
import platform
import shutil


class StarsectorPathValidator:
    """Validates and manages Starsector installation paths."""
    
    @staticmethod
    def auto_detect():
        """
        Auto-detect Starsector installation path based on OS.
        
        Returns:
            Path or None: Detected path if found, None otherwise
        """
        system = platform.system()
        
        if system == "Windows":
            possible_paths = [
                Path(r"C:\Program Files (x86)\Fractal Softworks\Starsector"),
                Path(r"C:\Program Files\Fractal Softworks\Starsector"),
                Path.home() / "Games" / "Starsector",
            ]
        elif system == "Darwin":  # macOS
            possible_paths = [
                Path("/Applications/Starsector.app"),
                Path.home() / "Applications" / "Starsector.app",
                Path.home() / "Games" / "Starsector.app",
            ]
        else:  # Linux
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
    def validate(path_obj):
        """
        Validate if a path is a valid Starsector installation.
        
        Args:
            path_obj: Path object or string to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not path_obj:
            return False
        
        if isinstance(path_obj, str):
            path_obj = Path(path_obj)
        
        if not path_obj.exists():
            return False
        
        # For macOS .app bundles, just check basic structure
        if str(path_obj).endswith('.app'):
            # Verify it's a valid .app bundle
            if not (path_obj / "Contents").exists():
                return False
            # Ensure mods folder exists (create if needed)
            StarsectorPathValidator._ensure_mods_folder(path_obj)
            return True
        
        # For Windows/Linux, check for typical Starsector files
        # At minimum, there should be a data folder or starsector executable
        has_data = (path_obj / "data").exists()
        has_exe = (path_obj / "starsector.exe").exists()  # Windows
        has_sh = (path_obj / "starsector.sh").exists()    # Linux
        
        if not (has_data or has_exe or has_sh):
            return False
        
        # Ensure mods folder exists (create if needed)
        mods_folder = path_obj / "mods"
        if not mods_folder.exists():
            try:
                mods_folder.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                return False
        
        return True
    
    @staticmethod
    def _ensure_mods_folder(path):
        """Ensure mods folder exists, create if missing."""
        mods_folder = path / "mods"
        
        if not mods_folder.exists():
            try:
                mods_folder.mkdir(parents=True, exist_ok=True)
                return True
            except (OSError, PermissionError):
                return False
        return True
    
    @staticmethod
    def check_disk_space(path, required_gb=5):
        """
        Check if there's enough free disk space at the given path.
        
        Args:
            path: Path to check
            required_gb: Required free space in GB
            
        Returns:
            tuple: (bool, float) - (has_space, free_gb)
        """
        try:
            if isinstance(path, str):
                path = Path(path)
            
            # Get disk usage stats
            stat = shutil.disk_usage(path)
            free_gb = stat.free / (1024 ** 3)  # Convert to GB
            
            has_space = free_gb >= required_gb
            return has_space, free_gb
        except (OSError, AttributeError):
            return False, 0.0
    
    @staticmethod
    def get_mods_dir(path):
        """
        Get the mods directory for a Starsector installation.
        
        Args:
            path: Starsector installation path
            
        Returns:
            Path: Mods directory path
        """
        if isinstance(path, str):
            path = Path(path)
        
        return path / "mods"
