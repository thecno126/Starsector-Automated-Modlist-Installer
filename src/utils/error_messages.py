"""User-friendly error message templates."""

from utils.symbols import LogSymbols


def get_user_friendly_error(error_type, error_details=""):
    """Convert error type to user-friendly message with actionable steps."""
    messages = {
        'network_timeout': (
            f"{LogSymbols.ERROR_BOLD} Connection timeout\n\n"
            "The download took too long to respond.\n\n"
            "Try:\n"
            f"{LogSymbols.BULLET} Check your internet connection\n"
            f"{LogSymbols.BULLET} Try again later (server might be busy)\n"
            f"{LogSymbols.BULLET} Check if your firewall is blocking the connection"
        ),
        
        'network_404': (
            f"{LogSymbols.ERROR_BOLD} Mod not found (404)\n\n"
            "The download link is broken or the mod was removed.\n\n"
            "Try:\n"
            f"{LogSymbols.BULLET} Check if the mod is still available online\n"
            f"{LogSymbols.BULLET} Update the modlist to get a new link\n"
            f"{LogSymbols.BULLET} Contact the modlist creator"
        ),
        
        'disk_space': (
            f"{LogSymbols.ERROR_BOLD} Not enough disk space\n\n"
            "Your drive doesn't have enough free space for the mods.\n\n"
            "Try:\n"
            f"{LogSymbols.BULLET} Free up at least 5 GB of space\n"
            f"{LogSymbols.BULLET} Install to a different drive\n"
            f"{LogSymbols.BULLET} Remove some old mods first"
        ),
        
        'permission_denied': (
            f"{LogSymbols.ERROR_BOLD} Permission denied\n\n"
            "The installer can't write to the Starsector folder.\n\n"
            "Try:\n"
            f"{LogSymbols.BULLET} Run the installer as Administrator (Windows)\n"
            f"{LogSymbols.BULLET} Check folder permissions\n"
            f"{LogSymbols.BULLET} Close Starsector if it's running"
        ),
        
        'corrupted_archive': (
            f"{LogSymbols.ERROR_BOLD} Corrupted download\n\n"
            "The downloaded file is damaged or incomplete.\n\n"
            "Try:\n"
            f"{LogSymbols.BULLET} Download again (automatic retry will happen)\n"
            f"{LogSymbols.BULLET} Check your internet connection stability\n"
            f"{LogSymbols.BULLET} Report the issue if it persists"
        ),
        
        'invalid_path': (
            f"{LogSymbols.ERROR_BOLD} Invalid Starsector folder\n\n"
            "The selected folder doesn't look like Starsector.\n\n"
            "Try:\n"
            f"{LogSymbols.BULLET} Select the folder containing 'starsector-core'\n"
            f"{LogSymbols.BULLET} Make sure Starsector is properly installed\n"
            f"{LogSymbols.BULLET} Re-install Starsector if needed"
        ),
        
        'gdrive_limit': (
            LogSymbols.WARNING + " Google Drive download quota exceeded\n\n"
            "This mod can't be downloaded right now due to Google Drive limits.\n\n"
            "Try:\n"
            f"{LogSymbols.BULLET} Wait a few hours and try again\n"
            f"{LogSymbols.BULLET} Contact the mod author for an alternative link\n"
            f"{LogSymbols.BULLET} Skip this mod for now"
        ),
        
        'dependency_missing': (
            LogSymbols.WARNING + " Missing dependencies\n\n"
            "Some mods require other mods to be installed first.\n\n"
            "The installer will try to install them in the correct order.\n"
            "Check the log for details."
        ),
        
        'version_mismatch': (
            LogSymbols.WARNING + " Version incompatibility\n\n"
            "This mod might not work with your Starsector version.\n\n"
            "The mod will be installed but might cause issues.\n"
            "Check the mod page for compatible versions."
        ),
    }
    
    default_message = (
        f"{LogSymbols.ERROR_BOLD} An error occurred\n\n"
        f"Technical details: {error_details}\n\n"
        f"Try:\n"
        f"{LogSymbols.BULLET} Check the log for more information\n"
        f"{LogSymbols.BULLET} Restart the installer\n"
        f"{LogSymbols.BULLET} Report this on GitHub if it persists"
    )
    
    return messages.get(error_type, default_message)


def suggest_fix_for_error(exception):
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
