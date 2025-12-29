"""Centralized symbols and icons for consistent UI display."""


class LogSymbols:
    """Unicode symbols for log messages and UI elements."""
    
    SUCCESS = "✓"
    ERROR = "✗"
    ERROR_BOLD = "❌"     # U+274C - Cross mark (bold error for dialogs)
    WARNING = "⚠️"
    INFO = "ℹ"
    QUESTION = "?"
    INSTALLED = "✓"
    NOT_INSTALLED = "○"
    UPDATED = "↑"
    
    # List and formatting
    BULLET = "•"         # U+2022 - Bullet point for lists
    TRASH = "🗑"         # U+1F5D1 - Trash/delete indicator
    ARROW_RIGHT = "→"    # U+2192 - Rightwards arrow (for "A → B" transitions)
    SEPARATOR = "─"      # U+2500 - Box drawing light horizontal (line separator)


class UISymbols:
    """Unicode symbols for UI buttons and navigation."""
    
    # Navigation arrows
    ARROW_UP = "⬆"       # U+2B06 - Bold upward arrow for buttons
    ARROW_DOWN = "⬇"     # U+2B07 - Bold downward arrow for buttons
    ARROW_DOWN_ALT = "↓" # U+2193 - Alternative downward arrow
    DOWNLOADING = "⬇"    # Download indicator
    
    # Media controls
    PAUSE = "⏸"          # U+23F8 - Pause button
    PLAY = "▶"           # U+25B6 - Play/Resume button
    
    # Action buttons
    EDIT_METADATA = "⋯"  # U+22EF - Horizontal ellipsis (edit metadata)
    REFRESH = "↻"        # U+21BB - Counterclockwise arrow (refresh)
    IMPORT = "⤓"         # U+2913 - Downward arrow with hook (import)
    EXPORT = "⤒"         # U+2912 - Upward arrow with hook (export)
    SEARCH = "🔍"        # U+1F50D - Magnifying glass
    CLEAR = "✕"          # U+2715 - Multiplication X (clear)
    REMOVE = "✖"         # U+2716 - Heavy multiplication X (remove)
    MINUS = "−"          # U+2212 - Minus sign (remove selected)
    ADD = "➕"           # U+2795 - Heavy plus sign (add)
    PLUS = "+"           # U+002B - Plus sign (add mod)
    SETTINGS = "⚙"       # U+2699 - Gear (settings/categories)
    EDIT = "✏️"          # U+270F - Pencil (edit)
    DELETE = "␡"         # U+2421 - Delete symbol
    SAVE = "💾"          # U+1F4BE - Floppy disk (save/restore backup)
    OPEN_FOLDER = "📂"   # U+1F4C2 - Open folder (import preset)
    FILE = "📄"          # U+1F4C4 - File document (import preset)
