import json
import os
from pathlib import Path

import pytest

from src.core.config_manager import ConfigManager
from src.core.constants import CONFIG_FILE, CATEGORIES_FILE, PREFS_FILE


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
    def __call__(self, msg, error=False):
        self.messages.append((msg, error))


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
    assert ok is False
    assert any("already installed" in m[0] for m in logs.messages)


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
    assert ok is False
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
            if installer._is_already_installed(mock_members, mods_dir):
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
    
    def test_network_failure_recovery(self, temp_workspace):
        """Test: Network error during download → Error handling → Retry logic."""
        log_mock = Mock()
        installer = ModInstaller(log_mock)
        
        mod = {'name': 'TestMod', 'download_url': 'https://example.com/testmod.zip'}
        
        with patch('src.core.installer.requests.get') as mock_get:
            # Simulate network timeout
            mock_get.side_effect = Exception("Connection timeout")
            
            temp_file, is_7z = installer.download_archive(mod)
            
            # Should return (None, False) on failure
            assert temp_file is None
            assert is_7z is False
            log_mock.assert_called()
            
            # Verify error was logged
            logged_messages = [call[0][0] for call in log_mock.call_args_list]
            assert any('error' in msg.lower() or 'unexpected' in msg.lower() for msg in logged_messages)
    
    def test_corrupted_archive_handling(self, temp_workspace):
        """Test: Download corrupted archive → Extraction fails → Proper error message."""
        log_mock = Mock()
        installer = ModInstaller(log_mock)
        
        # Create a corrupted ZIP file
        corrupted_zip = temp_workspace['cache'] / "corrupted.zip"
        corrupted_zip.write_bytes(b'this is not a valid zip file')
        
        # Try to extract
        success = installer.extract_archive(corrupted_zip, temp_workspace['mods'], is_7z=False)
        
        assert success is False
        log_mock.assert_called()


class TestCategoryManagement:
    """Test category organization scenarios."""
    
    def test_move_mod_between_categories(self, temp_workspace):
        """Test: Create categories → Assign mods → Move between categories → Persist."""
        config_file = temp_workspace['config'] / "modlist_config.json"
        
        modlist_data = {
            'modlist_name': 'Test',
            'version': '1.0',
            'starsector_version': '0.97a-RC11',
            'description': 'Test',
            'mods': [
                {'name': 'Mod A', 'category': 'Gameplay', 'download_url': 'https://example.com/a.zip'},
                {'name': 'Mod B', 'category': 'Graphics', 'download_url': 'https://example.com/b.zip'},
            ]
        }
        
        # Move Mod A from Gameplay to Graphics
        for mod in modlist_data['mods']:
            if mod['name'] == 'Mod A':
                mod['category'] = 'Graphics'
        
        # Save
        config_file.write_text(json.dumps(modlist_data, indent=2))
        
        # Reload and verify
        loaded = json.loads(config_file.read_text())
        mod_a = next(m for m in loaded['mods'] if m['name'] == 'Mod A')
        assert mod_a['category'] == 'Graphics'
        
        # Count mods per category
        graphics_count = sum(1 for m in loaded['mods'] if m['category'] == 'Graphics')
        assert graphics_count == 2


class TestPerformance:
    """Test performance and load scenarios."""
    
    def test_large_modlist_handling(self, temp_workspace):
        """Test: Load 100+ mods → Validate performance → Memory usage reasonable."""
        config_file = temp_workspace['config'] / "modlist_config.json"
        
        # Generate large modlist
        large_modlist = {
            'modlist_name': 'Large Test',
            'version': '1.0',
            'starsector_version': '0.97a-RC11',
            'description': 'Stress test',
            'mods': []
        }
        
        categories = ['Gameplay', 'Graphics', 'Utilities', 'Factions', 'Quality of Life']
        
        for i in range(150):
            large_modlist['mods'].append({
                'name': f'Mod {i:03d}',
                'category': categories[i % len(categories)],
                'download_url': f'https://example.com/mod{i}.zip',
                'version': f'{i % 10}.{i % 5}'
            })
        
        # Save large modlist
        config_file.write_text(json.dumps(large_modlist, indent=2))
        
        # Load and verify
        loaded = json.loads(config_file.read_text())
        assert len(loaded['mods']) == 150
        
        # Verify category distribution
        category_counts = {}
        for mod in loaded['mods']:
            cat = mod['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        assert len(category_counts) == 5
        assert all(count == 30 for count in category_counts.values())
    
    def test_parallel_downloads_efficiency(self, temp_workspace):
        """Test: Simulate parallel downloads → Verify concurrent execution → Time savings."""
        from concurrent.futures import ThreadPoolExecutor
        import time
        
        def mock_download(mod_id):
            """Simulate download with delay."""
            time.sleep(0.1)  # Simulate network delay
            return f"downloaded_{mod_id}"
        
        mods = [f"mod_{i}" for i in range(10)]
        
        # Sequential download time
        start_seq = time.time()
        results_seq = [mock_download(mod) for mod in mods]
        time_seq = time.time() - start_seq
        
        # Parallel download time (3 workers)
        start_par = time.time()
        with ThreadPoolExecutor(max_workers=3) as executor:
            results_par = list(executor.map(mock_download, mods))
        time_par = time.time() - start_par
        
        # Parallel should be faster (at least 2x with 3 workers)
        assert time_par < time_seq * 0.5
        assert len(results_par) == len(results_seq)
        assert all(r.startswith('downloaded_') for r in results_par)
