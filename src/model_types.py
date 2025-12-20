"""Type definitions for better code clarity and IDE support."""
from typing import NamedTuple, Optional
from pathlib import Path


class DownloadResult(NamedTuple):
    """Result of mod archive download operation."""
    temp_path: Optional[str]
    is_7z: bool


class ModVersionCheck(NamedTuple):
    """Result of mod version comparison check."""
    is_current: bool
    installed_version: Optional[str]


class BackupResult(NamedTuple):
    """Result of backup creation/restore operation."""
    path: Optional[Path]
    success: bool
    error: Optional[str]
