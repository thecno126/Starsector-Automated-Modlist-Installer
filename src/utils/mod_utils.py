"""
Utility functions for mod operations.
Centralized functions to avoid code duplication.
"""

import re
from pathlib import Path


def normalize_mod_name(name):
    """
    Normalize a mod name for comparison by removing spaces, hyphens, and underscores.
    Case-insensitive.
    
    Args:
        name: Mod name to normalize
        
    Returns:
        str: Normalized name (lowercase, no spaces/hyphens/underscores)
        
    Examples:
        >>> normalize_mod_name("Graphics Lib")
        'graphicslib'
        >>> normalize_mod_name("My-Awesome_Mod")
        'myawesomemod'
    """
    if not name:
        return ''
    return re.sub(r'[\s\-_]', '', str(name).lower())


def extract_mod_id_from_text(content):
    """
    Extract mod ID directly from raw mod_info.json text.
    Searches for "id" field and extracts the value.
    
    Args:
        content: Raw text content of mod_info.json
        
    Returns:
        str: Mod ID or None if not found
        
    Examples:
        >>> extract_mod_id_from_text('"id": "graphicslib"')
        'graphicslib'
        >>> extract_mod_id_from_text('id: "my_mod_123"')
        'my_mod_123'
    """
    # Look for "id" followed by value
    # Handles: "id": "value", id: "value", id:'value'
    match = re.search(r'["\']?id["\']?\s*:\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    return match.group(1) if match else None


def extract_mod_name_from_text(content):
    """
    Extract mod name from mod_info.json text.
    
    Args:
        content: Raw text content of mod_info.json
        
    Returns:
        str: Mod name or None if not found
    """
    match = re.search(r'["\']?name["\']?\s*:\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    return match.group(1) if match else None


def extract_mod_version_from_text(content):
    """
    Extract mod version string directly from raw mod_info.json text.
    Searches for "version" field (not "gameVersion") and extracts the value.
    
    This bypasses JSON parsing entirely, making it robust against malformed JSON.
    
    Args:
        content: Raw text content of mod_info.json
        
    Returns:
        str: Version string (e.g., "1.5.0", "0.12.1b", "2.0a") or 'unknown'
        
    Examples:
        >>> extract_mod_version_from_text('"version": "1.5.0"')
        '1.5.0'
        >>> extract_mod_version_from_text('version: {major: 0, minor: 12, patch: "1b"}')
        '0.12.1b'
    """
    # First try: object format like version: {major: 0, minor: 12, patch: "1b"}
    # This must come BEFORE the simple string match to avoid capturing gameVersion
    version_block = re.search(r'"?version"?\s*:\s*\{([^}]+)\}', content, re.IGNORECASE)
    if version_block:
        block = version_block.group(1)
        major = re.search(r'"?major"?\s*:\s*["\']?([0-9]+)', block, re.IGNORECASE)
        minor = re.search(r'"?minor"?\s*:\s*["\']?([0-9]+)', block, re.IGNORECASE)
        patch = re.search(r'"?patch"?\s*:\s*["\']?([0-9a-zA-Z]+)', block, re.IGNORECASE)
        
        if major:
            parts = [major.group(1)]
            if minor:
                parts.append(minor.group(1))
            if patch:
                parts.append(patch.group(1))
            return '.'.join(parts)
    
    # Second try: simple version string like "version": "1.5.0" or version: "1.5.0"
    # Use negative lookbehind to exclude "gameVersion"
    match = re.search(r'(?<!game)"?version"?\s*:\s*["\']?([0-9]+[0-9a-zA-Z._-]*)', content, re.IGNORECASE)
    if match:
        version = match.group(1).rstrip('",}] ')
        return version
    
    return 'unknown'


def extract_game_version_from_text(content):
    """
    Extract gameVersion (compatible Starsector version) from mod_info.json text.
    
    Args:
        content: Raw text content of mod_info.json
        
    Returns:
        str: Game version (e.g., "0.98a-RC8") or None if not found
        
    Examples:
        >>> extract_game_version_from_text('"gameVersion": "0.98a-RC8"')
        '0.98a-RC8'
    """
    match = re.search(r'"?gameVersion"?\s*:\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    return match.group(1) if match else None


def read_mod_info_json(mod_folder):
    """
    Read and return content of mod_info.json from a mod folder.
    
    Args:
        mod_folder: Path to mod folder
        
    Returns:
        str: Content of mod_info.json or None if not found/readable
    """
    mod_info_file = Path(mod_folder) / "mod_info.json"
    if not mod_info_file.exists():
        return None
    
    try:
        with open(mod_info_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None


def extract_all_metadata_from_text(content):
    """
    Extract all metadata from mod_info.json content in one pass.
    
    Args:
        content: Raw text content of mod_info.json
        
    Returns:
        dict: {
            'id': str or None,
            'name': str or None,
            'version': str or 'unknown',
            'gameVersion': str or None
        }
    """
    return {
        'id': extract_mod_id_from_text(content),
        'name': extract_mod_name_from_text(content),
        'version': extract_mod_version_from_text(content),
        'gameVersion': extract_game_version_from_text(content)
    }


def compare_versions(version1, version2):
    """
    Compare two version strings using semantic versioning rules.
    
    Args:
        version1: First version string (e.g., "1.2.3" or "2.0a")
        version2: Second version string
        
    Returns:
        int: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
        
    Examples:
        >>> compare_versions("1.2.3", "1.2.2")
        1
        >>> compare_versions("2.0a", "2.0b")
        -1
        >>> compare_versions("1.0.0", "1.0.0")
        0
    """
    if version1 == version2:
        return 0
    
    def parse_version(v):
        """Parse version string into list of comparable parts."""
        v = str(v).lower().replace('v', '').replace('version', '').strip()
        parts = re.findall(r'\d+|[a-z]+', v)
        return [int(p) if p.isdigit() else ord(p[0]) - ord('a') + 1 for p in parts]
    
    v1_parts = parse_version(version1)
    v2_parts = parse_version(version2)
    
    # Compare parts using zip_longest
    from itertools import zip_longest
    for p1, p2 in zip_longest(v1_parts, v2_parts, fillvalue=0):
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    
    return 0


def is_mod_name_match(search_name, folder_name, installed_name=None):
    """
    Check if a mod name matches using normalized comparison.
    
    Args:
        search_name: Name to search for
        folder_name: Mod folder name
        installed_name: Optional installed mod name from mod_info.json
        
    Returns:
        bool: True if names match
    """
    normalized_search = normalize_mod_name(search_name)
    folder_normalized = normalize_mod_name(folder_name)
    
    if normalized_search == folder_normalized:
        return True
    
    if installed_name:
        installed_normalized = normalize_mod_name(installed_name)
        if normalized_search == installed_normalized:
            return True
    
    # Partial match (one contains the other)
    if normalized_search in folder_normalized or folder_normalized in normalized_search:
        return True
    
    return False


def scan_installed_mods(mods_dir, filter_func=None):
    """
    Scan installed mods directory and extract metadata from all mod_info.json files.
    
    This centralizes the common pattern of iterating through mods_dir, reading mod_info.json,
    and extracting metadata. Reduces code duplication across installer.py and main_window.py.
    
    Args:
        mods_dir: Path to Starsector mods directory
        filter_func: Optional function(folder, content) -> bool to filter mods.
                    Return True to include mod, False to skip.
                    
    Yields:
        tuple: (folder_path, mod_metadata_dict) for each valid mod
               where mod_metadata_dict contains:
               {
                   'folder_name': str,
                   'mod_id': str or None,
                   'name': str or None,
                   'version': str or None,
                   'game_version': str or None,
                   'content': str (raw mod_info.json content)
               }
               
    Example:
        >>> for folder, metadata in scan_installed_mods(mods_dir):
        ...     print(f"Found {metadata['name']} v{metadata['version']}")
        
        >>> # With filter
        >>> def filter_by_id(folder, content):
        ...     return 'graphicslib' in content
        >>> for folder, metadata in scan_installed_mods(mods_dir, filter_by_id):
        ...     print(metadata['mod_id'])
    """
    if not mods_dir or not mods_dir.exists():
        return
    
    for folder in mods_dir.iterdir():
        # Skip hidden folders and non-directories
        if not folder.is_dir() or folder.name.startswith('.'):
            continue
        
        mod_info_file = folder / "mod_info.json"
        if not mod_info_file.exists():
            continue
        
        try:
            with open(mod_info_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Apply filter if provided
            if filter_func and not filter_func(folder, content):
                continue
            
            # Extract all metadata at once
            metadata = extract_all_metadata_from_text(content)
            
            # Add additional fields
            metadata['folder_name'] = folder.name
            metadata['content'] = content
            
            yield folder, metadata
            
        except (IOError, UnicodeDecodeError, PermissionError):
            # Skip files we can't read
            continue


def extract_dependencies_from_text(content):
    """
    Extract mod dependencies from mod_info.json content.
    
    Args:
        content: Raw text content of mod_info.json
        
    Returns:
        list: List of dependency mod IDs, or empty list if none found
        
    Examples:
        >>> extract_dependencies_from_text('"dependencies": ["lw_lazylib", "MagicLib"]')
        ['lw_lazylib', 'MagicLib']
    """
    dependencies = []
    
    # Look for "dependencies" array
    # Pattern matches: "dependencies": ["id1", "id2", ...] or "dependencies":["id1","id2"]
    pattern = r'"dependencies"\s*:\s*\[(.*?)\]'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    
    if match:
        deps_str = match.group(1)
        # Extract all quoted strings
        dep_pattern = r'["\']([^"\']+)["\']'
        dependencies = re.findall(dep_pattern, deps_str)
    
    return dependencies


def check_missing_dependencies(mod_list, installed_mod_ids):
    """
    Check which mods have missing dependencies.
    
    Args:
        mod_list: List of mod dictionaries with 'mod_id' and optionally 'dependencies'
        installed_mod_ids: Set or list of installed mod IDs
        
    Returns:
        dict: {mod_id: [list of missing dependency IDs]}
        
    Example:
        >>> mods = [{'mod_id': 'modA', 'dependencies': ['libB', 'libC']}]
        >>> installed = {'modA', 'libB'}
        >>> check_missing_dependencies(mods, installed)
        {'modA': ['libC']}
    """
    installed_set = set(installed_mod_ids)
    missing_deps = {}
    
    for mod in mod_list:
        mod_id = mod.get('mod_id')
        dependencies = mod.get('dependencies', [])
        
        if not mod_id or not dependencies:
            continue
        
        # Find missing dependencies
        missing = [dep for dep in dependencies if dep not in installed_set]
        
        if missing:
            missing_deps[mod_id] = missing
    
    return missing_deps

