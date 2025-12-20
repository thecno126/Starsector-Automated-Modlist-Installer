"""Helper functions for Tkinter listbox text extraction and navigation."""

from utils.mod_utils import normalize_mod_name
from utils.symbols import LogSymbols


def extract_mod_name_from_line(line_text):
    """Extract mod name from a listbox line.
    
    Args:
        line_text: Text from listbox line
        
    Returns:
        str: Mod name or None if not a mod line
    """
    line = line_text.strip()
    # Check if it's a mod line (starts with icon)
    if not (line.startswith(LogSymbols.INSTALLED) or line.startswith(LogSymbols.NOT_INSTALLED) or line.startswith(LogSymbols.UPDATED)):
        return None
    # Remove icon prefix and extract name (before version if present)
    name_part = line_text.replace(f"  {LogSymbols.INSTALLED} ", "").replace(f"  {LogSymbols.NOT_INSTALLED} ", "").replace(f"  {LogSymbols.UPDATED} ", "")
    return name_part.split(" v")[0].strip()


def find_mod_by_name(mod_name, mods_list):
    """Find a mod dict by name using exact match or normalized matching.
    
    Args:
        mod_name: Name to search for
        mods_list: List of mod dictionaries
        
    Returns:
        dict: Mod dictionary or None if not found
    """
    # First try exact match (fastest)
    exact_match = next((m for m in mods_list if m.get('name') == mod_name), None)
    if exact_match:
        return exact_match
    
    # Try normalized matching as fallback
    normalized_search = normalize_mod_name(mod_name)
    for mod in mods_list:
        mod_config_name = mod.get('name', '')
        if normalize_mod_name(mod_config_name) == normalized_search:
            return mod
    
    return None


def is_mod_line(line_text):
    """Check if a listbox line represents a mod (vs category).
    
    Args:
        line_text: Text from listbox line
        
    Returns:
        bool: True if line is a mod entry
    """
    line = line_text.strip()
    return line.startswith(LogSymbols.INSTALLED) or line.startswith(LogSymbols.NOT_INSTALLED) or line.startswith(LogSymbols.UPDATED)
