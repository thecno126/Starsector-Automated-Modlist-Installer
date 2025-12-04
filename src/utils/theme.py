"""System theme detection utilities."""
import sys
import subprocess


def detect_system_theme():
    """Detect if system is in dark mode.
    
    Returns:
        str: 'dark' if system is in dark mode, 'light' otherwise
    """
    try:
        if sys.platform == "darwin":  # macOS
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True,
                text=True
            )
            return 'dark' if result.returncode == 0 and 'Dark' in result.stdout else 'light'
        elif sys.platform == "win32":  # Windows
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                    r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                return 'light' if value == 1 else 'dark'
            except:
                return 'light'
        else:  # Linux and others
            return 'light'
    except:
        return 'light'


class ThemeManager:
    """Centralized theme manager to ensure consistency across all UI components."""
    
    def __init__(self):
        """Initialize theme manager with system theme detection."""
        self.current_theme = detect_system_theme()
        self.colors = {
            'light': {
                'bg': '#f0f0f0',
                'fg': '#000000',
                'listbox_bg': '#ffffff',
                'listbox_fg': '#000000',
                'category_bg': '#34495e',
                'category_fg': '#ffffff',
                'selected_bg': '#3498db',
                'selected_fg': '#ffffff',
                'header_bg': '#34495e',
                'header_fg': '#ffffff'
            },
            'dark': {
                'bg': '#2b2b2b',
                'fg': '#ffffff',
                'listbox_bg': '#1e1e1e',
                'listbox_fg': '#ffffff',
                'category_bg': '#34495e',
                'category_fg': '#ffffff',
                'selected_bg': '#3498db',
                'selected_fg': '#ffffff',
                'header_bg': '#34495e',
                'header_fg': '#ffffff'
            }
        }
    
    def get_colors(self):
        """Get current theme colors."""
        return self.colors[self.current_theme]
    
    def get_color(self, key):
        """Get specific color from current theme."""
        return self.colors[self.current_theme].get(key, '#ffffff')
    
    def is_dark_mode(self):
        """Check if dark mode is active."""
        return self.current_theme == 'dark'
