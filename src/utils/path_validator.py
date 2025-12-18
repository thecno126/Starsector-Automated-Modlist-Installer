"""Starsector installation path validation and auto-detection."""
from pathlib import Path
from typing import Optional, Union, Tuple
import platform
import shutil


class StarsectorPathValidator:
    
    @staticmethod
    def auto_detect() -> Optional[Path]:
        """Auto-detect Starsector installation by OS."""
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
        """Validate Starsector installation path. Creates mods folder if missing."""
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
        """Create mods folder if it doesn't exist."""
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
        """Check free disk space. Returns (has_space, free_gb)."""
        try:
            path_obj = Path(path) if isinstance(path, str) else path
            stat = shutil.disk_usage(path_obj)
            free_gb = stat.free / (1024 ** 3)
            return free_gb >= required_gb, free_gb
        except (OSError, AttributeError):
            return False, 0.0
    
    @staticmethod
    def get_mods_dir(path: Union[str, Path]) -> Path:
        """Return mods directory path."""
        path_obj = Path(path) if isinstance(path, str) else path
        return path_obj / "mods"
