"""
Tests for Google Drive URL fixing functionality.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from gui.dialogs import fix_google_drive_url
from core.installer import ModInstaller


def test_fix_google_drive_url_with_file_d_format():
    """Test fixing Google Drive URL with /file/d/ID/view format."""
    original = "https://drive.google.com/file/d/1ABC123xyz/view?usp=sharing"
    expected = "https://drive.usercontent.google.com/download?id=1ABC123xyz&export=download&confirm=t"
    assert fix_google_drive_url(original) == expected


def test_fix_google_drive_url_with_id_param():
    """Test fixing Google Drive URL with ?id=ID format."""
    original = "https://drive.google.com/uc?id=1ABC123xyz&export=download"
    expected = "https://drive.usercontent.google.com/download?id=1ABC123xyz&export=download&confirm=t"
    assert fix_google_drive_url(original) == expected


def test_fix_google_drive_url_non_google():
    """Test that non-Google Drive URLs are not modified."""
    original = "https://example.com/mod.zip"
    assert fix_google_drive_url(original) == original


def test_fix_google_drive_url_no_id():
    """Test Google Drive URL without extractable ID."""
    original = "https://drive.google.com/invalid"
    assert fix_google_drive_url(original) == original


def test_track_download_failure():
    """Test tracking download failures for Google Drive mods."""
    def dummy_log(msg, error=False, info=False):
        pass
    
    installer = ModInstaller(dummy_log)
    
    # Create a Google Drive mod
    mod = {
        'name': 'TestMod',
        'download_url': 'https://drive.google.com/file/d/ABC123/view'
    }
    
    # Track 3 failures
    for _ in range(3):
        installer._track_download_failure(mod)
    
    # Should be detected as failed
    failed = installer.get_failed_google_drive_mods()
    assert len(failed) == 1
    assert failed[0]['name'] == 'TestMod'
    assert failed[0]['url'] == mod['download_url']


def test_track_download_failure_non_google():
    """Test that non-Google Drive failures are not tracked."""
    def dummy_log(msg, error=False, info=False):
        pass
    
    installer = ModInstaller(dummy_log)
    
    # Create a non-Google Drive mod
    mod = {
        'name': 'TestMod',
        'download_url': 'https://example.com/mod.zip'
    }
    
    # Track failures
    for _ in range(3):
        installer._track_download_failure(mod)
    
    # Should not be tracked
    failed = installer.get_failed_google_drive_mods()
    assert len(failed) == 0


def test_track_download_failure_less_than_threshold():
    """Test that mods with less than 3 failures are not returned."""
    def dummy_log(msg, error=False, info=False):
        pass
    
    installer = ModInstaller(dummy_log)
    
    mod = {
        'name': 'TestMod',
        'download_url': 'https://drive.google.com/file/d/ABC123/view'
    }
    
    # Track only 2 failures
    for _ in range(2):
        installer._track_download_failure(mod)
    
    # Should not reach threshold
    failed = installer.get_failed_google_drive_mods()
    assert len(failed) == 0


def test_reset_failure_tracking():
    """Test resetting failure tracking."""
    def dummy_log(msg, error=False, info=False):
        pass
    
    installer = ModInstaller(dummy_log)
    
    mod = {
        'name': 'TestMod',
        'download_url': 'https://drive.google.com/file/d/ABC123/view'
    }
    
    # Track failures
    for _ in range(3):
        installer._track_download_failure(mod)
    
    # Should have failures
    assert len(installer.get_failed_google_drive_mods()) == 1
    
    # Reset
    installer.reset_failure_tracking()
    
    # Should be empty
    assert len(installer.get_failed_google_drive_mods()) == 0
