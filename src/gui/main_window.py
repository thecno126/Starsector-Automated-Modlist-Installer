"""
Main window for the Modlist Installer application.
Simplified version using modular components.
"""

import tkinter as tk
from tkinter import filedialog
import requests
from . import custom_dialogs
from pathlib import Path
import threading
import concurrent.futures
from datetime import datetime
import sys
import shutil
import time

# Import from our modules
from core import (
    LOG_FILE,
    URL_VALIDATION_TIMEOUT_HEAD, MIN_FREE_SPACE_GB,
    MAX_DOWNLOAD_WORKERS, CACHE_TIMEOUT,
    UI_MIN_WINDOW_WIDTH, UI_MIN_WINDOW_HEIGHT,
    UI_DEFAULT_WINDOW_WIDTH, UI_DEFAULT_WINDOW_HEIGHT,
    ModInstaller, ConfigManager
)
from core.installer import validate_mod_urls
from .dialogs import (
    open_add_mod_dialog,
    open_manage_categories_dialog,
    open_import_csv_dialog,
    open_export_csv_dialog,
    fix_google_drive_url
)
from .ui_builder import (
    create_header,
    create_path_section,
    create_modlist_section,
    create_button_panel,
    create_log_section,
    create_bottom_buttons
)


class ModlistInstaller:
    """Main application window for the Modlist Installer."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Modlist Installer")
        self.root.geometry(f"{UI_DEFAULT_WINDOW_WIDTH}x{UI_DEFAULT_WINDOW_HEIGHT}")
        self.root.resizable(True, True)
        self.root.minsize(UI_MIN_WINDOW_WIDTH, UI_MIN_WINDOW_HEIGHT)
        
        # Config manager
        self.config_manager = ConfigManager()
        
        self.modlist_data = None
        self.categories = self.config_manager.load_categories()
        
        # Installation variables
        self.starsector_path = tk.StringVar()
        self.is_installing = False
        self.is_paused = False
        self.download_futures = []
        self.current_executor = None  # Track active ThreadPoolExecutor for cancellation
        self.downloaded_temp_files = []  # Track downloaded temp files for cleanup on cancel
        self.current_mod_name = tk.StringVar(value="")  # Track current mod being processed
        self.url_validation_cache = {}  # Cache for URL validation results {url: (is_valid, timestamp)}
        
        # Mod installer
        self.mod_installer = ModInstaller(self.log)
        
        # Load preferences and auto-detect
        self.load_preferences()
        self.auto_detect_starsector()
        
        # Create UI
        self.create_ui()
        
        # Load modlist configuration
        self.modlist_data = self.config_manager.load_modlist_config()
        self.display_modlist_info()
        
        # Event bindings
        self.root.bind('<Configure>', self.on_window_resize)
        self._resize_after_id = None
        
        # Handle window close button (X)
        self.root.protocol("WM_DELETE_WINDOW", self.safe_quit)
        
        # Keyboard shortcuts
        self.root.bind('<Control-q>', lambda e: self.root.destroy())
        # Bind Ctrl+S to save configuration
        self.root.bind('<Control-s>', lambda e: self.save_modlist_config(log_message=True))
        self.root.bind('<Control-a>', lambda e: self.open_add_mod_dialog())
    
    def create_ui(self):
        """Create the user interface using modular builders."""
        # Header
        create_header(self.root)
        
        # Main container with horizontal split
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=8, sashrelief=tk.RAISED)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Main controls
        left_frame = tk.Frame(main_container, padx=10, pady=10)
        main_container.add(left_frame, minsize=550, stretch="always")
        
        # Path section
        path_frame, self.path_entry, self.browse_btn, self.path_status_label = create_path_section(
            left_frame, self.starsector_path, self.select_starsector_path
        )
        # Bind validation when user manually edits the path
        self.starsector_path.trace_add('write', lambda *args: self.on_path_changed())
        self.update_path_status()
        
        # Modlist section
        info_frame, main_paned, self.header_text, self.mod_listbox, self.search_var = create_modlist_section(
            left_frame,
            self.on_mod_click,
            lambda e: self.root.after(100, self.display_modlist_info),
            self.on_search_mods
        )
        
        # Track selected line and search filter
        self.selected_mod_line = None
        self.search_filter = ""
        
        # Button panel
        button_callbacks = {
            'reset': self.reset_modlist_config,
            'pause': self.toggle_pause,
            'move_up': self.move_mod_up,
            'move_down': self.move_mod_down,
            'categories': self.open_manage_categories_dialog,
            'add': self.open_add_mod_dialog,
            'edit': self.edit_selected_mod,
            'remove': self.remove_selected_mod,
            'import_csv': self.open_import_csv_dialog,
            'export_csv': self.open_export_csv_dialog
        }
        
        buttons = create_button_panel(main_paned, button_callbacks)
        self.reset_btn = buttons['reset']
        self.pause_install_btn = buttons['pause']
        self.up_btn = buttons['up']
        self.down_btn = buttons['down']
        self.categories_btn = buttons['categories']
        self.add_btn = buttons['add']
        self.edit_btn = buttons['edit']
        self.remove_btn = buttons['remove']
        self.import_btn = buttons['import']
        self.export_btn = buttons['export']
        
        # Bottom buttons (on left side)
        button_frame, self.install_modlist_btn, self.quit_btn = create_bottom_buttons(
            left_frame,
            self.start_installation,
            self.safe_quit
        )
        
        # Right side: Log panel
        right_frame = tk.Frame(main_container, padx=10, pady=10)
        main_container.add(right_frame, minsize=400, stretch="always")
        
        log_frame, self.install_progress_bar, self.log_text = create_log_section(
            right_frame, 
            self.current_mod_name
        )
        
        # Set initial sash position (60% left, 40% right)
        self.root.update_idletasks()
        try:
            main_container.sash_place(0, 600, 1)
        except Exception:
            pass  # Sash position is optional
    
    # ============================================
    # Event Handlers
    # ============================================
    
    def on_window_resize(self, event):
        """Handle window resize events."""
        if event.widget == self.root:
            if self._resize_after_id:
                self.root.after_cancel(self._resize_after_id)
            self._resize_after_id = self.root.after(100, self.display_modlist_info)
    
    def safe_quit(self):
        """Safely quit the application, canceling any ongoing operations."""
        if self.is_installing:
            response = custom_dialogs.askyesno(
                "Installation in Progress",
                "Mod installation is currently running.\n\n"
                "Closing now will cancel all downloads, delete temporary files, and stop the installation.\n\n"
                "Are you sure you want to quit?"
            )
            
            if not response:
                return
            
            # Cancel ongoing operations
            self.log("\n" + "=" * 50)
            self.log("User requested shutdown - canceling installation...", error=True)
            self.log("=" * 50)
            
            # Cancel all pending download futures
            if self.current_executor:
                try:
                    self.current_executor.shutdown(wait=False, cancel_futures=True)
                    self.log("Download tasks canceled")
                except (RuntimeError, AttributeError) as e:
                    self.log(f"Error canceling tasks: {type(e).__name__}", error=True)
            
            # Clean up temporary files
            self._cleanup_temp_files()
            
            self.is_installing = False
            self.is_paused = False
        
        # Save configuration before closing
        self.save_modlist_config()
        
        # Cleanup and exit
        self.log("Application closing...")
        self.root.destroy()
    
    def on_mod_click(self, event):
        """Handle click on mod list."""
        index = self.mod_listbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        line_text = self.mod_listbox.get(f"{line_num}.0", f"{line_num}.end")
        
        if line_text.strip().startswith("•"):
            self.selected_mod_line = line_num
            self.highlight_selected_mod()
    
    def on_search_mods(self, search_text):
        """Handle search filter changes."""
        self.search_filter = search_text.lower().strip()
        self.display_modlist_info()
    
    # ============================================
    # Dialog Methods
    # ============================================
    
    def open_add_mod_dialog(self):
        open_add_mod_dialog(self.root, self)
    
    def open_manage_categories_dialog(self):
        open_manage_categories_dialog(self.root, self)
    
    def open_import_csv_dialog(self):
        open_import_csv_dialog(self.root, self)
    
    def open_export_csv_dialog(self):
        open_export_csv_dialog(self.root, self)
    
    # ============================================
    # Mod Management
    # ============================================
    
    def _is_url_cached(self, url):
        """Check if URL validation result is in cache and still valid.
        
        Returns:
            tuple: (is_cached, is_valid) - (True, bool) if cached, (False, None) if not
        """
        if url in self.url_validation_cache:
            is_valid, timestamp = self.url_validation_cache[url]
            if time.time() - timestamp < CACHE_TIMEOUT:
                return (True, is_valid)
        return (False, None)
    
    def _cache_url_result(self, url, is_valid):
        """Store URL validation result in cache."""
        self.url_validation_cache[url] = (is_valid, time.time())
    
    def validate_url(self, url: str, use_cache: bool = True) -> bool:
        """Return True if the URL appears reachable.
        
        Args:
            url: URL to validate
            use_cache: If True, use cached validation results (default: True)
        """
        # Check cache first
        if use_cache:
            is_cached, is_valid = self._is_url_cached(url)
            if is_cached:
                return is_valid
        
        try:
            # Try HEAD first (lighter)
            resp = requests.head(url, timeout=URL_VALIDATION_TIMEOUT_HEAD, allow_redirects=True)
            if 200 <= resp.status_code < 400:
                result = True
            else:
                # Some servers don't support HEAD, fallback to GET
                resp = requests.get(url, stream=True, timeout=URL_VALIDATION_TIMEOUT_HEAD, allow_redirects=True)
                result = 200 <= resp.status_code < 400
            
            self._cache_url_result(url, result)
            return result
        except Exception:
            self._cache_url_result(url, False)
            return False

    def add_mod_to_config(self, mod: dict) -> None:
        """Append a mod entry to the config."""
        if not self.modlist_data:
            self.modlist_data = self.config_manager.load_modlist_config()
        
        if not self.modlist_data:
            return
        
        name = mod.get('name')
        url = mod.get('download_url')
        mods = self.modlist_data.setdefault('mods', [])
        
        if any(m.get('name') == name or m.get('download_url') == url for m in mods):
            return
        
        mods.append(mod)
        self.save_modlist_config()
        
        if threading.current_thread() is threading.main_thread():
            self.display_modlist_info()
        else:
            self.root.after(0, self.display_modlist_info)
    
    def remove_selected_mod(self):
        """Remove the currently selected mod."""
        if self.selected_mod_line is None:
            custom_dialogs.showwarning("No Selection", "Please select a mod to remove")
            return
        
        line_text = self.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        
        if not mod_name:
            custom_dialogs.showwarning("Invalid Selection", "Please select a mod (not a category header)")
            return
        
        if not custom_dialogs.askyesno(
            "Confirm Removal",
            f"Are you sure you want to remove '{mod_name}' from the modlist?\n\nThis action cannot be undone."
        ):
            return
        
        mods = self.modlist_data.get('mods', [])
        original_count = len(mods)
        self.modlist_data['mods'] = [m for m in mods if m['name'] != mod_name]
        
        if len(self.modlist_data['mods']) < original_count:
            self.log(f"Removed mod: {mod_name}")
            self.save_modlist_config()
            self.display_modlist_info()
            self.selected_mod_line = None
        else:
            custom_dialogs.showerror("Error", f"Mod '{mod_name}' not found in configuration")
    
    def edit_selected_mod(self):
        """Edit the currently selected mod."""
        if self.selected_mod_line is None:
            custom_dialogs.showwarning("No Selection", "Please select a mod to edit")
            return
        
        line_text = self.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        
        if not mod_name:
            custom_dialogs.showwarning("Invalid Selection", "Please select a mod (not a category header)")
            return
        
        # Find the mod in the modlist
        current_mod = self._find_mod_by_name(mod_name)
        if not current_mod:
            custom_dialogs.showerror("Error", f"Mod '{mod_name}' not found in configuration")
            return
        
        # Open edit dialog
        from .dialogs import open_edit_mod_dialog
        open_edit_mod_dialog(self.root, self, current_mod)
    
    # ============================================
    # Mod Reordering
    # ============================================
    
    def _move_mod_in_category(self, mod_name, current_mod, direction):
        """Move mod up or down within category or to adjacent category.
        
        Args:
            mod_name: Name of the mod to move
            current_mod: Mod dictionary
            direction: 1 for down, -1 for up
        """
        mods = self.modlist_data.get('mods', [])
        current_category = current_mod.get('category', 'Uncategorized')
        category_mods = [m for m in mods if m.get('category', 'Uncategorized') == current_category]
        
        try:
            pos_in_category = category_mods.index(current_mod)
        except ValueError:
            return
        
        # Check if we can move within category
        can_move_in_category = (
            (direction == -1 and pos_in_category > 0) or
            (direction == 1 and pos_in_category < len(category_mods) - 1)
        )
        
        if can_move_in_category:
            # Swap with adjacent mod in same category
            adjacent_mod = category_mods[pos_in_category + direction]
            idx_current = mods.index(current_mod)
            idx_adjacent = mods.index(adjacent_mod)
            mods[idx_current], mods[idx_adjacent] = mods[idx_adjacent], mods[idx_current]
            
            self.save_modlist_config()
            self.display_modlist_info()
            self.selected_mod_line = max(1, self.selected_mod_line + direction)
            self.highlight_selected_mod()
        else:
            # Move to adjacent category
            find_category = self._find_category_above if direction == -1 else self._find_category_below
            target_category = find_category(self.selected_mod_line, current_category if direction == -1 else None)
            
            if target_category:
                current_mod['category'] = target_category
                self.log(f"Moved '{mod_name}' to category '{target_category}'")
                self.save_modlist_config()
                self.display_modlist_info()
                self.find_and_select_mod(mod_name)
    
    def move_mod_up(self):
        """Move selected mod up."""
        if self.selected_mod_line is None:
            return
        
        line_text = self.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        if not mod_name:
            return
        
        current_mod = self._find_mod_by_name(mod_name)
        if current_mod:
            self._move_mod_in_category(mod_name, current_mod, -1)
    
    def move_mod_down(self):
        """Move selected mod down."""
        if self.selected_mod_line is None:
            return
        
        line_text = self.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        if not mod_name:
            return
        
        current_mod = self._find_mod_by_name(mod_name)
        if current_mod:
            self._move_mod_in_category(mod_name, current_mod, 1)
    
    def _find_category_above(self, line_num, current_category=None):
        """Find category header above given line.
        
        Args:
            line_num: Line number to search from
            current_category: Optional category to exclude from results
        """
        check_line = line_num - 1
        while check_line >= 1:
            check_text = self.mod_listbox.get(f"{check_line}.0", f"{check_line}.end").strip()
            if check_text and not check_text.startswith("•"):
                if current_category is None or check_text != current_category:
                    return check_text
            check_line -= 1
        return None
    
    def _find_category_below(self, line_num):
        """Find category header below given line."""
    def _find_category_below(self, line_num):
        """Find category header below given line."""
        try:
            max_line = int(self.mod_listbox.index('end-1c').split('.')[0])
        except (tk.TclError, ValueError):
            max_line = 1
        
        check_line = line_num + 1
        while check_line <= max_line:
            check_text = self.mod_listbox.get(f"{check_line}.0", f"{check_line}.end").strip()
            if check_text and not check_text.startswith("•"):
                return check_text
            check_line += 1
        return None
    
    # ============================================
    # Display
    # ============================================
    
    def save_modlist_config(self, log_message=False):
        """Save the current modlist configuration.
        
        Args:
            log_message: If True, log a confirmation message (default: False)
        """
        if not self.modlist_data:
            return
        self.config_manager.save_modlist_config(self.modlist_data)
        if log_message:
            self.log("Configuration saved", debug=True)
    
    def reset_modlist_config(self):
        """Reset the modlist configuration."""
        response = custom_dialogs.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset the modlist configuration?\n\nThis will remove all mods and reset metadata to default values.\n\nThis action cannot be undone."
        )
        
        if not response:
            return
        
        self.log("Resetting modlist configuration...")
        self.modlist_data = self.config_manager.reset_to_default()
        self.display_modlist_info()
        self.log("Configuration reset to default.")
        custom_dialogs.showsuccess("Reset Complete", "Modlist configuration has been reset to default.")
    
    def display_modlist_info(self):
        """Display the modlist information."""
        if not self.modlist_data:
            return
        
        # Update header
        self.header_text.config(state=tk.NORMAL)
        self.header_text.delete(1.0, tk.END)
        
        header_info = (
            f"Name: {self.modlist_data.get('modlist_name') or 'Unnamed'}\n"
            f"Version: {self.modlist_data.get('version') or 'n/a'}\n"
            f"Compatible with: {self.modlist_data.get('starsector_version') or 'N/A'}\n"
            f"Description: {self.modlist_data.get('description') or 'n/a'}"
        )
        
        self.header_text.insert(1.0, header_info)
        self.header_text.config(state=tk.DISABLED)
        
        # Update mod list
        self.mod_listbox.config(state=tk.NORMAL)
        self.mod_listbox.delete(1.0, tk.END)
        
        # Configure category and selection tags (system colors for text)
        self.mod_listbox.tag_configure('category', background='#34495e', 
            foreground='#ffffff', justify='center')
        self.mod_listbox.tag_configure('selected', background='#3498db', 
            foreground='#ffffff')
        
        # Group mods by category
        mods = self.modlist_data.get('mods', [])
        
        # Apply search filter if active
        if self.search_filter:
            mods = [m for m in mods if self.search_filter in m.get('name', '').lower()]
        
        categories = {}
        for mod in mods:
            cat = mod.get('category', 'Uncategorized')
            categories.setdefault(cat, []).append(mod)
        
        # Display categories (only those with mods after filtering)
        for cat in self.categories:
            if cat in categories:
                self.mod_listbox.insert(tk.END, f"{cat}\n", 'category')
                
                for mod in categories[cat]:
                    version = f" v{mod['version']}" if mod.get('version') else ""
                    self.mod_listbox.insert(tk.END, f"  • {mod['name']}{version}\n", 'mod')
        
        self.mod_listbox.config(state=tk.DISABLED)
    
    def highlight_selected_mod(self):
        """Highlight the selected mod."""
        if self.selected_mod_line is None:
            return
            
        self.mod_listbox.config(state=tk.NORMAL)
        self.mod_listbox.tag_remove('selected', '1.0', tk.END)
        self.mod_listbox.tag_add('selected', f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        self.mod_listbox.config(state=tk.DISABLED)
    
    def find_and_select_mod(self, mod_name):
        """Find and select a mod by name."""
        max_line = int(self.mod_listbox.index('end-1c').split('.')[0])
        
        for line_num in range(1, max_line + 1):
            line_text = self.mod_listbox.get(f"{line_num}.0", f"{line_num}.end")
            if line_text.strip().startswith("•") and mod_name in line_text:
                self.selected_mod_line = line_num
                self.highlight_selected_mod()
                return
        
        self.selected_mod_line = None
    
    # ============================================
    # Utility Methods
    # ============================================
    
    def _extract_mod_name_from_line(self, line_text):
        """Extract mod name from a listbox line."""
        if not line_text.strip().startswith("•"):
            return None
        return line_text.replace("  • ", "").split(" v")[0].strip()
    
    def _find_mod_by_name(self, mod_name):
        """Find a mod dict by name."""
        mods = self.modlist_data.get('mods', [])
        return next((m for m in mods if m['name'] == mod_name), None)
    
    def log(self, message, error=False, info=False, warning=False, debug=False):
        """Append a message to the log with different severity levels.
        
        Args:
            message: Message to log
            error: If True, display in red (for errors)
            info: If True, display in blue (for informational messages)
            warning: If True, display in orange (for warnings)
            debug: If True, display in gray (for debug messages)
        """
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self.log(message, error, info, warning, debug))
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Determine prefix and log level
        if error:
            prefix = 'ERROR: '
            level = 'ERROR'
        elif warning:
            prefix = 'WARN: '
            level = 'WARN'
        elif info:
            prefix = 'INFO: '
            level = 'INFO'
        elif debug:
            prefix = 'DEBUG: '
            level = 'DEBUG'
        else:
            prefix = ''
            level = 'INFO'
        
        log_entry = f"[{timestamp}] {prefix}{message}\n"
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass

        self.log_text.config(state=tk.NORMAL)
        
        # Configure tag colors for different log levels
        if error:
            tag = "error"
            self.log_text.tag_config("error", foreground="#e74c3c")  # Red
        elif warning:
            tag = "warning"
            self.log_text.tag_config("warning", foreground="#e67e22")  # Orange
        elif info:
            tag = "info"
            self.log_text.tag_config("info", foreground="#3498db")  # Blue
        elif debug:
            tag = "debug"
            self.log_text.tag_config("debug", foreground="#95a5a6")  # Gray
        else:
            tag = "normal"
        
        self.log_text.insert(tk.END, f"{message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    # ============================================
    # Starsector Path Management
    # ============================================
    
    def load_preferences(self):
        """Load user preferences."""
        prefs = self.config_manager.load_preferences()
        if 'last_starsector_path' in prefs:
            path = Path(prefs['last_starsector_path'])
            if path.exists():
                self.starsector_path.set(str(path))
        if 'theme' in prefs:
            self.current_theme = prefs['theme']
    
    def save_preferences(self):
        """Save user preferences."""
        prefs = {
            'last_starsector_path': self.starsector_path.get(),
            'theme': self.current_theme
        }
        self.config_manager.save_preferences(prefs)
    
    def auto_detect_starsector(self):
        """Auto-detect Starsector installation."""
        platform_paths = {
            "win32": [
                Path("C:/Program Files (x86)/Fractal Softworks/Starsector"),
                Path("C:/Program Files/Fractal Softworks/Starsector"),
                Path.home() / "Games/Starsector"
            ],
            "darwin": [
                Path.home() / "Applications/Starsector.app",
                Path("/Applications/Starsector.app")
            ]
        }
        
        common_paths = platform_paths.get(sys.platform, [
            Path.home() / "Games/starsector",
            Path.home() / ".local/share/starsector",
            Path("/opt/starsector")
        ])
        
        for path in common_paths:
            if path.exists() and (path / "mods").exists():
                self.starsector_path.set(str(path))
                self._auto_detected = True
                return
        
        self._auto_detected = False
    
    def validate_starsector_path(self, path_str):
        """Validate Starsector installation path."""
        path = Path(path_str)
        if not path.exists():
            return False, "Path does not exist"
        
        # macOS app bundle
        if self._is_mac_app_bundle(path):
            return self._ensure_mods_folder(path)
        
        # Windows/Linux installation
        if self._has_jre(path) and self._has_game_files(path):
            return self._ensure_mods_folder(path)
        
        return False, "Not a valid Starsector installation (missing JRE or game files)"
    
    def _is_mac_app_bundle(self, path):
        """Check if path is a macOS Starsector.app bundle."""
        return (
            str(path).endswith('.app') and 
            (path / "Contents/Home").exists() and
            (path / "Contents/Resources/Java").exists()
        )
    
    def _has_jre(self, path):
        """Check if Starsector installation has JRE."""
        return any([
            (path / "jre").exists(),
            (path / "jre_linux").exists(),
            (path / "Contents/Home").exists(),
        ])
    
    def _has_game_files(self, path):
        """Check if Starsector installation has game files."""
        return any([
            (path / "starsector.exe").exists(),
            (path / "starsector.sh").exists(),
            (path / "Contents/Resources/Java/starsector.command").exists(),
            (path / "Contents/Resources/Java").exists(),
        ])
    
    def _ensure_mods_folder(self, path):
        """Ensure mods folder exists, create if needed."""
        mods_folder = path / "mods"
        if mods_folder.exists():
            return True, "Valid"
        
        try:
            mods_folder.mkdir(parents=True, exist_ok=True)
            self.log(f"Created mods folder: {mods_folder}")
            return True, "Valid"
        except Exception as e:
            return False, f"Cannot create mods folder: {e}"
    
    def check_disk_space(self, required_gb=MIN_FREE_SPACE_GB):
        """Check if there's enough free disk space."""
        if not self.starsector_path.get():
            return True, ""
        
        try:
            path = Path(self.starsector_path.get())
            stat = shutil.disk_usage(path)
            free_gb = stat.free / (1024**3)
            
            if free_gb < required_gb:
                return False, f"Low disk space: {free_gb:.1f}GB free (recommended: {required_gb}GB+)"
            return True, f"{free_gb:.1f}GB free"
        except Exception:
            return True, ""
    
    def select_starsector_path(self):
        """Open dialog to select Starsector folder."""
        folder = filedialog.askdirectory(
            title="Select Starsector installation folder",
            initialdir=self.starsector_path.get() if self.starsector_path.get() else str(Path.home())
        )
        
        if folder:
            is_valid, message = self.validate_starsector_path(folder)
            if is_valid:
                self.starsector_path.set(folder)
                self.save_preferences()
                self.update_path_status()
                self.log(f"Starsector path set to: {folder}")
            else:
                custom_dialogs.showerror("Invalid Path", message)
    
    def on_path_changed(self):
        """Called when the path is manually edited by the user."""
        # Debounce validation to avoid validating on every keystroke
        if hasattr(self, '_path_validation_timer'):
            self.root.after_cancel(self._path_validation_timer)
        self._path_validation_timer = self.root.after(500, self.update_path_status)
    
    def update_path_status(self):
        """Update the path status label."""
        path = self.starsector_path.get()
        
        if not path:
            self.path_status_label.config(text="⚠ No Starsector installation detected", fg="#e67e22")
            return
        
        is_valid, message = self.validate_starsector_path(path)
        if is_valid:
            if hasattr(self, '_auto_detected') and self._auto_detected:
                self.path_status_label.config(text="✓ Auto-detected", fg="#27ae60")
            else:
                self.path_status_label.config(text="✓ Valid path", fg="#27ae60")
        else:
            self.path_status_label.config(text=f"✗ {message}", fg="#e74c3c")
    
    # ============================================
    # Installation
    # ============================================
    
    def toggle_pause(self):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_install_btn.config(text="Resume", bg="#e67e22")
            self.log("Installation paused")
        else:
            self.pause_install_btn.config(text="Pause", bg="#f39c12")
            self.log("Installation resumed")
    
    def start_installation(self):
        """Start the installation process."""
        if self.is_installing:
            return
        
        if not self.starsector_path.get():
            response = custom_dialogs.askyesno(
                "Starsector Path Required",
                "Starsector installation folder not set.\n\nWould you like to select it now?"
            )
            if response:
                folder = filedialog.askdirectory(title="Select Starsector folder")
                if folder:
                    is_valid, message = self.validate_starsector_path(folder)
                    if is_valid:
                        self.starsector_path.set(folder)
                        self.save_preferences()
                        self.log(f"Starsector path set: {folder}")
                    else:
                        custom_dialogs.showerror("Invalid Path", message)
                        return
                else:
                    return
            else:
                return
        
        starsector_dir = Path(self.starsector_path.get())
        
        is_valid, message = self.validate_starsector_path(str(starsector_dir))
        if not is_valid:
            custom_dialogs.showerror("Invalid Path", message)
            return
        
        has_space, space_msg = self.check_disk_space()
        if not has_space:
            self.log(space_msg, warning=True)
            response = custom_dialogs.askyesno("Low Disk Space", f"{space_msg}\n\nContinue anyway?")
            if not response:
                return
        
        if not self.modlist_data:
            custom_dialogs.showerror("Error", "No modlist configuration loaded")
            return
        
        # Validate URLs
        self.log("Validating mod URLs (this may take a moment)...")
        self.install_modlist_btn.config(text="Validating URLs...")
        
        results = self._validate_urls_async()
        self.install_modlist_btn.config(text="Install Modlist")
        
        if not results:
            return
        
        # Show validation summary and check if user wants to continue
        if not self._show_validation_summary(results):
            return
        
        # Start installation
        self.is_installing = True
        self.is_paused = False
        self.install_modlist_btn.config(state=tk.DISABLED, text="Installing...")
        self.pause_install_btn.config(state=tk.NORMAL)
        self.install_progress_bar['value'] = 0
        
        thread = threading.Thread(target=self.install_mods, daemon=True)
        thread.start()
    
    def _validate_urls_async(self):
        """Run URL validation in background thread and wait for results.
        
        Returns:
            dict: Validation results or None if timeout/error
        """
        validation_result = {'data': None, 'error': None}
        
        def run_validation():
            try:
                validation_result['data'] = validate_mod_urls(
                    self.modlist_data['mods'], 
                    progress_callback=None
                )
            except Exception as e:
                validation_result['error'] = str(e)
        
        validation_thread = threading.Thread(target=run_validation, daemon=True)
        validation_thread.start()
        
        # Wait with periodic UI updates
        max_wait = 60
        elapsed = 0
        while validation_thread.is_alive() and elapsed < max_wait:
            self.root.update()
            validation_thread.join(timeout=0.1)
            elapsed += 0.1
        
        if validation_result['error']:
            custom_dialogs.showerror("Validation Error", f"Failed to validate URLs: {validation_result['error']}")
            return None
        
        if not validation_result['data']:
            custom_dialogs.showerror("Validation Timeout", "URL validation took too long. Try again or check your internet connection.")
            return None
        
        return validation_result['data']
    
    def _show_validation_summary(self, results):
        """Show validation results summary and prompt user to continue.
        
        Returns:
            bool: True if user wants to continue, False otherwise
        """
        github_count = len(results['github'])
        gdrive_mods = results['google_drive']
        other_domains = results['other']
        failed_list = results['failed']
        
        total_other = sum(len(mods) for mods in other_domains.values())
        self.log(f"GitHub: {github_count}, Google Drive: {len(gdrive_mods)}, Other: {total_other}, Failed: {len(failed_list)}")
        
        if github_count > 0 or gdrive_mods or other_domains or failed_list:
            action = custom_dialogs.show_validation_report(
                self.root,
                github_count,
                gdrive_mods,
                other_domains,
                failed_list
            )
            
            if action == 'cancel':
                self.log("Installation cancelled by user")
                return False
        
        return True
        
        # Start installation directly (validation already confirmed)
        self.is_installing = True
        self.is_paused = False
        self.install_modlist_btn.config(state=tk.DISABLED, text="Installing...")
        self.pause_install_btn.config(state=tk.NORMAL)
        self.install_progress_bar['value'] = 0
        
        thread = threading.Thread(target=self.install_mods, daemon=True)
        thread.start()
    
    def install_specific_mods(self, mod_names, temp_mods=None, skip_gdrive_check=False):
        """Install only specific mods by name.
        
        Args:
            mod_names: List of mod names to install
            temp_mods: Optional list of mod dictionaries with temporary URLs (e.g., fixed Google Drive)
            skip_gdrive_check: If True, skip Google Drive verification (already confirmed by user)
        """
        # Use temp_mods if provided, otherwise filter from main modlist
        if temp_mods:
            mods_to_install = temp_mods
        else:
            mods_to_install = [mod for mod in self.modlist_data['mods'] if mod.get('name') in mod_names]
        
        if not mods_to_install:
            custom_dialogs.showerror("Error", "No mods found to install")
            return
        
        self.is_installing = True
        self.is_paused = False
        self.install_modlist_btn.config(state=tk.DISABLED, text="Installing...")
        self.pause_install_btn.config(state=tk.NORMAL)
        self.install_progress_bar['value'] = 0
        
        # Run installation in thread with filtered mods
        def run_specific_installation():
            self._install_mods_internal(mods_to_install, skip_gdrive_check=skip_gdrive_check)
        
        thread = threading.Thread(target=run_specific_installation, daemon=True)
        thread.start()
    
    def install_mods(self):
        """Install the mods from the modlist using parallel downloads and sequential extraction."""
        self._install_mods_internal(self.modlist_data['mods'])
    
    def _cleanup_temp_files(self):
        """Clean up temporary files created during mod installation."""
        import tempfile
        import glob
        
        deleted_count = 0
        
        # First, clean up tracked downloaded files
        for temp_file in self.downloaded_temp_files:
            try:
                if os.path.isfile(temp_file):
                    os.unlink(temp_file)
                    deleted_count += 1
            except (OSError, PermissionError):
                pass  # Silently ignore files we can't delete
        
        # Clear the tracking list
        self.downloaded_temp_files = []
        
        # Then clean up any remaining modlist_ temp files
        temp_dir = tempfile.gettempdir()
        pattern = os.path.join(temp_dir, "modlist_*")
        
        for temp_file in glob.glob(pattern):
            try:
                if os.path.isfile(temp_file):
                    os.unlink(temp_file)
                    deleted_count += 1
            except (OSError, PermissionError):
                pass  # Silently ignore files we can't delete
        
        if deleted_count > 0:
            self.log(f"Cleaned up {deleted_count} temporary file(s)")
    
    def _download_mods_parallel(self, mods_to_download, skip_gdrive_check=False, max_workers=None):
        """Download mods in parallel using ThreadPoolExecutor.
        
        Args:
            mods_to_download: List of mod dictionaries to download
            skip_gdrive_check: If True, skip Google Drive HTML detection
            max_workers: Number of parallel download workers (default: MAX_DOWNLOAD_WORKERS)
            
        Returns:
            tuple: (download_results, gdrive_failed)
                download_results: List of (mod, temp_path, is_7z) tuples for successful downloads
                gdrive_failed: List of mods that failed due to Google Drive HTML
        """
        download_results = []
        gdrive_failed = []
        
        # Reset temp files tracker
        self.downloaded_temp_files = []
        
        if max_workers is None:
            max_workers = MAX_DOWNLOAD_WORKERS
        
        self.current_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_to_mod = {
                self.current_executor.submit(self.mod_installer.download_archive, mod, skip_gdrive_check): mod
                for mod in mods_to_download
            }
            completed = 0
            for future in concurrent.futures.as_completed(future_to_mod):
                # Check if installation was canceled
                if not self.is_installing:
                    self.log("Installation canceled by user", error=True)
                    break
                
                while self.is_paused:
                    threading.Event().wait(0.1)
                    
                mod = future_to_mod[future]
                mod_name = mod.get('name', 'Unknown')
                self.current_mod_name.set(f"⬇ Downloading: {mod_name}")
                
                try:
                    temp_path, is_7z = future.result()
                    if temp_path == 'GDRIVE_HTML':
                        gdrive_failed.append(mod)
                        self.log(f"  ⚠️  Google Drive returned HTML (virus scan warning): {mod.get('name')}", error=True)
                    elif temp_path:
                        download_results.append((mod, temp_path, is_7z))
                        self.downloaded_temp_files.append(temp_path)  # Track for cleanup
                        self.log(f"  ✓ Downloaded: {mod.get('name')}")
                    else:
                        self.log(f"  ✗ Failed to download: {mod.get('name')}", error=True)
                except Exception as e:
                    self.log(f"  ✗ Download error for {mod.get('name')}: {e}", error=True)
                    
                completed += 1
                self.install_progress_bar['value'] = (completed / len(mods_to_download)) * 50
                self.root.update_idletasks()
        finally:
            if self.current_executor:
                self.current_executor.shutdown(wait=True)
                self.current_executor = None
        
        return download_results, gdrive_failed

    def _install_mods_internal(self, mods_to_install, skip_gdrive_check=False):
        """Internal method to install a list of mods.
        
        Args:
            mods_to_install: List of mod dictionaries to install
            skip_gdrive_check: If True, skip Google Drive verification (already confirmed by user)
        """
        mods_dir = Path(self.starsector_path.get()) / "mods"
        total_mods = len(mods_to_install)

        self.log(f"Starting installation of {total_mods} mod{'s' if total_mods > 1 else ''}...")
        self.log("=" * 50)

        # Step 1: parallel downloads
        self.log(f"Starting parallel downloads (workers={MAX_DOWNLOAD_WORKERS})...")
        download_results, gdrive_failed = self._download_mods_parallel(
            mods_to_install, 
            skip_gdrive_check=skip_gdrive_check
        )
        
        # Check if installation was canceled during downloads
        if not self.is_installing:
            self.log("Installation aborted")
            self.install_modlist_btn.config(state=tk.NORMAL, text="Install Modlist")
            self.pause_install_btn.config(state=tk.DISABLED)
            return
        
        # Step 2: sequential extraction
        self.log("Starting sequential extraction...")
        extracted = 0
        skipped = 0
        extraction_failures = []  # Track mods that failed extraction
        
        if not download_results:
            self.log("All mods were skipped (already installed or failed to download)", info=True)
            self.install_progress_bar['value'] = 100
        
        for i, (mod, temp_path, is_7z) in enumerate(download_results, 1):
            # Check if installation was canceled
            if not self.is_installing:
                self.log("\nInstallation canceled during extraction", error=True)
                # Clean up remaining unprocessed temp files
                for _, remaining_temp_path, _ in download_results[i-1:]:
                    try:
                        Path(remaining_temp_path).unlink()
                    except Exception:
                        pass
                break
                
            while self.is_paused:
                threading.Event().wait(0.1)
            
            mod_name = mod.get('name', 'Unknown')
            mod_version = mod.get('version')
            
            # Update progress indicator
            self.current_mod_name.set(f"📦 Extracting: {mod_name}")
            
            if mod_version:
                self.log(f"\n[{i}/{len(download_results)}] Installing {mod_name} v{mod_version}...")
            else:
                self.log(f"\n[{i}/{len(download_results)}] Installing {mod_name}...")
            try:
                success = self.mod_installer.extract_archive(Path(temp_path), mods_dir, is_7z)
                try:
                    Path(temp_path).unlink()
                except Exception:
                    pass
                if success == 'skipped':
                    # Already logged by installer
                    skipped += 1
                elif success:
                    self.log(f"  ✓ {mod['name']} installed successfully")
                    extracted += 1
                else:
                    self.log(f"  ✗ Failed to install {mod['name']}", error=True)
                    extraction_failures.append(mod)
                    skipped += 1
            except Exception as e:
                self.log(f"  ✗ Unexpected extraction error for {mod.get('name')}: {e}", error=True)
                extraction_failures.append(mod)
                skipped += 1
            # progress: second half (based on total attempted, not total in list)
            progress = 50 + ((extracted + skipped) / len(download_results)) * 50
            self.install_progress_bar['value'] = progress
            self.root.update_idletasks()
        
        # Identify Google Drive mods that failed extraction (likely HTML instead of ZIP)
        gdrive_extraction_failures = [
            mod for mod in extraction_failures
            if 'drive.google.com' in mod.get('download_url', '') 
            or 'drive.usercontent.google.com' in mod.get('download_url', '')
        ]
        
        # Combine all Google Drive issues (download failures + extraction failures)
        all_gdrive_issues = gdrive_failed + gdrive_extraction_failures
        
        # Final statistics
        self.install_progress_bar['value'] = 100
        self.current_mod_name.set("")  # Clear progress indicator
        
        # Simple statistics
        total_downloaded = len(download_results)
        total_failed_download = len(gdrive_failed)  # Google Drive failures
        total_network_failed = total_mods - total_downloaded - total_failed_download  # Other network errors
        truly_skipped = skipped - len(gdrive_extraction_failures)  # Exclude extraction failures
        
        self.log("\n" + "=" * 50)
        self.log("Installation complete!")
        
        # Build detailed status message
        status_parts = []
        if extracted > 0:
            status_parts.append(f"{extracted} newly installed")
        if truly_skipped > 0:
            status_parts.append(f"{truly_skipped} already present")
        if total_network_failed > 0:
            status_parts.append(f"{total_network_failed} failed")
        if len(all_gdrive_issues) > 0:
            status_parts.append(f"{len(all_gdrive_issues)} Google Drive issues")
        
        if status_parts:
            self.log(f"  {', '.join(status_parts)}")
        
        if len(all_gdrive_issues) > 0:
            self.log("\nGoogle Drive mods not installed:")
            for mod in all_gdrive_issues:
                self.log(f"  - {mod.get('name')}", error=True)
        
        self.log("\nYou can now start Starsector to enable the mods.")

        self.is_installing = False
        self.install_modlist_btn.config(state=tk.NORMAL, text="Install Modlist")
        self.pause_install_btn.config(state=tk.DISABLED)
        
        # Clear temp files tracker (all should be deleted by now)
        self.downloaded_temp_files = []

        # Show manual download instructions for Google Drive mods
        if len(all_gdrive_issues) > 0:
            self._propose_fix_google_drive_urls(all_gdrive_issues)

    def _propose_fix_google_drive_urls(self, failed_mods):
        """Propose to fix Google Drive URLs after installation is complete.
        
        Args:
            failed_mods: List of mod dictionaries that failed to download
        """
        # Create custom dialog matching pre-installation check style
        result = {'action': None}
        
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Main frame
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Failed Google Drive mods section
        gdrive_frame = tk.Frame(main_frame)
        gdrive_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(gdrive_frame, text=f"{len(failed_mods)} Google Drive mod(s) need confirmation to download:", 
                font=("Arial", 10, "bold"), fg="#dc2626").pack(anchor=tk.W, pady=(0, 8))
        
        # List Google Drive mods
        gdrive_list_frame = tk.Frame(gdrive_frame, relief=tk.SUNKEN, bd=1, bg="#ffe6e6")
        gdrive_list_frame.pack(fill=tk.X, pady=(0, 10))
        
        gdrive_text = tk.Text(gdrive_list_frame, height=min(5, len(failed_mods)), width=60,
                             font=("Courier", 9), wrap=tk.WORD, bg="#ffe6e6", relief=tk.FLAT)
        for mod in failed_mods:
            gdrive_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
        gdrive_text.config(state=tk.DISABLED)
        gdrive_text.pack(padx=5, pady=5)
        
        # Warning message
        warning_frame = tk.Frame(gdrive_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 0))
        
        warning_text = tk.Label(warning_frame, 
            text="⚠️  Google can't verify these files due to their size. Confirm only if from a trusted source.",
            font=("Arial", 9), fg="#666", wraplength=500, justify=tk.LEFT)
        warning_text.pack(anchor=tk.W)
        
        # Buttons frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def on_confirm():
            import re
            # Fix Google Drive URLs
            from .dialogs import fix_google_drive_url
            mods_to_download = []
            for mod in failed_mods:
                mod_copy = mod.copy()
                fixed_url = fix_google_drive_url(mod['download_url'])
                mod_copy['download_url'] = fixed_url
                mods_to_download.append(mod_copy)
                if fixed_url != mod['download_url']:
                    self.log(f"🔧 Fixed Google Drive URL: {mod.get('name')}", info=True)
            
            result['action'] = 'confirm'
            dialog.destroy()
            
            # Start download with fixed URLs
            self.install_specific_mods(
                [mod['name'] for mod in mods_to_download],
                temp_mods=mods_to_download,
                skip_gdrive_check=True
            )
        
        def on_cancel():
            result['action'] = 'cancel'
            dialog.destroy()
        
        # Center the buttons
        button_container = tk.Frame(button_frame)
        button_container.pack(anchor=tk.CENTER)
        
        tk.Button(button_container, text="Confirm Installation", command=on_confirm,
                 font=("Arial", 10, "bold"), cursor="hand2", padx=20, pady=8, bg="#4CAF50", fg="black").pack(side=tk.LEFT, padx=(0, 8))
        
        tk.Button(button_container, text="Cancel", command=on_cancel,
                 font=("Arial", 10), cursor="hand2", padx=20, pady=8).pack(side=tk.LEFT)
        
        # Keyboard bindings
        dialog.bind("<Escape>", lambda e: on_cancel())
        dialog.bind("<Return>", lambda e: on_apply())
        
        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        dialog.wait_window()
        
        if result['action'] != 'apply':
            self.log("User declined Google Drive download confirmation", info=True)
            return
        
        # Prepare mods for download (fix URLs if needed, or use usercontent as-is)
        self.log("Preparing Google Drive mods for download...", info=True)
        fixed_mods_list = self._prepare_gdrive_urls(failed_mods)
        
        if fixed_mods_list:
            # Trigger installation directly (no "Retry Installation?" dialog)
            self.install_specific_mods([m['name'] for m in fixed_mods_list], temp_mods=fixed_mods_list, skip_gdrive_check=True)
        else:
            self.log("No URLs could be prepared for download", error=True)

