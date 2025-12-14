"""
User-friendly error messages for common installation issues.
Translates technical errors into actionable advice.
"""


def get_user_friendly_error(error_type, error_details=""):
    """
    Convert technical error into user-friendly message with actionable steps.
    
    Args:
        error_type: Type of error (e.g., 'network', 'disk_space', 'permission')
        error_details: Optional technical details
        
    Returns:
        str: User-friendly error message with suggested actions
    """
    messages = {
        'network_timeout': (
            "❌ Connection timeout\n\n"
            "The download took too long to respond.\n\n"
            "Try:\n"
            "• Check your internet connection\n"
            "• Try again later (server might be busy)\n"
            "• Check if your firewall is blocking the connection"
        ),
        
        'network_404': (
            "❌ Mod not found (404)\n\n"
            "The download link is broken or the mod was removed.\n\n"
            "Try:\n"
            "• Check if the mod is still available online\n"
            "• Update the modlist to get a new link\n"
            "• Contact the modlist creator"
        ),
        
        'disk_space': (
            "❌ Not enough disk space\n\n"
            "Your drive doesn't have enough free space for the mods.\n\n"
            "Try:\n"
            "• Free up at least 5 GB of space\n"
            "• Install to a different drive\n"
            "• Remove some old mods first"
        ),
        
        'permission_denied': (
            "❌ Permission denied\n\n"
            "The installer can't write to the Starsector folder.\n\n"
            "Try:\n"
            "• Run the installer as Administrator (Windows)\n"
            "• Check folder permissions\n"
            "• Close Starsector if it's running"
        ),
        
        'corrupted_archive': (
            "❌ Corrupted download\n\n"
            "The downloaded file is damaged or incomplete.\n\n"
            "Try:\n"
            "• Download again (automatic retry will happen)\n"
            "• Check your internet connection stability\n"
            "• Report the issue if it persists"
        ),
        
        'invalid_path': (
            "❌ Invalid Starsector folder\n\n"
            "The selected folder doesn't look like Starsector.\n\n"
            "Try:\n"
            "• Select the folder containing 'starsector-core'\n"
            "• Make sure Starsector is properly installed\n"
            "• Re-install Starsector if needed"
        ),
        
        'gdrive_limit': (
            "⚠️ Google Drive download quota exceeded\n\n"
            "This mod can't be downloaded right now due to Google Drive limits.\n\n"
            "Try:\n"
            "• Wait a few hours and try again\n"
            "• Contact the mod author for an alternative link\n"
            "• Skip this mod for now"
        ),
        
        'dependency_missing': (
            "⚠️ Missing dependencies\n\n"
            "Some mods require other mods to be installed first.\n\n"
            "The installer will try to install them in the correct order.\n"
            "Check the log for details."
        ),
        
        'version_mismatch': (
            "⚠️ Version incompatibility\n\n"
            "This mod might not work with your Starsector version.\n\n"
            "The mod will be installed but might cause issues.\n"
            "Check the mod page for compatible versions."
        ),
    }
    
    default_message = (
        f"❌ An error occurred\n\n"
        f"Technical details: {error_details}\n\n"
        f"Try:\n"
        f"• Check the log for more information\n"
        f"• Restart the installer\n"
        f"• Report this on GitHub if it persists"
    )
    
    return messages.get(error_type, default_message)


def suggest_fix_for_error(exception):
    """
    Analyze an exception and suggest the most likely fix.
    
    Args:
        exception: Python exception object
        
    Returns:
        str: Error type key for get_user_friendly_error()
    """
    import requests
    
    # Network errors
    if isinstance(exception, requests.exceptions.Timeout):
        return 'network_timeout'
    elif isinstance(exception, requests.exceptions.ConnectionError):
        return 'network_timeout'
    elif isinstance(exception, requests.exceptions.HTTPError):
        if exception.response.status_code == 404:
            return 'network_404'
        elif exception.response.status_code == 403:
            return 'gdrive_limit'
    
    # File system errors
    elif isinstance(exception, PermissionError):
        return 'permission_denied'
    elif isinstance(exception, OSError):
        if 'No space left' in str(exception):
            return 'disk_space'
        return 'permission_denied'
    
    # Archive errors
    elif 'zipfile' in str(type(exception)).lower() or 'Bad7zFile' in str(type(exception)):
        return 'corrupted_archive'
    
    return None  # Use default message
