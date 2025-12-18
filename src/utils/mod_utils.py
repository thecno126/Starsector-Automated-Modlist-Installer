"""Mod metadata extraction, version comparison, and dependency resolution.

Public API:
    High-level: extract_all_metadata_from_text(), read_mod_info_from_archive()
    Low-level parsing: extract_mod_id_from_text(), extract_mod_version_from_text(), 
                       extract_game_version_from_text(), extract_dependencies_from_text()
    Version handling: compare_versions(), extract_major_version()
    Mod scanning: scan_installed_mods(), is_mod_name_match(), is_mod_up_to_date()
    Dependencies: resolve_mod_dependencies(), check_missing_dependencies()
"""
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import zipfile
import tempfile


def normalize_mod_name(name: str) -> str:
    """Normalize mod name for comparison (remove spaces/hyphens/underscores, lowercase)."""
    if not name:
        return ''
    return re.sub(r'[\s\-_]', '', str(name).lower())


def extract_mod_id_from_text(content: str) -> Optional[str]:
    """Extract mod ID. Handles \"id\": \"value\", id: \"value\", id:'value'."""
    match = re.search(r'["\']?id["\']?\s*:\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_mod_name_from_text(content: str) -> Optional[str]:
    match = re.search(r'["\']?name["\']?\s*:\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    return match.group(1) if match else None


def extract_mod_version_from_text(content: str) -> str:
    """Extract version. Handles {major/minor/patch} or \"1.5.0\" formats."""
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
    
    match = re.search(r'(?<!game)"?version"?\s*:\s*["\']?([0-9]+[0-9a-zA-Z._-]*)', content, re.IGNORECASE)
    if match:
        return match.group(1).rstrip('",}] ')
    
    return 'unknown'


def extract_game_version_from_text(content: str) -> Optional[str]:
    match = re.search(r'"?gameVersion"?\s*:\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
    return match.group(1) if match else None


def _read_mod_info_json(mod_folder: Path) -> Optional[str]:
    mod_info_file = Path(mod_folder) / "mod_info.json"
    if not mod_info_file.exists():
        return None
    try:
        with open(mod_info_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None


def extract_all_metadata_from_text(content: str) -> Dict[str, Optional[str]]:
    """Extract id, name, version, gameVersion from mod_info.json text."""
    return {
        'id': extract_mod_id_from_text(content),
        'name': _extract_mod_name_from_text(content),
        'version': extract_mod_version_from_text(content),
        'gameVersion': extract_game_version_from_text(content)
    }


def compare_versions(version1: str, version2: str) -> int:
    """Compare semantic versions. Returns 1 if v1>v2, -1 if v1<v2, 0 if equal."""
    if version1 == version2:
        return 0
    
    def parse_version(v):
        v = str(v).lower().replace('v', '').replace('version', '').strip()
        parts = re.findall(r'\d+|[a-z]+', v)
        return [int(p) if p.isdigit() else ord(p[0]) - ord('a') + 1 for p in parts]
    
    v1_parts = parse_version(version1)
    v2_parts = parse_version(version2)
    
    from itertools import zip_longest
    for p1, p2 in zip_longest(v1_parts, v2_parts, fillvalue=0):
        if p1 > p2:
            return 1
        elif p1 < p2:
            return -1
    return 0


def is_mod_name_match(search_name: str, folder_name: str, installed_name: Optional[str] = None) -> bool:
    """Check if search_name matches folder_name or installed_name (normalized, partial match)."""
    normalized_search = normalize_mod_name(search_name)
    folder_normalized = normalize_mod_name(folder_name)
    
    if normalized_search == folder_normalized:
        return True
    
    if installed_name:
        installed_normalized = normalize_mod_name(installed_name)
        if normalized_search == installed_normalized:
            return True
    
    return normalized_search in folder_normalized or folder_normalized in normalized_search


def scan_installed_mods(mods_dir: Path, filter_func=None):
    """Scan mods directory and yield (folder_path, metadata_dict) for each valid mod.
    
    Args:
        mods_dir: Starsector mods directory
        filter_func: Optional (folder, content) -> bool filter
    
    Yields: (folder, {'folder_name', 'mod_id', 'name', 'version', 'game_version', 'content'})
    """
    if not mods_dir or not mods_dir.exists():
        return
    
    for folder in mods_dir.iterdir():
        if not folder.is_dir() or folder.name.startswith('.'):
            continue
        
        mod_info_file = folder / "mod_info.json"
        if not mod_info_file.exists():
            continue
        
        try:
            with open(mod_info_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if filter_func and not filter_func(folder, content):
                continue
            
            metadata = extract_all_metadata_from_text(content)
            metadata['folder_name'] = folder.name
            metadata['content'] = content
            
            yield folder, metadata
        except (IOError, UnicodeDecodeError, PermissionError):
            continue


def extract_dependencies_from_text(content: str) -> List[str]:
    """Extract dependency mod IDs from mod_info.json."""
    pattern = r'"dependencies"\s*:\s*\[(.*?)\]'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    
    if match:
        deps_str = match.group(1)
        dep_pattern = r'["\']([^"\']+)["\']'
        return re.findall(dep_pattern, deps_str)
    return []


def check_missing_dependencies(mod_list: List[Dict[str, Any]], installed_mod_ids) -> Dict[str, List[str]]:
    """Return {mod_id: [missing_dep_ids]} for mods with unmet dependencies."""
    installed_set = set(installed_mod_ids)
    missing_deps = {}
    
    for mod in mod_list:
        mod_id = mod.get('mod_id')
        dependencies = mod.get('dependencies', [])
        
        if not mod_id or not dependencies:
            continue
        
        missing = [dep for dep in dependencies if dep not in installed_set]
        if missing:
            missing_deps[mod_id] = missing
    
    return missing_deps


def extract_major_version(version_str: Optional[str]) -> Optional[str]:
    """Extract major version: '0.97a' from '0.97a-RC10'."""
    if not version_str:
        return None
    match = re.match(r'([\d.]+[a-z]?)', version_str.split('-')[0])
    return match.group(1) if match else version_str.split('-')[0]


def is_mod_up_to_date(mod_name: str, expected_version: Optional[str], mods_dir: Path) -> Tuple[bool, Optional[str]]:
    """Check installed mod version >= expected. Returns (is_up_to_date, installed_version)."""
    installed_version = None
    
    for folder, metadata in scan_installed_mods(mods_dir):
        if is_mod_name_match(mod_name, folder.name, metadata.get('name', '')):
            installed_version = metadata.get('version', 'unknown')
            break
    
    if not installed_version:
        return False, None
    
    if not expected_version:
        return True, installed_version
    
    if installed_version == 'unknown':
        return False, installed_version
    
    try:
        return compare_versions(installed_version, expected_version) >= 0, installed_version
    except Exception:
        return False, installed_version


def resolve_mod_dependencies(mods: List[Dict[str, Any]], installed_mods_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Topological sort: reorder mods so dependencies install first."""
    mod_by_id = {mod.get('mod_id'): mod for mod in mods if mod.get('mod_id')}
    mod_by_name = {normalize_mod_name(mod.get('name', '')): mod for mod in mods if mod.get('name')}
    
    in_degree = {mod['name']: 0 for mod in mods}
    adj_list = {mod['name']: [] for mod in mods}
    
    for mod in mods:
        for dep in mod.get('dependencies', []):
            dep_mod = mod_by_id.get(dep.get('id'))
            if not dep_mod and dep.get('name'):
                dep_mod = mod_by_name.get(normalize_mod_name(dep.get('name', '')))
            
            if dep_mod and dep_mod['name'] not in installed_mods_dict:
                adj_list[dep_mod['name']].append(mod['name'])
                in_degree[mod['name']] += 1
    
    queue = [mod['name'] for mod in mods if in_degree[mod['name']] == 0]
    sorted_names = []
    
    while queue:
        current = queue.pop(0)
        sorted_names.append(current)
        for neighbor in adj_list[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    if len(sorted_names) != len(mods):
        return mods
    
    name_to_mod = {mod['name']: mod for mod in mods}
    return [name_to_mod[name] for name in sorted_names]


def read_mod_info_from_archive(archive_path: Path, is_7z: bool = False) -> Optional[Dict[str, Any]]:
    """Extract metadata from mod_info.json without full extraction."""
    try:
        if is_7z:
            try:
                import py7zr
            except ImportError:
                return None
            
            with py7zr.SevenZipFile(archive_path, 'r') as archive:
                for member in archive.getnames():
                    if member.endswith('mod_info.json'):
                        with tempfile.TemporaryDirectory() as tmpdir:
                            archive.extract(path=tmpdir, targets=[member])
                            with open(Path(tmpdir) / member, 'r', encoding='utf-8') as f:
                                return extract_all_metadata_from_text(f.read())
        else:
            with zipfile.ZipFile(archive_path, 'r') as archive:
                for member in archive.namelist():
                    if member.endswith('mod_info.json'):
                        with archive.open(member) as f:
                            return extract_all_metadata_from_text(f.read().decode('utf-8'))
    except Exception:
        pass
    return None

