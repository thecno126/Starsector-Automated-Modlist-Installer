"""
Test suite for button functions in the main window.
Tests all button callbacks including add, remove, edit, import, export, 
refresh, restore, clear, enable mods, and reorder functions.
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import tkinter as tk

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.gui.main_window import ModlistInstaller
from src.core.config_manager import ConfigManager
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
        def mock_log(msg, error=False, info=False, debug=False):
            app.log_messages.append((msg, error, info, debug))
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
        
        mock_app.refresh_btn = Mock()
        
        with patch.object(mock_app, '_update_mod_metadata_from_installed') as mock_update, \
             patch.object(custom_dialogs, 'showsuccess'):
            
            mock_app.refresh_mod_metadata()
            
            mock_update.assert_called_once()
            assert mock_app.display_modlist_info.called
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
    
    @pytest.mark.skip(reason="Complex Tkinter dialog mocking - tested via integration")
    def test_restore_backup_dialog_opens(self, mock_app, temp_dir):
        """Test that restore backup dialog opens with backups."""
        mock_backups = [
            {
                "timestamp": "2025-01-01_12-00-00",
                "path": temp_dir / "backups" / "backup1"
            }
        ]
        
        with patch('utils.backup_manager.BackupManager') as mock_backup_mgr:
            mock_instance = mock_backup_mgr.return_value
            mock_instance.list_backups.return_value = mock_backups
            
            # Mock tk.Toplevel to prevent actual dialog creation
            with patch('tkinter.Toplevel') as mock_toplevel:
                mock_dialog = Mock()
                mock_dialog.title = Mock()
                mock_dialog.geometry = Mock()
                mock_dialog.configure = Mock()
                mock_dialog.transient = Mock()
                mock_dialog.grab_set = Mock()
                mock_toplevel.return_value = mock_dialog
                
                # Call should not raise an error
                mock_app.restore_backup_dialog()
                
                # Dialog should be created
                mock_toplevel.assert_called()


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
