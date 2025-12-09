"""
TriOS-inspired theme for ASTRA Modlist Installer.
Color palette and styling inspired by TriOS (https://github.com/wispborne/TriOS).
"""


class TriOSTheme:
    """Theme configuration inspired by TriOS with Starsector-themed colors."""
    
    # Primary colors (Cyan/Turquoise from TriOS)
    PRIMARY = "#49FCFF"  # Bright cyan
    PRIMARY_DARK = "#3BCBE8"  # Darker cyan
    SECONDARY = "#3BCBE8"  # Secondary cyan
    
    # Surface/Background colors (Dark blue inspired by TriOS)
    SURFACE_DARK = "#0E162B"  # Very dark blue background
    SURFACE = "#202941"  # Dark blue surface
    SURFACE_LIGHT = "#2A3552"  # Slightly lighter surface
    
    # Text colors
    TEXT_PRIMARY = "#E8EAF0"  # Light text for dark backgrounds
    TEXT_SECONDARY = "#9CA3AF"  # Muted text
    TEXT_DISABLED = "#6B7280"  # Disabled text
    
    # State colors (matching TriOS)
    ERROR = "#FC6300"  # Orange-red (TriOS vanillaErrorColor)
    WARNING = "#FDD418"  # Yellow (TriOS vanillaWarningColor)
    SUCCESS = "#2ECC71"  # Green (standard success color)
    INFO = "#49FCFF"  # Cyan info color
    
    # UI Element colors
    BORDER = "#3A4255"  # Subtle border
    BORDER_ACTIVE = PRIMARY  # Active/focused border
    
    # Button colors
    BUTTON_PRIMARY_BG = PRIMARY
    BUTTON_PRIMARY_FG = "#0E162B"  # Dark text on bright button
    BUTTON_SECONDARY_BG = SURFACE_LIGHT
    BUTTON_SECONDARY_FG = TEXT_PRIMARY
    BUTTON_DANGER_BG = ERROR
    BUTTON_DANGER_FG = "#FFFFFF"
    
    # Category/List colors
    CATEGORY_BG = "#2A3552"  # Darker blue for categories
    CATEGORY_FG = PRIMARY  # Cyan text
    ITEM_SELECTED_BG = "#3A4A6B"  # Selected item background
    ITEM_SELECTED_FG = "#FFFFFF"
    
    # Log colors
    LOG_ERROR = ERROR
    LOG_WARNING = WARNING
    LOG_SUCCESS = SUCCESS
    LOG_INFO = INFO
    LOG_DEBUG = TEXT_SECONDARY
    LOG_NORMAL = TEXT_PRIMARY
    
    # Validation report colors (keeping existing style but with theme colors)
    GITHUB_BG = "#1A4A4A"  # Dark green-ish
    GITHUB_FG = SUCCESS
    GDRIVE_BG = "#1A3A5A"  # Dark blue
    GDRIVE_FG = INFO
    OTHER_BG = "#4A3A1A"  # Dark yellow-ish
    OTHER_FG = WARNING
    FAILED_BG = "#4A1A1A"  # Dark red-ish
    FAILED_FG = ERROR
    
    # Constants
    CORNER_RADIUS = 6  # Matching TriOS cornerRadius
    
    @classmethod
    def get_button_style(cls, button_type="primary"):
        """Get button styling based on type."""
        styles = {
            "primary": {
                "bg": cls.BUTTON_PRIMARY_BG,
                "fg": cls.BUTTON_PRIMARY_FG,
                "activebackground": cls.PRIMARY_DARK,
                "activeforeground": cls.BUTTON_PRIMARY_FG,
            },
            "secondary": {
                "bg": cls.BUTTON_SECONDARY_BG,
                "fg": cls.BUTTON_SECONDARY_FG,
                "activebackground": cls.SURFACE_LIGHT,
                "activeforeground": cls.TEXT_PRIMARY,
            },
            "danger": {
                "bg": cls.BUTTON_DANGER_BG,
                "fg": cls.BUTTON_DANGER_FG,
                "activebackground": "#D95500",
                "activeforeground": cls.BUTTON_DANGER_FG,
            },
            "success": {
                "bg": cls.SUCCESS,
                "fg": cls.BUTTON_PRIMARY_FG,
                "activebackground": "#27AE60",
                "activeforeground": cls.BUTTON_PRIMARY_FG,
            },
            "warning": {
                "bg": cls.WARNING,
                "fg": cls.BUTTON_PRIMARY_FG,
                "activebackground": "#F1C40F",
                "activeforeground": cls.BUTTON_PRIMARY_FG,
            },
            "info": {
                "bg": cls.INFO,
                "fg": cls.BUTTON_PRIMARY_FG,
                "activebackground": cls.PRIMARY_DARK,
                "activeforeground": cls.BUTTON_PRIMARY_FG,
            }
        }
        return styles.get(button_type, styles["primary"])
