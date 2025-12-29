"""
Application theme for Starsector Automated Modlist Installer.
Neutral palette and styling without external app naming.
"""


class AppTheme:
    """Theme configuration with Starsector-themed colors (neutral naming)."""
    
    # Primary colors (Cyan/Turquoise)
    PRIMARY = "#49FCFF"  # Bright cyan
    PRIMARY_DARK = "#3BCBE8"  # Darker cyan
    SECONDARY = "#3BCBE8"  # Secondary cyan
    
    # Surface/Background colors (Dark blue)
    SURFACE_DARK = "#0E162B"  # Very dark blue background
    SURFACE = "#202941"  # Dark blue surface
    SURFACE_LIGHT = "#2A3552"  # Slightly lighter surface
    
    # Text colors
    TEXT_PRIMARY = "#E8EAF0"  # Light text for dark backgrounds
    TEXT_SECONDARY = "#9CA3AF"  # Muted text
    TEXT_DISABLED = "#6B7280"  # Disabled text
    
    # State colors
    ERROR = "#FC6300"  # Orange-red
    WARNING = "#FDD418"  # Yellow
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
    GITHUB_BG = "#1A3A5A"  # Dark blue
    GITHUB_FG = SUCCESS
    GDRIVE_BG = "#1A3A5A"  # Dark blue
    GDRIVE_FG = SUCCESS
    MEDIAFIRE_BG = "#1A3A5A"  # Dark blue
    MEDIAFIRE_FG = SUCCESS
    OTHER_BG = "#4A3A1A"  # Dark yellow-ish
    OTHER_FG = WARNING
    FAILED_BG = "#4A1A1A"  # Dark red-ish
    FAILED_FG = ERROR
    
    # Constants
    CORNER_RADIUS = 6
    
    @classmethod
    def configure_ttk_styles(cls, style):
        """Configure ttk widget styles to match the app theme."""
        # Configure Combobox
        style.theme_use('clam')  # Use clam theme as base for customization
        
        style.configure('TCombobox',
                       fieldbackground=cls.SURFACE_DARK,
                       background=cls.SURFACE,
                       foreground=cls.TEXT_PRIMARY,
                       bordercolor=cls.BORDER,
                       arrowcolor=cls.PRIMARY,
                       selectbackground=cls.PRIMARY,
                       selectforeground=cls.SURFACE_DARK)
        
        style.map('TCombobox',
                 fieldbackground=[('readonly', cls.SURFACE_DARK)],
                 selectbackground=[('readonly', cls.SURFACE_DARK)],
                 selectforeground=[('readonly', cls.TEXT_PRIMARY)])
        
        # Configure Progressbar
        style.configure('TProgressbar',
                       background=cls.PRIMARY,
                       troughcolor=cls.SURFACE_DARK,
                       bordercolor=cls.BORDER,
                       lightcolor=cls.PRIMARY,
                       darkcolor=cls.PRIMARY_DARK)
        
        # Configure Frame
        style.configure('TFrame',
                       background=cls.SURFACE)
        
        # Configure Label
        style.configure('TLabel',
                       background=cls.SURFACE,
                       foreground=cls.TEXT_PRIMARY)
    
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
                "bg": "#DC2626",  # Rouge
                "fg": cls.BUTTON_DANGER_FG,
                "activebackground": "#B91C1C",  # Rouge plus foncé au hover
                "activeforeground": cls.BUTTON_DANGER_FG,
            },
            "success": {
                "bg": cls.SUCCESS,
                "fg": cls.BUTTON_PRIMARY_FG,
                "activebackground": "#27AE60",
                "activeforeground": cls.BUTTON_PRIMARY_FG,
            },
            "warning": {
                "bg": "#2563EB",  # Bleu foncé
                "fg": "#FFFFFF",
                "activebackground": "#1D4ED8",  # Bleu plus foncé au hover
                "activeforeground": "#FFFFFF",
            },
            "info": {
                "bg": cls.INFO,
                "fg": cls.BUTTON_PRIMARY_FG,
                "activebackground": cls.PRIMARY_DARK,
                "activeforeground": cls.BUTTON_PRIMARY_FG,
            },
            "plain": {
                "bg": "#2F3A54",  # Bleu légèrement moins sombre que SURFACE_LIGHT
                "fg": cls.TEXT_PRIMARY,
                "activebackground": cls.SURFACE_LIGHT,
                "activeforeground": cls.TEXT_PRIMARY,
            },
            "pastel_warning": {
                "bg": "#D4A574",  # Soft beige/sand
                "fg": cls.SURFACE_DARK,
                "activebackground": "#C89563",
                "activeforeground": cls.SURFACE_DARK,
            },
            "pastel_danger": {
                "bg": "#B85450",  # Bordeaux/dark red
                "fg": "white",
                "activebackground": "#A4433F",
                "activeforeground": "white",
            },
            "pastel_purple": {
                "bg": "#9B7EBD",  # Soft purple/lavender
                "fg": "white",
                "activebackground": "#8566A8",
                "activeforeground": "white",
            },
            "starsector_blue": {
                "bg": cls.PRIMARY,  # Bright cyan Starsector blue
                "fg": cls.BUTTON_PRIMARY_FG,
                "activebackground": cls.PRIMARY_DARK,
                "activeforeground": cls.BUTTON_PRIMARY_FG,
            },
            "delete_purple": {
                "bg": "#7C3AED",  # Violet vif
                "fg": "#FFFFFF",
                "activebackground": "#6D28D9",  # Violet plus foncé au hover
                "activeforeground": "#FFFFFF",
            }
        }
        return styles.get(button_type, styles["primary"])
