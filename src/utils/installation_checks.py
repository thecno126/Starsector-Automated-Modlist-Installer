"""Pre-installation validation checks."""

from pathlib import Path
import socket
import shutil

from utils.error_messages import get_user_friendly_error


def check_disk_space(install_dir, min_gb=5):
    """Check if there's enough disk space.
    
    Args:
        install_dir: Directory to check space for
        min_gb: Minimum required space in GB
        
    Returns:
        tuple: (has_space: bool, message: str)
    """
    try:
        stat = shutil.disk_usage(install_dir)
        free_gb = stat.free / (1024 ** 3)
        
        if free_gb < min_gb:
            return False, f"Only {free_gb:.1f} GB available (minimum {min_gb} GB recommended)"
        
        return True, f"{free_gb:.1f} GB available"
    except Exception as e:
        return False, f"Could not check disk space: {e}"


def check_write_permissions(mods_dir):
    """Check if we have write permissions to mods directory.
    
    Args:
        mods_dir: Path to mods directory
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        test_file = mods_dir / ".write_test"
        mods_dir.mkdir(exist_ok=True)
        test_file.write_text("test")
        test_file.unlink()
        return True, None
    except (PermissionError, OSError) as e:
        friendly_msg = get_user_friendly_error('permission_denied')
        return False, f"{friendly_msg}\n\nTechnical: {e}"


def check_internet_connection(timeout=3):
    """Quick internet connection check.
    
    Args:
        timeout: Connection timeout in seconds
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        socket.create_connection(("www.google.com", 80), timeout=timeout)
        return True, None
    except (socket.error, socket.timeout):
        return False, "Could not verify internet connection"


def run_all_pre_installation_checks(starsector_dir, modlist_data, check_deps_func, 
                                     log_callback=None, prompt_callback=None,
                                     min_disk_gb=5):
    """Run comprehensive pre-installation checks.
    
    Args:
        starsector_dir: Path to Starsector installation
        modlist_data: Modlist data for dependency checking
        check_deps_func: Function to check dependencies (takes mods_dir, returns dict)
        log_callback: Optional callback for logging (msg, level='info')
        prompt_callback: Optional callback for yes/no prompts (title, message) → bool
        min_disk_gb: Minimum disk space in GB
        
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    mods_dir = Path(starsector_dir) / "mods"
    
    def log(msg, level='info'):
        if log_callback:
            log_callback(msg, level)
    
    def prompt(title, message):
        if prompt_callback:
            return prompt_callback(title, message)
        return True  # Default to continue if no callback
    
    # Check disk space
    has_space, space_msg = check_disk_space(starsector_dir, min_disk_gb)
    if not has_space:
        log(space_msg, 'warning')
        if not prompt("Low Disk Space", f"{space_msg}\n\nContinue anyway?"):
            return False, "Installation cancelled due to low disk space"
    
    # Check write permissions
    perm_success, perm_error = check_write_permissions(mods_dir)
    if not perm_success:
        return False, perm_error
    log("✓ Write permissions verified", 'debug')
    
    # Check internet connection
    conn_success, conn_error = check_internet_connection()
    if not conn_success:
        log("⚠ Internet connection may be unavailable", 'warning')
        if not prompt("Connection Warning", f"{conn_error}\n\nContinue anyway?"):
            return False, "Installation cancelled due to connection issues"
    log("✓ Internet connection verified", 'debug')
    
    # Check dependencies
    dependency_issues = check_deps_func(mods_dir)
    if dependency_issues:
        issues_text = "\n".join([f"  • {mod_name}: missing {', '.join(deps)}" 
                                 for mod_name, deps in dependency_issues.items()])
        log(f"⚠ Dependency issues found:\n{issues_text}", 'warning')
        
        message = f"Some mods have missing dependencies:\n\n{issues_text}\n\nThese dependencies will be installed if they're in the modlist.\n\nContinue?"
        if not prompt("Missing Dependencies", message):
            return False, "Installation cancelled due to missing dependencies"
    else:
        log("✓ No dependency issues found", 'debug')
    
    return True, None
