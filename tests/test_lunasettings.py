#!/usr/bin/env python3
"""Test script for LunaSettings functionality."""

from pathlib import Path
from src.core.config_manager import ConfigManager

def test_list_presets():
    """Test listing presets with LunaSettings detection."""
    print("=" * 60)
    print("Test 1: Listing presets")
    print("=" * 60)
    
    config_mgr = ConfigManager()
    presets = config_mgr.list_presets()
    
    for name, path, has_lunalib in presets:
        luna_indicator = "📘" if has_lunalib else "  "
        print(f"{luna_indicator} {name}")
        if has_lunalib:
            lunasettings_path = path / "LunaSettings"
            config_files = list(lunasettings_path.glob("*.json.data"))
            print(f"   → {len(config_files)} LunaLib config files")
    
    print()

def test_load_preset():
    """Test loading a preset with LunaSettings."""
    print("=" * 60)
    print("Test 2: Loading Example_Preset")
    print("=" * 60)
    
    config_mgr = ConfigManager()
    modlist_data, lunalib_data, error = config_mgr.load_preset("Example_Preset")
    
    if error:
        print(f"❌ Error: {error}")
        return
    
    print(f"✓ Loaded modlist with {len(modlist_data.get('mods', []))} mods")
    
    if lunalib_data:
        print(f"✓ Loaded LunaSettings with {len(lunalib_data)} mod configs:")
        for mod_id, settings in lunalib_data.items():
            print(f"   - {mod_id}: {len(settings)} settings")
    else:
        print("  No LunaSettings in preset")
    
    print()

def test_export_with_lunalib():
    """Test exporting with LunaLib settings from game."""
    print("=" * 60)
    print("Test 3: Export with LunaLib")
    print("=" * 60)
    
    starsector_path = "/Applications/Starsector.app"
    lunasettings_path = Path(starsector_path) / "saves" / "common" / "LunaSettings"
    
    if lunasettings_path.is_dir():
        config_files = list(lunasettings_path.glob("*.json.data"))
        print(f"✓ Found LunaSettings folder with {len(config_files)} configs:")
        for config_file in config_files[:5]:  # Show first 5
            print(f"   - {config_file.name}")
        if len(config_files) > 5:
            print(f"   ... and {len(config_files) - 5} more")
    else:
        print(f"❌ LunaSettings folder not found at: {lunasettings_path}")
    
    print()

def test_patch_lunalib():
    """Test patching LunaLib (dry run - shows what would happen)."""
    print("=" * 60)
    print("Test 4: Patch LunaLib (simulation)")
    print("=" * 60)
    
    config_mgr = ConfigManager()
    preset_path = config_mgr.presets_dir / "Example_Preset"
    preset_lunasettings = preset_path / "LunaSettings"
    
    if preset_lunasettings.is_dir():
        config_files = list(preset_lunasettings.glob("*.json.data"))
        print(f"✓ Preset has {len(config_files)} LunaLib configs to patch:")
        for config_file in config_files:
            print(f"   - {config_file.name}")
        print("\nWould copy these files to:")
        print("   /Applications/Starsector.app/saves/common/LunaSettings/")
    else:
        print("❌ No LunaSettings folder in preset")
    
    print()

if __name__ == "__main__":
    print("\n🧪 Testing LunaSettings Functionality\n")
    
    test_list_presets()
    test_load_preset()
    test_export_with_lunalib()
    test_patch_lunalib()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)
