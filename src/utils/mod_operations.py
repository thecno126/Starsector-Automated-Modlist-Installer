"""High-level mod operations (refresh metadata, enable mods, etc.)."""

from pathlib import Path
from utils.mod_utils import scan_installed_mods, is_mod_name_match


def refresh_mod_metadata(modlist_data, mods_dir, log_callback=None):
    """Refresh mod metadata from installed mods.
    
    Args:
        modlist_data: Modlist configuration dictionary
        mods_dir: Path to mods directory
        log_callback: Optional callback for logging messages
        
    Returns:
        tuple: (updated_count: int, error_message: str or None)
    """
    def log(msg, **kwargs):
        if log_callback:
            log_callback(msg, **kwargs)
    
    log("Reloading modlist configuration...")
    
    updated_count = 0
    for mod in modlist_data.get('mods', []):
        mod_name = mod.get('name', '')
        if not mod_name:
            continue
        
        for folder, metadata in scan_installed_mods(mods_dir):
            if is_mod_name_match(mod_name, folder.name, metadata.get('name', '')):
                if metadata.get('version') and metadata['version'] != 'unknown':
                    mod['mod_version'] = metadata['version']
                    updated_count += 1
                if metadata.get('gameVersion'):
                    mod['game_version'] = metadata['gameVersion']
                break
    
    return (updated_count, None)


def enable_all_installed_mods(mods_dir, mod_installer, log_callback=None):
    """Enable all installed mods by updating enabled_mods.json.
    
    Args:
        mods_dir: Path to mods directory
        mod_installer: ModInstaller instance
        log_callback: Optional callback for logging messages
        
    Returns:
        tuple: (enabled_count: int, error_message: str or None)
    """
    def log(msg, **kwargs):
        if log_callback:
            log_callback(msg, **kwargs)
    
    log("Enabling all installed mods...")
    
    # Scan all installed mods
    all_installed_folders = []
    for folder, metadata in scan_installed_mods(mods_dir):
        all_installed_folders.append(folder.name)
        log(f"  Found: {folder.name}", debug=True)
    
    if not all_installed_folders:
        return (0, "No mods found in mods directory")
    
    # Update enabled_mods.json with all installed mods
    success = mod_installer.update_enabled_mods(mods_dir, all_installed_folders, merge=False)
    
    if success:
        log(f"✓ Enabled {len(all_installed_folders)} mod(s) in enabled_mods.json")
        return (len(all_installed_folders), None)
    else:
        return (0, "Failed to update enabled_mods.json")
