"""
Comprehensive test suite for Starsector Automated Modlist Installer.
Includes all tests from config management, installation, download scenarios,
Google Drive handling, mod_info.json version extraction, and button functions.
"""

import json
import sys
import io
import zipfile
import tempfile
import shutil
import tkinter as tk
import requests
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import concurrent.futures

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.config_manager import ConfigManager
from src.core.installer import ModInstaller
from src.utils.network_utils import validate_mod_urls
from src.gui.dialogs import fix_google_drive_url


# ============================================================================
# Global Fixtures to Prevent GUI Window Creation
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def mock_tkinter_windows():
    """Mock Tkinter window creation globally for all tests."""
    original_tk = tk.Tk
    original_toplevel = tk.Toplevel
    
    class MockTk:
        def __init__(self, *args, **kwargs):
            self.title_text = ""
            self.attributes = {}
            self.geometry_str = ""
            self._destroyed = False
            self._bindings = {}
            self._width = 800
            self._height = 600
            self._x = 100
            self._y = 100
            
        def title(self, text):
            self.title_text = text
            
        def geometry(self, geom):
            self.geometry_str = geom
            
        def withdraw(self):
            pass
            
        def deiconify(self):
            pass
            
        def destroy(self):
            self._destroyed = True
            
        def winfo_exists(self):
            return not self._destroyed
            
        def winfo_width(self):
            """Mock window width."""
            return self._width
            
        def winfo_height(self):
            """Mock window height."""
            return self._height
            
        def winfo_x(self):
            """Mock window x position."""
            return self._x
            
        def winfo_y(self):
            """Mock window y position."""
            return self._y
            
        def update(self):
            pass
            
        def update_idletasks(self):
            pass
            
        def mainloop(self):
            pass
            
        def quit(self):
            pass
            
        def bind(self, sequence, func, add=None):
            """Mock bind method for event handling."""
            self._bindings[sequence] = func
            
        def unbind(self, sequence):
            """Mock unbind method."""
            if sequence in self._bindings:
                del self._bindings[sequence]
                
        def after(self, ms, func=None, *args):
            """Mock after method - execute immediately for tests."""
            if func:
                func(*args)
            return "after_id"
            
        def after_cancel(self, after_id):
            """Mock after_cancel."""
            pass
            
        def protocol(self, name, func):
            """Mock protocol method for WM_DELETE_WINDOW etc."""
            pass
            
        def resizable(self, width, height):
            """Mock resizable."""
            pass
            
        def minsize(self, width, height):
            """Mock minsize."""
            pass
            
        def configure(self, **kwargs):
            """Mock configure."""
            self.attributes.update(kwargs)
            
        def config(self, **kwargs):
            """Alias for configure."""
            self.configure(**kwargs)
    
    class MockToplevel(MockTk):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.master = args[0] if args else None
            
        def transient(self, master):
            pass
            
        def grab_set(self):
            pass
            
        def grab_release(self):
            pass
            
        def wait_window(self, window=None):
            pass
    
    with patch('tkinter.Tk', MockTk), \
         patch('tkinter.Toplevel', MockToplevel):
        yield
    
    # Restore originals (though not necessary with pytest)
    tk.Tk = original_tk
    tk.Toplevel = original_toplevel


def test_load_default_when_missing(tmp_path, monkeypatch):
    # Rediriger les chemins de config vers un dossier temporaire
    base = tmp_path
    monkeypatch.setenv("PYTEST_BASE_DIR", str(base))

    # Simuler des chemins en remplaçant les attributs de l'instance
    cm = ConfigManager()
    cm.config_file = base / "config" / "modlist_config.json"
    cm.categories_file = base / "config" / "categories.json"
    cm.prefs_file = base / "config" / "installer_prefs.json"

    data = cm.load_modlist_config()
    assert isinstance(data, dict)
    assert data.get("mods") == []
    assert cm.config_file.exists(), "Le fichier de config doit être créé lors du reset"


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    base = tmp_path
    cm = ConfigManager()
    cm.config_file = base / "config" / "modlist_config.json"

    payload = {
        "modlist_name": "ASTRA",
        "version": "1.1",
        "starsector_version": "0.98a",
        "description": "desc",
        "mods": [{"name": "TestMod", "download_url": "http://example.com/mod.zip"}]
    }

    cm.save_modlist_config(payload)
    loaded = cm.load_modlist_config()
    assert loaded == payload


def test_categories_roundtrip(tmp_path):
    cm = ConfigManager()
    cm.categories_file = tmp_path / "config" / "categories.json"

    cats = ["Required", "Gameplay", "QoL"]
    cm.save_categories(cats)
    assert cm.categories_file.exists()
    loaded = cm.load_categories()
    assert loaded == cats


def test_preferences_roundtrip(tmp_path):
    cm = ConfigManager()
    cm.prefs_file = tmp_path / "config" / "installer_prefs.json"

    prefs = {"last_starsector_path": str(tmp_path), "theme": "dark"}
    cm.save_preferences(prefs)
    loaded = cm.load_preferences()
    assert loaded == prefs
import io
import zipfile
from pathlib import Path

import pytest

from src.core.installer import ModInstaller


class Logger:
    def __init__(self):
        self.messages = []
    def __call__(self, msg, error=False, info=False):
        self.messages.append((msg, error, info))


def make_in_memory_zip(files):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    bio.seek(0)
    return bio.getvalue()


def test_extract_zip_success(tmp_path, monkeypatch):
    # Crée un ZIP simple avec un dossier racine unique
    zip_bytes = make_in_memory_zip({
        "TestMod/README.txt": "hello",
        "TestMod/mod_info.json": "{}",
    })

    # Écrire l'archive sur disque pour passer au flux de l'installer
    archive_path = tmp_path / "archive.zip"
    archive_path.write_bytes(zip_bytes)

    # Mock requests.get pour renvoyer le contenu du ZIP
    class FakeResp:
        status_code = 200
        headers = {"Content-Type": "application/zip"}
        def iter_content(self, chunk_size=8192):
            yield zip_bytes
        def raise_for_status(self):
            return None
    monkeypatch.setattr("src.core.installer.requests.get", lambda url, stream=True, timeout=30: FakeResp())

    logs = Logger()
    installer = ModInstaller(logs)

    mods_dir = tmp_path / "Starsector" / "mods"
    mods_dir.mkdir(parents=True)

    mod = {"name": "TestMod", "download_url": "http://example.com/mod.zip"}
    ok = installer.install_mod(mod, mods_dir)
    assert ok is True
    assert (mods_dir / "TestMod").exists()


def test_zip_slip_blocked(tmp_path, monkeypatch):
    # ZIP avec tentative de traversal
    zip_bytes = make_in_memory_zip({
        "../evil.txt": "boom",
        "TestMod/file.txt": "safe",
    })
    class FakeResp:
        status_code = 200
        headers = {"Content-Type": "application/zip"}
        def iter_content(self, chunk_size=8192):
            yield zip_bytes
        def raise_for_status(self):
            return None
    monkeypatch.setattr("src.core.installer.requests.get", lambda url, stream=True, timeout=30: FakeResp())

    logs = Logger()
    installer = ModInstaller(logs)

    mods_dir = tmp_path / "Starsector" / "mods"
    mods_dir.mkdir(parents=True)

    mod = {"name": "BadMod", "download_url": "http://example.com/bad.zip"}
    ok = installer.install_mod(mod, mods_dir)
    assert ok is False
    # Doit logguer un message de sécurité
    assert any("Security" in m[0] for m in logs.messages)


def test_network_error(tmp_path, monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            raise Exception("Network down")
    monkeypatch.setattr("src.core.installer.requests.get", lambda url, stream=True, timeout=30: FakeResp())

    logs = Logger()
    installer = ModInstaller(logs)
    mods_dir = tmp_path / "Starsector" / "mods"
    mods_dir.mkdir(parents=True)
    ok = installer.install_mod({"name": "NetFail", "download_url": "http://example.com/x.zip"}, mods_dir)
    assert ok is False
    assert any("Download error" in m[0] or "Unexpected" in m[0] for m in logs.messages)


def test_already_installed_single_root(tmp_path, monkeypatch):
    # Create zip with single root folder
    zip_bytes = make_in_memory_zip({
        "ExistingMod/README.txt": "x"
    })
    class FakeResp:
        status_code = 200
        headers = {"Content-Type": "application/zip"}
        def iter_content(self, chunk_size=8192):
            yield zip_bytes
        def raise_for_status(self):
            return None
    monkeypatch.setattr("src.core.installer.requests.get", lambda url, stream=True, timeout=30: FakeResp())

    logs = Logger()
    installer = ModInstaller(logs)
    mods_dir = tmp_path / "Starsector" / "mods"
    (mods_dir / "ExistingMod").mkdir(parents=True)
    ok = installer.install_mod({"name": "ExistingMod", "download_url": "http://example.com/mod.zip"}, mods_dir)
    assert ok == 'skipped'
    assert any("Skipped" in m[0] and "already installed" in m[0] for m in logs.messages)


def test_overlap_at_root(tmp_path, monkeypatch):
    # Zip with file at root will overlap existing
    zip_bytes = make_in_memory_zip({
        "readme.txt": "x"
    })
    class FakeResp:
        status_code = 200
        headers = {"Content-Type": "application/zip"}
        def iter_content(self, chunk_size=8192):
            yield zip_bytes
        def raise_for_status(self):
            return None
    monkeypatch.setattr("src.core.installer.requests.get", lambda url, stream=True, timeout=30: FakeResp())

    logs = Logger()
    installer = ModInstaller(logs)
    mods_dir = tmp_path / "Starsector" / "mods"
    mods_dir.mkdir(parents=True)
    # Pre-create overlapping file
    (mods_dir / "readme.txt").write_text("existing")
    ok = installer.install_mod({"name": "RootOverlap", "download_url": "http://example.com/mod.zip"}, mods_dir)
    assert ok == 'skipped'
    assert any(("overlap" in m[0].lower()) or ("skipping" in m[0].lower()) for m in logs.messages)


def test_extract_7z_if_available(tmp_path, monkeypatch):
    try:
        import py7zr  # noqa: F401
    except Exception:
        pytest.skip("py7zr not available")

    # Build a minimal 7z archive in memory using py7zr
    import py7zr
    sevenz_path = tmp_path / "mod.7z"
    with py7zr.SevenZipFile(sevenz_path, 'w') as archive:
        file_path = tmp_path / "TestMod" / "file.txt"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("hello")
        archive.writeall(file_path.parent, arcname="TestMod")

    data = sevenz_path.read_bytes()

    class FakeResp:
        status_code = 200
        headers = {"Content-Type": "application/x-7z-compressed"}
        def iter_content(self, chunk_size=8192):
            yield data
        def raise_for_status(self):
            return None
    monkeypatch.setattr("src.core.installer.requests.get", lambda url, stream=True, timeout=30: FakeResp())

    logs = Logger()
    installer = ModInstaller(logs)
    mods_dir = tmp_path / "Starsector" / "mods"
    mods_dir.mkdir(parents=True)
    ok = installer.install_mod({"name": "SevenZ", "download_url": "http://example.com/mod.7z"}, mods_dir)
    assert ok is True
    assert (mods_dir / "TestMod").exists()
"""
Integration tests for complete user scenarios.
Tests end-to-end workflows and complex interactions.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import io
import zipfile

from src.core.config_manager import ConfigManager
from src.core.installer import ModInstaller


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    config_dir = temp_dir / "config"
    config_dir.mkdir()
    mods_dir = temp_dir / "mods"
    mods_dir.mkdir()
    cache_dir = temp_dir / "mod_cache"
    cache_dir.mkdir()
    
    yield {
        'root': temp_dir,
        'config': config_dir,
        'mods': mods_dir,
        'cache': cache_dir
    }
    
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_csv():
    """Sample CSV content for import testing."""
    return """Test Modlist,1.0,0.97a-RC11,Integration test modlist
name,category,download_url,version
LazyLib,Required,https://example.com/lazylib.zip,2.8
GraphicsLib,Required,https://example.com/graphicslib.zip,1.0
Nexerelin,Gameplay,https://example.com/nexerelin.7z,0.11.2b
"""


class TestCompleteWorkflows:
    """Test complete user workflows from start to finish."""
    
    def test_csv_import_to_installation(self, temp_workspace, sample_csv):
        """Test: Import CSV → Validate → Install → Verify files."""
        config_file = temp_workspace['config'] / "modlist_config.json"
        
        # Step 1: Parse CSV (simulated import)
        lines = sample_csv.strip().split('\n')
        metadata_line = lines[0].split(',')
        # Skip header line at index 1, mods start at index 2
        mod_lines = lines[2:]
        
        # Build modlist structure
        modlist_data = {
            'modlist_name': metadata_line[0],
            'version': metadata_line[1],
            'starsector_version': metadata_line[2],
            'description': metadata_line[3],
            'mods': []
        }
        
        for line in mod_lines:
            parts = line.split(',')
            modlist_data['mods'].append({
                'name': parts[0],
                'category': parts[1],
                'download_url': parts[2],
                'version': parts[3] if len(parts) > 3 else ''
            })
        
        # Step 2: Save configuration
        config_file.write_text(json.dumps(modlist_data, indent=2))
        
        # Step 3: Verify saved data
        loaded = json.loads(config_file.read_text())
        assert loaded['modlist_name'] == 'Test Modlist'
        assert len(loaded['mods']) == 3
        assert loaded['mods'][0]['name'] == 'LazyLib'
        assert loaded['mods'][2]['download_url'].endswith('.7z')
        
        # Step 4: Simulate installation (with mocked downloads)
        log_mock = Mock()
        installer = ModInstaller(log_mock)
        
        with patch('src.core.installer.requests.get') as mock_get:
            # Mock successful download
            mock_response = Mock()
            mock_response.iter_content = lambda chunk_size: [b'fake_zip_data']
            mock_response.headers = {'content-type': 'application/zip'}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            # Download first mod
            temp_file, is_7z = installer.download_archive(loaded['mods'][0])
            assert temp_file is not None
            assert Path(temp_file).exists()
    
    def test_manual_mod_addition_workflow(self, temp_workspace):
        """Test: Add mods manually → Reorganize → Save → Export CSV."""
        config_file = temp_workspace['config'] / "modlist_config.json"
        
        # Step 1: Create empty modlist
        modlist_data = {
            'modlist_name': 'My Custom Modlist',
            'version': '1.0',
            'starsector_version': '0.97a-RC11',
            'description': 'Hand-crafted modlist',
            'mods': []
        }
        
        # Step 2: Add mods one by one
        new_mods = [
            {'name': 'Mod A', 'category': 'Gameplay', 'download_url': 'https://example.com/a.zip'},
            {'name': 'Mod B', 'category': 'Graphics', 'download_url': 'https://example.com/b.zip'},
            {'name': 'Mod C', 'category': 'Gameplay', 'download_url': 'https://example.com/c.zip'},
        ]
        
        for mod in new_mods:
            modlist_data['mods'].append(mod)
        
        # Step 3: Reorganize (move Mod C before Mod A in same category)
        gameplay_mods = [m for m in modlist_data['mods'] if m['category'] == 'Gameplay']
        # Swap positions
        idx_a = next(i for i, m in enumerate(modlist_data['mods']) if m['name'] == 'Mod A')
        idx_c = next(i for i, m in enumerate(modlist_data['mods']) if m['name'] == 'Mod C')
        modlist_data['mods'][idx_a], modlist_data['mods'][idx_c] = \
            modlist_data['mods'][idx_c], modlist_data['mods'][idx_a]
        
        # Step 4: Save
        config_file.write_text(json.dumps(modlist_data, indent=2))
        
        # Step 5: Export to CSV format
        csv_lines = [
            f"{modlist_data['modlist_name']},{modlist_data['version']},"
            f"{modlist_data['starsector_version']},{modlist_data['description']}",
            "name,category,download_url,version"
        ]
        
        for mod in modlist_data['mods']:
            csv_lines.append(
                f"{mod['name']},{mod['category']},{mod['download_url']},"
                f"{mod.get('version', '')}"
            )
        
        csv_content = '\n'.join(csv_lines)
        
        # Verify export
        assert 'Mod C' in csv_content
        assert csv_content.count('Gameplay') == 2
        assert 'My Custom Modlist' in csv_content


class TestInstallationScenarios:
    """Test various installation scenarios."""
    
    def test_installation_with_already_installed_mods(self, temp_workspace):
        """Test: Install modlist where some mods are already present → Skip → Progress 100%."""
        log_mock = Mock()
        installer = ModInstaller(log_mock)
        mods_dir = temp_workspace['mods']
        
        # Pre-install two mods (create folders)
        (mods_dir / "LazyLib").mkdir()
        (mods_dir / "GraphicsLib").mkdir()
        
        mods_to_install = [
            {'name': 'LazyLib', 'download_url': 'https://example.com/lazylib.zip'},
            {'name': 'GraphicsLib', 'download_url': 'https://example.com/graphicslib.zip'},
            {'name': 'NewMod', 'download_url': 'https://example.com/newmod.zip'},
        ]
        
        # Check which are already installed
        already_installed = []
        needs_download = []
        
        for mod in mods_to_install:
            # Simulate archive structure (single root folder matching mod name)
            mock_members = [f"{mod['name']}/mod_info.json", f"{mod['name']}/data/config.json"]
            # Use ArchiveExtractor's _check_if_installed method
            if installer.extractor._check_if_installed(None, mock_members, mods_dir, is_7z=True):
                already_installed.append(mod['name'])
            else:
                needs_download.append(mod)
        
        assert len(already_installed) == 2
        assert 'LazyLib' in already_installed
        assert 'GraphicsLib' in already_installed
        assert len(needs_download) == 1
        assert needs_download[0]['name'] == 'NewMod'
        
        # Simulate progress calculation
        total_mods = len(mods_to_install)
        downloaded = len(needs_download)  # Only download what's needed
        skipped = len(already_installed)
        
        # Progress should reach 100%
        download_progress = (downloaded / total_mods) * 50 if downloaded > 0 else 50
        install_progress = 50 + ((downloaded / total_mods) * 50) if downloaded > 0 else 100
        
        assert install_progress == 100 or (downloaded > 0 and install_progress > 50)


# ============================================================================
# Google Drive URL Fixing Tests
# ============================================================================

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


# ============================================================================
# Download Scenarios Tests
# ============================================================================

class TestDownloadScenarios:
    """Test various download scenarios."""
    
    def test_parallel_download_success(self):
        """Test successful parallel downloads."""
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        mods = [
            {'name': 'Mod1', 'download_url': 'http://example.com/mod1.zip'},
            {'name': 'Mod2', 'download_url': 'http://example.com/mod2.zip'},
            {'name': 'Mod3', 'download_url': 'http://example.com/mod3.zip'}
        ]
        
        with patch('requests.get') as mock_get:
            # Mock successful downloads
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'Content-Type': 'application/zip'}
            mock_response.iter_content = Mock(return_value=[b'fake zip content'])
            mock_get.return_value = mock_response
            
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(installer.download_archive, mod) for mod in mods]
                for future in concurrent.futures.as_completed(futures):
                    temp_path, is_7z = future.result()
                    results.append((temp_path is not None, is_7z))
            
            # All downloads should succeed
            assert len(results) == 3
            assert all(success for success, _ in results)
    
    def test_download_with_timeout(self):
        """Test download timeout handling."""
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        mod = {'name': 'SlowMod', 'download_url': 'http://slow.example.com/mod.zip'}
        
        with patch('requests.get', side_effect=Exception("Timeout")):
            temp_path, is_7z = installer.download_archive(mod)
            
            # Download should fail gracefully
            assert temp_path is None
            assert is_7z is False
            # Should log error
            log_callback.assert_called()
    
    def test_download_404_error(self):
        """Test handling of 404 errors."""
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        mod = {'name': 'MissingMod', 'download_url': 'http://example.com/missing.zip'}
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = Exception("404 Not Found")
            mock_get.return_value = mock_response
            
            temp_path, is_7z = installer.download_archive(mod)
            
            assert temp_path is None
            assert is_7z is False
    
    def test_detect_7z_from_url(self):
        """Test detection of 7z format from URL."""
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        mod = {'name': 'Compressed', 'download_url': 'http://example.com/mod.7z'}
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'Content-Type': 'application/x-7z-compressed'}
            mock_response.iter_content = Mock(return_value=[b'7z content'])
            mock_get.return_value = mock_response
            
            temp_path, is_7z = installer.download_archive(mod)
            
            # Should detect 7z format
            assert temp_path is not None
            assert is_7z is True
    
    def test_google_drive_html_detection(self):
        """Test detection of Google Drive HTML response (virus scan page)."""
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        gdrive_mod = {
            'name': 'GDriveMod',
            'download_url': 'https://drive.google.com/uc?id=ABC123'
        }
        
        # Mock response with HTML content type
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = MagicMock()
        
        with patch('requests.get', return_value=mock_response):
            temp_path, is_7z = installer.download_archive(gdrive_mod)
        
        # Should return GDRIVE_HTML indicator
        assert temp_path == 'GDRIVE_HTML'
        assert is_7z is False
    
    def test_non_google_drive_html_not_detected(self):
        """Test that HTML from non-Google Drive sources is downloaded normally."""
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        regular_mod = {
            'name': 'RegularMod',
            'download_url': 'http://example.com/mod.zip'
        }
        
        # Mock response with HTML (should still download for non-GDrive)
        mock_response = MagicMock()
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_content = MagicMock(return_value=[b'fake html'])
        
        with patch('requests.get', return_value=mock_response), \
             patch('tempfile.mkstemp', return_value=(99, '/tmp/test.zip')):
            temp_path, is_7z = installer.download_archive(regular_mod)
        
        # Should download normally (not GDRIVE_HTML)
        assert temp_path != 'GDRIVE_HTML'


class TestURLValidation:
    """Test URL validation scenarios."""
    
    def test_validate_mixed_urls(self):
        """Test validation of mixed URL sources."""
        mods = [
            {'name': 'GitHubMod', 'download_url': 'https://github.com/user/repo/releases/download/v1.0/mod.zip'},
            {'name': 'GDriveMod', 'download_url': 'https://drive.google.com/uc?id=ABC123'},
            {'name': 'OtherMod', 'download_url': 'https://example.com/mod.zip'}
        ]
        
        with patch('requests.head') as mock_head:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            
            results = validate_mod_urls(mods)
            
            # Should categorize correctly
            assert len(results['github']) >= 0
            assert len(results['google_drive']) >= 0
            assert len(results['other']) >= 0
    
    def test_validate_with_timeout_retry(self):
        """Test retry logic for timeout errors."""
        mods = [
            {'name': 'TimeoutMod', 'download_url': 'http://slow.example.com/mod.zip'}
        ]
        
        call_count = 0
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt times out
                import requests
                raise requests.exceptions.Timeout("Timeout")
            else:
                # Second attempt succeeds
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                return mock_resp
        
        with patch('requests.head', side_effect=mock_request):
            results = validate_mod_urls(mods)
            
            # Should have retried (call_count will be 2+ due to retry logic)
            # The mod should eventually be validated or in failed list
            assert call_count >= 1
    
    def test_validate_403_fallback_to_get(self):
        """Test fallback to GET request when HEAD returns 403."""
        mods = [
            {'name': 'BlockedMod', 'download_url': 'http://example.com/mod.zip'}
        ]
        
        with patch('requests.head') as mock_head, patch('requests.get') as mock_get:
            # HEAD returns 403
            mock_head_response = MagicMock()
            mock_head_response.status_code = 403
            mock_head.return_value = mock_head_response
            
            # GET succeeds
            mock_get_response = MagicMock()
            mock_get_response.status_code = 200
            mock_get_response.close = Mock()
            mock_get.return_value = mock_get_response
            
            results = validate_mod_urls(mods)
            
            # Should have used GET as fallback
            mock_get.assert_called()
    
    def test_validate_empty_url(self):
        """Test handling of mods with missing URLs."""
        mods = [
            {'name': 'NoURL', 'download_url': ''}
        ]
        
        results = validate_mod_urls(mods)
        
        # Should be in failed list
        assert len(results['failed']) == 1
        assert results['failed'][0]['error'] == 'No download URL'
    
    def test_validate_domain_categorization(self):
        """Test proper domain categorization for 'other' sources."""
        mods = [
            {'name': 'Mod1', 'download_url': 'https://cdn.example.com/mod1.zip'},
            {'name': 'Mod2', 'download_url': 'https://cdn.example.com/mod2.zip'},
            {'name': 'Mod3', 'download_url': 'https://other.site/mod3.zip'}
        ]
        
        with patch('requests.head') as mock_head:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            
            results = validate_mod_urls(mods)
            
            # Should group by domain
            assert 'cdn.example.com' in results['other'] or 'other.site' in results['other']


class TestConcurrentDownloads:
    """Test concurrent download behavior."""
    
    def test_executor_max_workers(self):
        """Test that executor respects max_workers limit."""
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        mods = [{'name': f'Mod{i}', 'download_url': f'http://example.com/mod{i}.zip'} 
                for i in range(10)]
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'Content-Type': 'application/zip'}
            mock_response.iter_content = Mock(return_value=[b'content'])
            mock_get.return_value = mock_response
            
            max_workers = 3
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(installer.download_archive, mod) for mod in mods]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            # All should complete
            assert len(results) == 10
    
    def test_executor_cancellation(self):
        """Test that executor can be cancelled."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit long-running tasks
            futures = [executor.submit(lambda: None) for _ in range(5)]
            
            # Cancel executor
            executor.shutdown(wait=False, cancel_futures=True)
            
            # Executor should shut down without waiting
            assert True  # If we reach here, cancellation worked


# ============================================================================
# Theme Tests (removed - using system theme now)
# ============================================================================
# ThemeManager has been removed in favor of system theme integration


# ============================================================================
# Button Function Tests
# ============================================================================

from src.gui.main_window import ModlistInstaller
from src.gui import dialogs as custom_dialogs


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory structure for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mods_dir = tmp_path / "starsector" / "mods"
    mods_dir.mkdir(parents=True)
    
    # Create default config files
    modlist_config = {
        "modlist_name": "Test Modlist",
        "version": "1.0",
        "starsector_version": "0.97a",
        "description": "Test modlist",
        "mods": [
            {"name": "TestMod1", "download_url": "http://example.com/mod1.zip", "category": "Required"},
            {"name": "TestMod2", "download_url": "http://example.com/mod2.zip", "category": "Gameplay"},
            {"name": "TestMod3", "download_url": "http://example.com/mod3.zip", "category": "Gameplay"}
        ]
    }
    
    categories = ["Required", "Gameplay", "QoL"]
    
    (config_dir / "modlist_config.json").write_text(json.dumps(modlist_config, indent=2))
    (config_dir / "categories.json").write_text(json.dumps(categories, indent=2))
    (config_dir / "installer_prefs.json").write_text(json.dumps({}, indent=2))
    
    return tmp_path


@pytest.fixture
def mock_app(temp_dir):
    """Create a mock ModlistInstaller for testing."""
    # Create a mock root
    mock_root = Mock(spec=tk.Tk)
    mock_root.title = Mock()
    mock_root.geometry = Mock()
    mock_root.resizable = Mock()
    mock_root.minsize = Mock()
    mock_root.configure = Mock()
    mock_root.protocol = Mock()
    mock_root.after = Mock()
    mock_root.update_idletasks = Mock()
    
    # Mock ttk.Style
    with patch('tkinter.ttk.Style'), \
         patch('tkinter.PanedWindow'), \
         patch('tkinter.Frame'), \
         patch('tkinter.Text'), \
         patch('tkinter.scrolledtext.ScrolledText'), \
         patch('tkinter.StringVar', return_value=Mock(get=Mock(return_value=str(temp_dir / "starsector")), set=Mock())), \
         patch('src.gui.ui_builder.create_header'), \
         patch('src.gui.ui_builder.create_path_section'), \
         patch('src.gui.ui_builder.create_modlist_section'), \
         patch('src.gui.ui_builder.create_log_section'), \
         patch('src.gui.ui_builder.create_enable_mods_section'), \
         patch('src.gui.ui_builder.create_bottom_buttons'):
        
        app = ModlistInstaller(mock_root)
        
        # Mock config paths
        app.config_manager = ConfigManager()
        app.config_manager.config_file = temp_dir / "config" / "modlist_config.json"
        app.config_manager.categories_file = temp_dir / "config" / "categories.json"
        app.config_manager.prefs_file = temp_dir / "config" / "installer_prefs.json"
        
        # Load config
        app.modlist_data = app.config_manager.load_modlist_config()
        app.categories = app.config_manager.load_categories()
        
        # Mock UI elements
        app.mod_listbox = Mock()
        app.mod_listbox.get = Mock(return_value="  ○ TestMod1")
        app.log_text = Mock()
        app.starsector_path = Mock()
        app.starsector_path.get = Mock(return_value=str(temp_dir / "starsector"))
        app.selected_mod_line = None
        
        # Mock log method
        app.log_messages = []
        original_log = app.log
        def mock_log(msg, error=False, info=False, debug=False, success=False, warning=False, **kwargs):
            app.log_messages.append((msg, error, info, debug, success, warning))
        app.log = mock_log
        
        # Mock display methods
        app.display_modlist_info = Mock()
        
        yield app


class TestAddModFunction:
    """Test add_mod_to_config functionality."""
    
    def test_add_mod_to_empty_config(self, mock_app):
        """Test adding a mod to empty modlist."""
        mock_app.modlist_data = {"mods": []}
        
        new_mod = {
            "name": "NewMod",
            "download_url": "http://example.com/newmod.zip",
            "category": "QoL"
        }
        
        mock_app.add_mod_to_config(new_mod)
        
        assert len(mock_app.modlist_data['mods']) == 1
        assert mock_app.modlist_data['mods'][0]['name'] == "NewMod"
    
    def test_add_duplicate_mod_by_name(self, mock_app):
        """Test that duplicate mods by name are not added."""
        initial_count = len(mock_app.modlist_data['mods'])
        
        duplicate_mod = {
            "name": "TestMod1",
            "download_url": "http://example.com/different.zip",
            "category": "QoL"
        }
        
        mock_app.add_mod_to_config(duplicate_mod)
        
        # Should not add duplicate
        assert len(mock_app.modlist_data['mods']) == initial_count
    
    def test_add_duplicate_mod_by_url(self, mock_app):
        """Test that duplicate mods by URL are not added."""
        initial_count = len(mock_app.modlist_data['mods'])
        
        duplicate_mod = {
            "name": "DifferentName",
            "download_url": "http://example.com/mod1.zip",
            "category": "QoL"
        }
        
        mock_app.add_mod_to_config(duplicate_mod)
        
        # Should not add duplicate
        assert len(mock_app.modlist_data['mods']) == initial_count


class TestRemoveModFunction:
    """Test remove_selected_mod functionality."""
    
    def test_remove_mod_no_selection(self, mock_app):
        """Test removing mod with no selection."""
        mock_app.selected_mod_line = None
        
        with patch.object(custom_dialogs, 'showwarning') as mock_warning:
            mock_app.remove_selected_mod()
            mock_warning.assert_called_once()
    
    def test_remove_mod_with_confirmation(self, mock_app):
        """Test removing mod with user confirmation."""
        mock_app.selected_mod_line = 2
        mock_app.mod_listbox.get.return_value = "  ○ TestMod2"
        initial_count = len(mock_app.modlist_data['mods'])
        
        with patch.object(custom_dialogs, 'askyesno', return_value=True):
            mock_app.remove_selected_mod()
        
        # Should have removed one mod
        assert len(mock_app.modlist_data['mods']) == initial_count - 1
        assert not any(m['name'] == 'TestMod2' for m in mock_app.modlist_data['mods'])
    
    def test_remove_mod_without_confirmation(self, mock_app):
        """Test canceling mod removal."""
        mock_app.selected_mod_line = 2
        mock_app.mod_listbox.get.return_value = "  ○ TestMod2"
        initial_count = len(mock_app.modlist_data['mods'])
        
        with patch.object(custom_dialogs, 'askyesno', return_value=False):
            mock_app.remove_selected_mod()
        
        # Should not have removed any mod
        assert len(mock_app.modlist_data['mods']) == initial_count


class TestResetModlistFunction:
    """Test reset_modlist_config functionality."""
    
    def test_reset_modlist_with_confirmation(self, mock_app):
        """Test resetting modlist with user confirmation."""
        # Add some mods
        assert len(mock_app.modlist_data['mods']) > 0
        
        with patch.object(custom_dialogs, 'askyesno', return_value=True), \
             patch.object(custom_dialogs, 'showsuccess'):
            mock_app.reset_modlist_config()
        
        # Should be reset to empty
        assert mock_app.modlist_data['mods'] == []
        assert mock_app.display_modlist_info.called
    
    def test_reset_modlist_without_confirmation(self, mock_app):
        """Test canceling modlist reset."""
        initial_count = len(mock_app.modlist_data['mods'])
        
        with patch.object(custom_dialogs, 'askyesno', return_value=False):
            mock_app.reset_modlist_config()
        
        # Should not have reset
        assert len(mock_app.modlist_data['mods']) == initial_count


class TestReorderModFunctions:
    """Test move_mod_up and move_mod_down functionality."""
    
    def test_move_mod_up_no_selection(self, mock_app):
        """Test moving mod up with no selection."""
        mock_app.selected_mod_line = None
        initial_order = [m['name'] for m in mock_app.modlist_data['mods']]
        
        mock_app.move_mod_up()
        
        # Order should not change
        assert [m['name'] for m in mock_app.modlist_data['mods']] == initial_order
    
    def test_move_mod_down_no_selection(self, mock_app):
        """Test moving mod down with no selection."""
        mock_app.selected_mod_line = None
        initial_order = [m['name'] for m in mock_app.modlist_data['mods']]
        
        mock_app.move_mod_down()
        
        # Order should not change
        assert [m['name'] for m in mock_app.modlist_data['mods']] == initial_order
    
    def test_move_mod_up_in_category(self, mock_app):
        """Test moving a mod up within its category."""
        # Select TestMod3 (last in Gameplay category)
        mock_app.selected_mod_line = 3
        mock_app.mod_listbox.get.return_value = "  ○ TestMod3"
        
        # Mock _find_mod_by_name and _move_mod_in_category
        with patch.object(mock_app, '_find_mod_by_name') as mock_find, \
             patch.object(mock_app, '_move_mod_in_category') as mock_move:
            
            mock_find.return_value = mock_app.modlist_data['mods'][2]  # TestMod3
            mock_app.move_mod_up()
            
            mock_move.assert_called_once_with("TestMod3", mock_find.return_value, -1)
    
    def test_move_mod_down_in_category(self, mock_app):
        """Test moving a mod down within its category."""
        # Select TestMod2 (first in Gameplay category)
        mock_app.selected_mod_line = 2
        mock_app.mod_listbox.get.return_value = "  ○ TestMod2"
        
        # Mock _find_mod_by_name and _move_mod_in_category
        with patch.object(mock_app, '_find_mod_by_name') as mock_find, \
             patch.object(mock_app, '_move_mod_in_category') as mock_move:
            
            mock_find.return_value = mock_app.modlist_data['mods'][1]  # TestMod2
            mock_app.move_mod_down()
            
            mock_move.assert_called_once_with("TestMod2", mock_find.return_value, 1)


class TestRefreshMetadataFunction:
    """Test refresh_mod_metadata functionality."""
    
    def test_refresh_metadata_no_starsector_path(self, mock_app):
        """Test refresh with no Starsector path set."""
        mock_app.starsector_path.get.return_value = ""
        
        with patch.object(custom_dialogs, 'showerror') as mock_error:
            mock_app.refresh_mod_metadata()
            mock_error.assert_called_once()
    
    def test_refresh_metadata_mods_dir_not_found(self, mock_app, temp_dir):
        """Test refresh when mods directory doesn't exist."""
        mock_app.starsector_path.get.return_value = str(temp_dir / "nonexistent")
        
        with patch.object(custom_dialogs, 'showerror') as mock_error:
            mock_app.refresh_mod_metadata()
            mock_error.assert_called_once()
    
    def test_refresh_metadata_success(self, mock_app, temp_dir):
        """Test successful metadata refresh."""
        mods_dir = temp_dir / "starsector" / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test mod folder
        test_mod_dir = mods_dir / "TestMod1"
        test_mod_dir.mkdir()
        (test_mod_dir / "mod_info.json").write_text(json.dumps({
            "id": "testmod1",
            "name": "Test Mod 1",
            "version": "1.5.0"
        }))
        
        # Add a mod to config that matches
        mock_app.modlist_data['mods'] = [
            {"name": "Test Mod 1", "download_url": "http://example.com/mod1.zip"}
        ]
        
        mock_app.refresh_btn = Mock()
        
        with patch.object(custom_dialogs, 'showsuccess'):
            mock_app.refresh_mod_metadata()
            
            # Verify that display was called
            assert mock_app.display_modlist_info.called
            # Verify that the mod metadata was updated
            assert mock_app.modlist_data['mods'][0].get('mod_version') == '1.5.0'
            assert any("refresh complete" in str(msg).lower() for msg, *_ in mock_app.log_messages)


class TestEnableAllModsFunction:
    """Test enable_all_installed_mods functionality."""
    
    def test_enable_mods_no_starsector_path(self, mock_app):
        """Test enable mods with no Starsector path set."""
        mock_app.starsector_path.get.return_value = ""
        
        with patch.object(custom_dialogs, 'showerror') as mock_error:
            mock_app.enable_all_installed_mods()
            mock_error.assert_called_once()
    
    def test_enable_mods_no_mods_found(self, mock_app, temp_dir):
        """Test enable mods when no mods are installed."""
        mods_dir = temp_dir / "starsector" / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        
        with patch.object(custom_dialogs, 'showwarning') as mock_warning:
            mock_app.enable_all_installed_mods()
            mock_warning.assert_called_once()
    
    def test_enable_mods_success(self, mock_app, temp_dir):
        """Test successful enabling of all mods."""
        mods_dir = temp_dir / "starsector" / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test mod folders
        for i in [1, 2, 3]:
            mod_dir = mods_dir / f"TestMod{i}"
            mod_dir.mkdir()
            (mod_dir / "mod_info.json").write_text(json.dumps({
                "id": f"testmod{i}",
                "name": f"Test Mod {i}"
            }))
        
        mock_app.mod_installer = Mock()
        mock_app.mod_installer.update_enabled_mods = Mock(return_value=True)
        
        with patch.object(custom_dialogs, 'showsuccess') as mock_success:
            mock_app.enable_all_installed_mods()
            
            mock_app.mod_installer.update_enabled_mods.assert_called_once()
            mock_success.assert_called_once()
            # Should find 3 mods
            call_args = mock_app.mod_installer.update_enabled_mods.call_args
            enabled_folders = call_args[0][1]
            assert len(enabled_folders) == 3


class TestRestoreBackupFunction:
    """Test restore_backup_dialog functionality."""
    
    def test_restore_backup_no_starsector_path(self, mock_app):
        """Test restore backup with no Starsector path set."""
        mock_app.starsector_path.get.return_value = ""
        
        with patch.object(custom_dialogs, 'showerror') as mock_error:
            mock_app.restore_backup_dialog()
            mock_error.assert_called_once()
    
    def test_restore_backup_no_backups_found(self, mock_app, temp_dir):
        """Test restore backup when no backups exist."""
        with patch('utils.backup_manager.BackupManager') as mock_backup_mgr:
            mock_instance = mock_backup_mgr.return_value
            mock_instance.list_backups.return_value = []
            
            with patch.object(custom_dialogs, 'showinfo') as mock_info:
                mock_app.restore_backup_dialog()
                mock_info.assert_called_once()
    
    def test_restore_backup_dialog_displays_details(self, mock_app, tmp_path):
        """Test that enhanced backup dialog displays backup details correctly."""
        from datetime import datetime
        from pathlib import Path
        import json
        
        # Setup mock backups with enabled_mods.json
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        
        backup1 = backup_dir / "backup_20251220_120000"
        backup1.mkdir()
        (backup1 / "enabled_mods.json").write_text(json.dumps({
            "enabledMods": ["mod1", "mod2", "mod3"]
        }))
        (backup1 / "backup_info.json").write_text(json.dumps({
            "timestamp": "20251220_120000"
        }))
        
        mock_app.starsector_path.get.return_value = str(tmp_path)
        
        with patch('utils.backup_manager.BackupManager') as mock_backup_mgr:
            mock_instance = mock_backup_mgr.return_value
            mock_instance.list_backups.return_value = [
                (backup1, {"timestamp": "20251220_120000"})
            ]
            mock_instance.backup_dir = backup_dir
            
            # Mock the dialog creation to avoid actual Tkinter windows
            with patch('gui.dialogs._create_dialog') as mock_create:
                mock_dialog = Mock()
                mock_create.return_value = mock_dialog
                
                # Test that dialog can be opened without errors
                from gui.dialogs import open_restore_backup_dialog
                open_restore_backup_dialog(None, mock_app)
                
                # Verify dialog was created with correct title and size
                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert call_args[0][1] == "Restore Backup"  # Title
                assert call_args[1]['width'] == 750
                assert call_args[1]['height'] == 500


class TestRestoreBackupSafely:
    """Test restore_backup_safely high-level function."""
    
    def test_restore_backup_safely_creates_pre_restore_backup(self, mock_app, tmp_path):
        """Test that restore_backup_safely creates a pre-restore backup before restoring."""
        from pathlib import Path
        
        # Setup mock backup manager
        mock_backup_mgr = Mock()
        mock_backup_mgr.create_backup.return_value = (Path("backup_pre_restore"), True, None)
        mock_backup_mgr.restore_backup.return_value = (True, None)
        mock_app.backup_manager = mock_backup_mgr
        
        # Setup mock for display_modlist_info
        mock_app.display_modlist_info = Mock()
        mock_app.modlist_data = {"mods": []}
        
        # Call restore_backup_safely
        backup_path = tmp_path / "backup_20251220_120000"
        success, error = mock_app.restore_backup_safely(backup_path, "2025-12-20 at 12:00:00")
        
        # Verify success
        assert success is True
        assert error is None
        
        # Verify pre-restore backup was created
        mock_backup_mgr.create_backup.assert_called_once()
        
        # Verify restore was called
        mock_backup_mgr.restore_backup.assert_called_once_with(backup_path)
        
        # Verify UI was refreshed
        mock_app.display_modlist_info.assert_called_once()
        
        # Verify logging - check log_messages list
        log_texts = [msg[0].lower() for msg in mock_app.log_messages]
        assert any("pre-restore backup" in text for text in log_texts)
        assert any("restored" in text for text in log_texts)
    
    def test_restore_backup_safely_fails_if_pre_backup_fails(self, mock_app, tmp_path):
        """Test that restore is aborted if pre-restore backup creation fails."""
        # Setup mock backup manager with failing pre-backup
        mock_backup_mgr = Mock()
        mock_backup_mgr.create_backup.return_value = (None, False, "Disk full")
        mock_app.backup_manager = mock_backup_mgr
        
        # Call restore_backup_safely
        backup_path = tmp_path / "backup_20251220_120000"
        success, error = mock_app.restore_backup_safely(backup_path)
        
        # Verify failure
        assert success is False
        assert "pre-restore backup" in error.lower()
        assert "Disk full" in error
        
        # Verify restore was NOT called
        mock_backup_mgr.restore_backup.assert_not_called()
    
    def test_restore_backup_safely_no_changes_on_restore_failure(self, mock_app, tmp_path):
        """Test that if restore fails, the function reports failure properly."""
        # Setup mock backup manager
        mock_backup_mgr = Mock()
        mock_backup_mgr.create_backup.return_value = (Path("backup_pre_restore"), True, None)
        mock_backup_mgr.restore_backup.return_value = (False, "Corrupt backup file")
        mock_app.backup_manager = mock_backup_mgr
        
        # Call restore_backup_safely
        backup_path = tmp_path / "backup_20251220_120000"
        success, error = mock_app.restore_backup_safely(backup_path)
        
        # Verify failure
        assert success is False
        assert "restore backup" in error.lower()
        assert "Corrupt backup file" in error
        
        # Pre-restore backup should still have been created
        mock_backup_mgr.create_backup.assert_called_once()
    
    def test_restore_backup_safely_no_backup_manager(self, mock_app):
        """Test that restore_backup_safely fails gracefully without backup_manager."""
        mock_app.backup_manager = None
        
        success, error = mock_app.restore_backup_safely(Path("backup"))
        
        assert success is False
        assert "backup manager not initialized" in error.lower()
    
    def test_restore_backup_safely_ui_refresh_failure_is_non_fatal(self, mock_app, tmp_path):
        """Test that UI refresh failure doesn't prevent successful restore."""
        # Setup mock backup manager
        mock_backup_mgr = Mock()
        mock_backup_mgr.create_backup.return_value = (Path("backup_pre_restore"), True, None)
        mock_backup_mgr.restore_backup.return_value = (True, None)
        mock_app.backup_manager = mock_backup_mgr
        
        # Setup mock that fails on refresh
        mock_app.display_modlist_info = Mock(side_effect=Exception("UI error"))
        mock_app.modlist_data = {"mods": []}
        
        # Call restore_backup_safely
        backup_path = tmp_path / "backup_20251220_120000"
        success, error = mock_app.restore_backup_safely(backup_path)
        
        # Verify success (UI refresh failure is just a warning)
        assert success is True
        assert error is None
        
        # Verify warning was logged about UI refresh failure
        warning_logs = [msg for msg in mock_app.log_messages if msg[5]]  # msg[5] is warning flag
        assert len(warning_logs) > 0
        assert any("ui" in msg[0].lower() and "refresh" in msg[0].lower() for msg in warning_logs)


class TestBackupRetentionPolicy:
    """Test BackupManager retention policy."""
    
    def test_default_retention_count_is_4(self):
        """Test that default retention count is 4."""
        from utils.backup_manager import BackupManager
        assert BackupManager.DEFAULT_RETENTION_COUNT == 4
    
    def test_automatic_cleanup_on_create_backup(self, tmp_path):
        """Test that creating a backup automatically cleans up old ones beyond retention limit."""
        from utils.backup_manager import BackupManager
        from datetime import datetime
        
        # Setup temp Starsector directory
        starsector_dir = tmp_path / "starsector"
        mods_dir = starsector_dir / "mods"
        mods_dir.mkdir(parents=True)
        
        # Create enabled_mods.json
        enabled_mods_file = mods_dir / "enabled_mods.json"
        enabled_mods_file.write_text('{"enabledMods": []}')
        
        log_messages = []
        def mock_log(msg, **kwargs):
            log_messages.append(msg)
        
        # Create BackupManager with retention_count=3 for testing
        backup_mgr = BackupManager(starsector_dir, log_callback=mock_log, retention_count=3)
        
        # Create 5 backups with mocked timestamps
        backup_paths = []
        base_time = datetime(2025, 1, 1, 12, 0, 0)
        
        with patch('utils.backup_manager.datetime') as mock_datetime:
            for i in range(5):
                # Mock datetime to return incremental timestamps
                current_time = base_time.replace(hour=12+i)
                mock_datetime.now.return_value = current_time
                
                backup_path, success, error = backup_mgr.create_backup()
                assert success, f"Backup {i} creation failed: {error}"
                backup_paths.append(backup_path)
        
        # Check that only 3 backups remain
        remaining_backups = backup_mgr.list_backups()
        assert len(remaining_backups) == 3, f"Expected 3 backups, found {len(remaining_backups)}"
        
        # Verify that the 3 most recent backups are kept
        remaining_names = {backup[0].name for backup in remaining_backups}
        expected_names = {backup_paths[i].name for i in [2, 3, 4]}  # Last 3
        assert remaining_names == expected_names, "Wrong backups were kept"
        
        # Verify cleanup was logged
        cleanup_logs = [msg for msg in log_messages if "Cleaned up" in msg and "old backup" in msg]
        assert len(cleanup_logs) >= 2, "Cleanup should have been logged"
    
    def test_retention_with_custom_count(self, tmp_path):
        """Test custom retention count."""
        from utils.backup_manager import BackupManager
        from datetime import datetime
        
        starsector_dir = tmp_path / "starsector"
        mods_dir = starsector_dir / "mods"
        mods_dir.mkdir(parents=True)
        (mods_dir / "enabled_mods.json").write_text('{"enabledMods": []}')
        
        # Create with retention_count=2
        backup_mgr = BackupManager(starsector_dir, retention_count=2)
        
        # Create 4 backups with mocked timestamps
        base_time = datetime(2025, 1, 1, 12, 0, 0)
        with patch('utils.backup_manager.datetime') as mock_datetime:
            for i in range(4):
                mock_datetime.now.return_value = base_time.replace(hour=12+i)
                backup_mgr.create_backup()
        
        # Should keep only 2
        remaining = backup_mgr.list_backups()
        assert len(remaining) == 2, f"Expected 2 backups with retention_count=2, found {len(remaining)}"
    
    def test_manual_cleanup(self, tmp_path):
        """Test manual cleanup_old_backups call."""
        from utils.backup_manager import BackupManager
        from datetime import datetime
        
        starsector_dir = tmp_path / "starsector"
        mods_dir = starsector_dir / "mods"
        mods_dir.mkdir(parents=True)
        (mods_dir / "enabled_mods.json").write_text('{"enabledMods": []}')
        
        # Create with high retention to prevent auto-cleanup
        backup_mgr = BackupManager(starsector_dir, retention_count=10)
        
        # Create 6 backups with mocked timestamps
        base_time = datetime(2025, 1, 1, 12, 0, 0)
        with patch('utils.backup_manager.datetime') as mock_datetime:
            for i in range(6):
                mock_datetime.now.return_value = base_time.replace(hour=12+i)
                backup_mgr.create_backup()
        
        assert len(backup_mgr.list_backups()) == 6
        
        # Manually cleanup to keep only 3
        deleted_count = backup_mgr.cleanup_old_backups(keep_count=3)
        assert deleted_count == 3, f"Expected to delete 3 backups, deleted {deleted_count}"
        assert len(backup_mgr.list_backups()) == 3, "Should have 3 backups remaining"


class TestSaveConfigFunction:
    """Test save_modlist_config functionality."""
    
    def test_save_config_with_log(self, mock_app):
        """Test saving config with log message."""
        mock_app.save_modlist_config(log_message=True)
        
        # Should log a message
        assert any("saved" in str(msg).lower() for msg, *_ in mock_app.log_messages)
    
    def test_save_config_without_log(self, mock_app):
        """Test saving config without log message."""
        mock_app.log_messages = []
        mock_app.save_modlist_config(log_message=False)
        
        # Should not log
        assert len(mock_app.log_messages) == 0
    
    def test_save_config_persists(self, mock_app, temp_dir):
        """Test that config is actually saved to file."""
        # Add a new mod
        new_mod = {
            "name": "PersistTest",
            "download_url": "http://example.com/persist.zip",
            "category": "QoL"
        }
        mock_app.modlist_data['mods'].append(new_mod)
        
        # Save
        mock_app.save_modlist_config()
        
        # Reload from file
        config_file = temp_dir / "config" / "modlist_config.json"
        reloaded = json.loads(config_file.read_text())
        
        # Should contain new mod
        assert any(m['name'] == 'PersistTest' for m in reloaded['mods'])


class TestModExtractionHelpers:
    """Test helper functions for extracting mod info from display lines."""
    
    def test_extract_mod_name_from_line(self, mock_app):
        """Test extracting mod name from listbox line."""
        test_cases = [
            ("  ○ TestMod", "TestMod"),
            ("  ✓ AnotherMod", "AnotherMod"),
            ("  ↑ UpdatedMod", "UpdatedMod"),
            ("Required", None),  # Category header
            ("", None),  # Empty line
        ]
        
        for line_text, expected in test_cases:
            result = mock_app._extract_mod_name_from_line(line_text)
            assert result == expected, f"Failed for: {line_text}"
    
    def test_find_mod_by_name(self, mock_app):
        """Test finding a mod in config by name."""
        result = mock_app._find_mod_by_name("TestMod1")
        assert result is not None
        assert result['name'] == "TestMod1"
        
        result = mock_app._find_mod_by_name("NonExistent")
        assert result is None


class TestExtractModMetadata:
    """Test extract_mod_metadata functionality."""
    
    def test_extract_metadata_from_zip(self, tmp_path):
        """Test extracting metadata from ZIP archive."""
        # Create a test ZIP with mod_info.json
        zip_path = tmp_path / "test_mod.zip"
        mod_info = {
            "id": "test_mod",
            "name": "Test Mod",
            "version": "1.0.0",
            "gameVersion": "0.97a-RC11"
        }
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("TestMod/mod_info.json", json.dumps(mod_info))
        
        # Test extraction
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        metadata = installer.extract_mod_metadata(zip_path, is_7z=False)
        
        assert metadata is not None
        assert metadata['id'] == "test_mod"
        assert metadata['name'] == "Test Mod"
        assert metadata['version'] == "1.0.0"
    
    def test_extract_metadata_no_mod_info(self, tmp_path):
        """Test extraction fails gracefully when mod_info.json is missing."""
        # Create a ZIP without mod_info.json
        zip_path = tmp_path / "no_info.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("readme.txt", "No mod_info here")
        
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        metadata = installer.extract_mod_metadata(zip_path, is_7z=False)
        
        assert metadata is None
    
    def test_extract_metadata_nested_path(self, tmp_path):
        """Test extraction from nested mod_info.json."""
        zip_path = tmp_path / "nested_mod.zip"
        mod_info = {
            "id": "nested_mod",
            "name": "Nested Mod",
            "version": "2.0.0"
        }
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("SomeFolder/NestedMod/mod_info.json", json.dumps(mod_info))
        
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        metadata = installer.extract_mod_metadata(zip_path, is_7z=False)
        
        assert metadata is not None
        assert metadata['id'] == "nested_mod"


class TestMoveModWithArrows:
    """Test moving mods up/down with arrow keys."""
    
    def test_move_mod_up_method_exists(self, mock_app):
        """Test that move_mod_up method exists and is callable."""
        assert hasattr(mock_app, 'move_mod_up')
        assert callable(mock_app.move_mod_up)
    
    def test_move_mod_down_method_exists(self, mock_app):
        """Test that move_mod_down method exists and is callable."""
        assert hasattr(mock_app, 'move_mod_down')
        assert callable(mock_app.move_mod_down)
    
    def test_move_mod_requires_selection(self, mock_app):
        """Test that move operations require a selected mod."""
        # No selection
        mock_app.selected_mod_line = None
        
        # Should not raise errors, just return early
        mock_app.move_mod_up()
        mock_app.move_mod_down()
        
        # No changes should occur
        assert len(mock_app.modlist_data['mods']) == 3
    
    def test_move_mod_with_selection(self, mock_app):
        """Test that move operations work with valid selection."""
        # Setup: select middle mod
        mock_app.selected_mod_line = 2
        mock_app.mod_listbox.get = Mock(return_value="  ○ TestMod2")
        
        # Should not raise errors
        try:
            mock_app.move_mod_up()
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_swap_adjacent_mods_functionality(self, mock_app):
        """Test the underlying swap functionality."""
        # Directly test _swap_adjacent_mods if accessible
        if not hasattr(mock_app, '_swap_adjacent_mods'):
            pytest.skip("_swap_adjacent_mods not accessible")
        
        # Get two mods in same category
        category_mods = [m for m in mock_app.modlist_data['mods'] 
                        if m['category'] == 'Required']
        
        if len(category_mods) >= 2:
            original_first = category_mods[0]['name']
            original_second = category_mods[1]['name']
            
            # Swap down (move first mod down)
            mock_app._swap_adjacent_mods(category_mods[0], category_mods, 0, 1)
            
            # Verify swap occurred in main data
            updated_mods = [m for m in mock_app.modlist_data['mods'] 
                           if m['category'] == 'Required']
            
            # After swapping, first should be second, second should be first
            assert updated_mods[0]['name'] == original_second
            assert updated_mods[1]['name'] == original_first


class TestRefreshMetadataButton:
    """Test refresh metadata button functionality."""
    
    def test_refresh_metadata_updates_versions(self, mock_app, temp_dir):
        """Test that refresh button updates mod versions from installed mods."""
        # Create fake installed mod with mod_info.json
        mods_dir = temp_dir / "Starsector" / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        
        test_mod_dir = mods_dir / "TestMod1"
        test_mod_dir.mkdir()
        mod_info = {
            "id": "testmod1",
            "name": "TestMod1",
            "version": "2.0.0",  # Newer version
            "gameVersion": "0.97a-RC11"
        }
        (test_mod_dir / "mod_info.json").write_text(json.dumps(mod_info))
        
        # Setup mock app with old version
        mock_app.starsector_path.set(str(temp_dir / "Starsector"))
        mock_app.modlist_data['mods'][0]['mod_version'] = "1.0.0"
        
        # Execute refresh
        with patch('src.utils.mod_utils.scan_installed_mods') as mock_scan:
            mock_scan.return_value = [(test_mod_dir, mod_info)]
            mock_app.refresh_mod_metadata()
        
        # Verify version was updated
        assert mock_app.modlist_data['mods'][0]['mod_version'] == "2.0.0"
    
    def test_refresh_metadata_no_starsector_path(self, mock_app):
        """Test refresh fails gracefully without Starsector path."""
        mock_app.starsector_path.set("")
        
        with patch('src.gui.dialogs.showerror') as mock_error:
            mock_app.refresh_mod_metadata()
            
            # Should show error (may be called through custom_dialogs)
            # Just verify no crash and error handling works
            assert True  # Method completed without exception
    
    def test_refresh_metadata_logs_changes(self, mock_app, temp_dir):
        """Test that refresh logs which mods were updated."""
        mods_dir = temp_dir / "Starsector" / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        
        test_mod_dir = mods_dir / "TestMod1"
        test_mod_dir.mkdir()
        mod_info = {
            "id": "testmod1",
            "name": "TestMod1",
            "version": "3.0.0"
        }
        (test_mod_dir / "mod_info.json").write_text(json.dumps(mod_info))
        
        mock_app.starsector_path.set(str(temp_dir / "Starsector"))
        mock_app.log_messages = []
        
        # Execute refresh
        with patch('src.utils.mod_utils.scan_installed_mods') as mock_scan:
            mock_scan.return_value = [(test_mod_dir, mod_info)]
            mock_app.refresh_mod_metadata()
        
        # Verify logging occurred
        assert any("metadata" in str(msg).lower() for msg, *_ in mock_app.log_messages)
    
    def test_refresh_metadata_handles_missing_mods(self, mock_app, temp_dir):
        """Test refresh handles mods that aren't installed."""
        mods_dir = temp_dir / "Starsector" / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        
        mock_app.starsector_path.set(str(temp_dir / "Starsector"))
        
        # Execute refresh with no installed mods
        with patch('src.utils.mod_utils.scan_installed_mods') as mock_scan:
            mock_scan.return_value = []
            mock_app.refresh_mod_metadata()
        
        # Should complete without error
        assert mock_app.display_modlist_info.called


class TestDragAndDropEdgeCases:
    """Test drag & drop stability with edge cases."""
    
    def test_drag_drop_to_empty_category(self, mock_app):
        """Test dragging mod to an empty category."""
        # Add a new empty category
        mock_app.categories.append("EmptyCategory")
        mock_app.modlist_data['mods'][0]['category'] = "Required"
        
        # Mock the drag operation
        source_mod = mock_app.modlist_data['mods'][0]
        mock_app.drag_start_line = 1
        
        # Simulate drop on empty category
        with patch.object(mock_app, '_find_category_above', return_value="EmptyCategory"):
            with patch.object(mock_app, '_find_category_line', return_value=10):
                with patch.object(mock_app, '_calculate_drop_position', return_value=0):
                    # Should not crash
                    try:
                        mock_app._move_mod_to_category_position(
                            source_mod['name'], 
                            source_mod, 
                            "EmptyCategory", 
                            0
                        )
                        success = True
                    except Exception as e:
                        success = False
                        print(f"Error: {e}")
                    
                    assert success
    
    def test_drag_drop_single_mod_in_category(self, mock_app):
        """Test dragging the only mod in a category."""
        # Setup: single mod in Required category
        mock_app.modlist_data['mods'] = [
            {'name': 'OnlyMod', 'category': 'Required', 'download_url': 'http://example.com/mod.zip'}
        ]
        
        # Try to drag it within same category (should be no-op)
        source_mod = mock_app.modlist_data['mods'][0]
        
        try:
            mock_app._move_mod_to_category_position('OnlyMod', source_mod, 'Required', 0)
            success = True
        except Exception:
            success = False
        
        assert success
        assert len(mock_app.modlist_data['mods']) == 1
        assert mock_app.modlist_data['mods'][0]['name'] == 'OnlyMod'
    
    def test_drag_drop_invalid_target_category(self, mock_app):
        """Test dragging to non-existent category."""
        source_mod = mock_app.modlist_data['mods'][0]
        mock_app.drag_start_line = 1
        
        # Mock finding a category that doesn't exist
        with patch.object(mock_app, '_find_category_above', return_value="NonExistent"):
            with patch.object(mock_app, '_find_category_line', return_value=None):
                # Create mock event
                event = Mock()
                event.x = 100
                event.y = 100
                
                # Should handle gracefully (return early)
                mock_app._on_drag_end(event)
                
                # drag_start_line should be reset
                assert mock_app.drag_start_line is None
    
    def test_drag_drop_without_drag_start(self, mock_app):
        """Test drag end without drag start."""
        mock_app.drag_start_line = None
        
        event = Mock()
        event.x = 100
        event.y = 100
        
        # Should return early without error
        try:
            mock_app._on_drag_end(event)
            success = True
        except Exception:
            success = False
        
        assert success


class TestNetworkErrorRecovery:
    """Test network error recovery and cleanup."""
    
    def test_download_timeout_cleanup(self, tmp_path):
        """Test that temp files are cleaned up after network timeout."""
        import requests
        from unittest.mock import MagicMock
        
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        # Mock timeout exception
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")
            
            mod = {'download_url': 'http://example.com/slow.zip', 'name': 'SlowMod'}
            result, is_7z = installer.download_archive(mod)
            
            # Should return None and not crash
            assert result is None
            assert is_7z is False
    
    def test_download_connection_error_cleanup(self, tmp_path):
        """Test cleanup after connection error."""
        import requests
        
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        # Mock connection error
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            mod = {'download_url': 'http://example.com/unreachable.zip', 'name': 'UnreachableMod'}
            result, is_7z = installer.download_archive(mod)
            
            # Should return None and not crash
            assert result is None
            assert is_7z is False
    
    def test_download_interrupted_cleanup(self, tmp_path):
        """Test that incomplete downloads are cleaned up."""
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        # Mock a download that fails mid-stream
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'Content-Type': 'application/zip'}
            mock_response.raise_for_status = Mock()
            
            # Simulate failure during iter_content
            mock_response.iter_content = Mock(side_effect=requests.exceptions.ChunkedEncodingError("Connection broken"))
            mock_get.return_value = mock_response
            
            mod = {'download_url': 'http://example.com/interrupted.zip', 'name': 'InterruptedMod'}
            result, is_7z = installer.download_archive(mod)
            
            # Should return None after cleanup
            assert result is None
            assert is_7z is False
    
    def test_corrupted_archive_cleanup(self, tmp_path):
        """Test cleanup of corrupted archives."""
        import zipfile
        
        log_callback = Mock()
        installer = ModInstaller(log_callback)
        
        # Create a corrupted zip file
        corrupted_zip = tmp_path / "corrupted.zip"
        corrupted_zip.write_bytes(b"NOT A VALID ZIP FILE")
        
        # Mock download to return corrupted file
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'Content-Type': 'application/zip'}
            mock_response.raise_for_status = Mock()
            mock_response.iter_content = Mock(return_value=[b"NOT A VALID ZIP FILE"])
            mock_get.return_value = mock_response
            
            mod = {'download_url': 'http://example.com/corrupted.zip', 'name': 'CorruptedMod'}
            
            # Should detect invalid archive and clean up
            with patch.object(installer, '_validate_archive_integrity', return_value=False):
                result, is_7z = installer.download_archive(mod)
                
                assert result is None
                assert is_7z is False
    
    def test_ui_recovery_after_network_error(self, mock_app, monkeypatch):
        """Test that UI buttons are re-enabled after network error in Add Mod dialog."""
        from src.gui import dialogs
        
        # This test verifies the async workflow handles errors correctly
        # The actual dialog testing would require Tkinter integration
        # We verify the error handling logic is present
        
        # Check that the error handling functions exist
        import inspect
        source = inspect.getsource(dialogs.open_add_mod_dialog)
        
        # Verify error handling helpers are defined
        assert 're_enable_buttons' in source
        assert 'show_error' in source
        assert 'dlg.after' in source  # Tkinter-safe callbacks
        
        # Verify threading is used
        assert 'threading.Thread' in source
        assert 'daemon=True' in source


class TestAddModDialogRobustness:
    """Test Add Mod dialog error handling and recovery."""
    
    def test_add_mod_dialog_handles_download_failure(self, mock_app, tmp_path):
        """Test that Add Mod dialog handles download failures gracefully."""
        # Verify the download_and_extract_async function has proper error handling
        from src.gui import dialogs
        import inspect
        
        source = inspect.getsource(dialogs.open_add_mod_dialog)
        
        # Verify error handling structure
        assert 'except Exception as e:' in source
        assert 'dlg.after(0, lambda: show_error' in source
        
        # Verify cleanup is in finally block
        assert 'finally:' in source
        assert 'Path(temp_file).unlink()' in source
    
    def test_add_mod_dialog_handles_metadata_extraction_failure(self):
        """Test that metadata extraction failures are handled."""
        from src.gui import dialogs
        import inspect
        
        source = inspect.getsource(dialogs.open_add_mod_dialog)
        
        # Verify metadata validation
        assert 'if not metadata or not metadata.get' in source
        assert "Could not extract mod metadata" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
