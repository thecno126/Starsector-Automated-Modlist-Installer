"""
Main window for the Modlist Installer application.
Simplified version using modular components.
"""

import tkinter as tk
from tkinter import filedialog, ttk
import re
import requests
from . import dialogs as custom_dialogs
from pathlib import Path
import threading
import concurrent.futures
from datetime import datetime
import os
import shutil
import time

# Import from our modules
from core import (
    LOG_FILE,
    URL_VALIDATION_TIMEOUT_HEAD, MIN_FREE_SPACE_GB,
    MAX_DOWNLOAD_WORKERS, CACHE_TIMEOUT,
    UI_MIN_WINDOW_WIDTH, UI_MIN_WINDOW_HEIGHT,
    UI_DEFAULT_WINDOW_WIDTH, UI_DEFAULT_WINDOW_HEIGHT,
    ModInstaller, ConfigManager, InstallationReport
)
from core.installer import validate_mod_urls, is_mod_up_to_date, resolve_mod_dependencies
from .dialogs import (
    open_add_mod_dialog,
    open_manage_categories_dialog,
    open_import_csv_dialog,
    open_export_csv_dialog,
    show_google_drive_confirmation_dialog
)
from .installation_controller import InstallationController
from .ui_builder import (
    create_header,
    create_path_section,
    create_modlist_section,
    create_log_section,
    create_enable_mods_section,
    create_bottom_buttons
)
from utils.theme import TriOSTheme
from utils.mod_utils import (
    normalize_mod_name,
    is_mod_name_match,
    scan_installed_mods
)
from utils.backup_manager import BackupManager
from utils.path_validator import StarsectorPathValidator
from utils.error_messages import get_user_friendly_error


class ModlistInstaller:
    """Main application window for the Modlist Installer."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Starsector Automated Modlist Installer")
        self.root.geometry(f"{UI_DEFAULT_WINDOW_WIDTH}x{UI_DEFAULT_WINDOW_HEIGHT}")
        self.root.resizable(True, True)
        self.root.minsize(UI_MIN_WINDOW_WIDTH, UI_MIN_WINDOW_HEIGHT)
        
        # Apply TriOS-inspired theme
        self.root.configure(bg=TriOSTheme.SURFACE_DARK)
        
        # Configure ttk styles for themed widgets
        self.style = ttk.Style()
        TriOSTheme.configure_ttk_styles(self.style)
        
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
        
        # Installation controller (delegates complex installation logic)
        self.installation_controller = None  # Initialized after UI is ready
        
        # Log level: 'INFO' (default) or 'DEBUG'
        self.log_level = 'INFO'
        
        # Load preferences and auto-detect
        self.load_preferences()
        self.auto_detect_starsector()
        
        # Create UI
        self.create_ui()
        
        # Initialize installation controller (needs UI to be ready)
        self.installation_controller = InstallationController(self)
        
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
        
        # Drag and drop state for mod list reordering
        self.drag_start_line = None
        self.drag_start_y = None
        self._setup_drag_and_drop()
    
    def _setup_drag_and_drop(self):
        """Set up drag and drop handlers for mod list reordering."""
        self.mod_listbox.bind('<Button-1>', self._on_drag_start, add="+")
        self.mod_listbox.bind('<B1-Motion>', self._on_drag_motion)
        self.mod_listbox.bind('<ButtonRelease-1>', self._on_drag_end, add="+")
    
    def _on_drag_start(self, event):
        """Handle start of drag operation."""
        index = self.mod_listbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        line_text = self.mod_listbox.get(f"{line_num}.0", f"{line_num}.end").strip()
        
        # Only allow dragging mod lines (not categories or empty lines)
        if line_text and (line_text.startswith("✓") or line_text.startswith("○") or line_text.startswith("↑")):
            self.drag_start_line = line_num
            self.drag_start_y = event.y
        else:
            self.drag_start_line = None
    
    def _on_drag_motion(self, event):
        """Handle drag motion."""
        if self.drag_start_line is None:
            return
        
        # Visual feedback could be added here (e.g., change cursor)
        pass
    
    def _on_drag_end(self, event):
        """Handle end of drag operation - reorder mod."""
        if self.drag_start_line is None:
            return
        
        try:
            # Get target line
            index = self.mod_listbox.index(f"@{event.x},{event.y}")
            target_line = int(index.split('.')[0])
            
            # Only proceed if moved significantly
            if abs(target_line - self.drag_start_line) < 1:
                self.drag_start_line = None
                return
            
            # Get source mod name
            source_text = self.mod_listbox.get(f"{self.drag_start_line}.0", f"{self.drag_start_line}.end")
            source_mod_name = self._extract_mod_name_from_line(source_text)
            
            if not source_mod_name:
                self.drag_start_line = None
                return
            
            # Find source mod in data
            source_mod = self._find_mod_by_name(source_mod_name)
            if not source_mod:
                self.drag_start_line = None
                return
            
            # Find target category
            target_category = self._find_category_above(target_line)
            if not target_category:
                self.drag_start_line = None
                return
            
            # Calculate position within target category
            category_start_line = self._find_category_line(target_category)
            if category_start_line is None:
                self.drag_start_line = None
                return
            
            # Count mods between category start and target
            position = 0
            for line_num in range(category_start_line + 1, target_line + 1):
                line_text = self.mod_listbox.get(f"{line_num}.0", f"{line_num}.end").strip()
                if line_text and (line_text.startswith("✓") or line_text.startswith("○") or line_text.startswith("↑")):
                    position += 1
            
            # Move mod
            self._move_mod_to_category_position(source_mod_name, source_mod, target_category, position)
            
        except Exception as e:
            self.log(f"Drag and drop error: {e}", debug=True)
        finally:
            self.drag_start_line = None
    
    def _find_category_line(self, category_name):
        """Find the line number of a category header."""
        try:
            max_line = int(self.mod_listbox.index('end-1c').split('.')[0])
        except (tk.TclError, ValueError):
            return None
        
        for line_num in range(1, max_line + 1):
            line_text = self.mod_listbox.get(f"{line_num}.0", f"{line_num}.end").strip()
            if line_text == category_name:
                return line_num
        return None
    
    def _move_mod_to_category_position(self, mod_name, mod, target_category, position):
        """Move a mod to a specific position within a category."""
        source_category = mod.get('category', 'Uncategorized')
        
        # Remove from source category
        if source_category in self.modlist_data.get('mods_by_category', {}):
            category_mods = self.modlist_data['mods_by_category'][source_category]
            category_mods = [m for m in category_mods if m.get('name') != mod_name]
            self.modlist_data['mods_by_category'][source_category] = category_mods
        
        # Update mod category
        mod['category'] = target_category
        
        # Add to target category at position
        if target_category not in self.modlist_data.get('mods_by_category', {}):
            self.modlist_data['mods_by_category'][target_category] = []
        
        category_mods = self.modlist_data['mods_by_category'][target_category]
        position = max(0, min(position, len(category_mods)))
        category_mods.insert(position, mod)
        
        # Rebuild mods list
        self.modlist_data['mods'] = []
        for category in self.categories:
            if category in self.modlist_data['mods_by_category']:
                self.modlist_data['mods'].extend(self.modlist_data['mods_by_category'][category])
        
        # Save and refresh
        self.save_modlist_config()
        self.display_modlist_info()
        self.log(f"✓ Moved '{mod_name}' to {target_category} (position {position})", debug=True)
    
    def create_ui(self):
        """Create the user interface using modular builders."""
        # Header
        create_header(self.root)
        
        # Main container with horizontal split
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=8, sashrelief=tk.RAISED,
                                       bg=TriOSTheme.SURFACE)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Main controls
        left_frame = tk.Frame(main_container, bg=TriOSTheme.SURFACE)
        left_frame.pack_configure(padx=10, pady=(10, 0))
        main_container.add(left_frame, minsize=550, stretch="always")
        
        # Path section
        path_frame, self.path_entry, self.browse_btn, self.path_status_label = create_path_section(
            left_frame, self.starsector_path, self.select_starsector_path
        )
        # Bind validation when user manually edits the path
        self.starsector_path.trace_add('write', lambda *args: self.on_path_changed())
        self.update_path_status()
        
        # Modlist section
        info_frame, left_container, self.header_text, self.mod_listbox, self.search_var, mod_action_buttons, header_buttons = create_modlist_section(
            left_frame,
            self.on_mod_click,
            lambda e: None,  # No resize callback needed anymore
            self.on_search_mods,
            self.open_import_csv_dialog,
            self.open_export_csv_dialog,
            self.refresh_mod_metadata,
            self.restore_backup_dialog,
            self.reset_modlist_config,
            self.edit_modlist_metadata
        )
        
        # Track selected line and search filter
        self.selected_mod_line = None
        self.search_filter = ""
        
        # Configure action buttons from modlist section
        if mod_action_buttons:
            mod_action_buttons['add'].config(command=self.open_add_mod_dialog)
            mod_action_buttons['edit'].config(command=self.edit_selected_mod)
            mod_action_buttons['remove'].config(command=self.remove_selected_mod)
            mod_action_buttons['categories'].config(command=self.open_manage_categories_dialog)
            self.add_btn = mod_action_buttons['add']
            self.edit_btn = mod_action_buttons['edit']
            self.remove_btn = mod_action_buttons['remove']
            self.categories_btn = mod_action_buttons['categories']
        
        # Store header buttons
        if header_buttons:
            self.import_btn = header_buttons.get('import')
            self.export_btn = header_buttons.get('export')
            self.refresh_btn = header_buttons.get('refresh')
            self.clear_all_btn = header_buttons.get('clear')
            self.restore_backup_btn = header_buttons.get('restore')
            self.edit_metadata_btn = header_buttons.get('edit_metadata')
            self.up_btn = header_buttons.get('up')
            self.down_btn = header_buttons.get('down')
            
            # Configure up/down buttons
            if self.up_btn:
                self.up_btn.config(command=self.move_mod_up)
            if self.down_btn:
                self.down_btn.config(command=self.move_mod_down)
        
        # Bottom buttons (on left side)
        button_frame, self.install_modlist_btn, self.quit_btn = create_bottom_buttons(
            left_frame,
            self.start_installation,
            self.safe_quit
        )
        
        # Right side: Log panel
        right_frame = tk.Frame(main_container, bg=TriOSTheme.SURFACE)
        right_frame.pack_configure(padx=10, pady=(10, 0))
        main_container.add(right_frame, minsize=700, stretch="always")
        
        log_frame, self.install_progress_bar, self.log_text, self.pause_install_btn = create_log_section(
            right_frame, 
            self.current_mod_name,
            self.toggle_pause
        )
        
        # Enable All Mods button (below log, above bottom buttons)
        enable_frame, self.enable_mods_btn = create_enable_mods_section(
            right_frame,
            self.enable_all_installed_mods
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
        
        line_stripped = line_text.strip()
        # Check if it's a mod line (starts with ✓, ○, or ↑)
        if line_stripped.startswith("✓") or line_stripped.startswith("○") or line_stripped.startswith("↑"):
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
        
        # Find and remove the mod using normalized matching
        mods = self.modlist_data.get('mods', [])
        original_count = len(mods)
        
        # Try exact match first
        mod_to_remove = next((m for m in mods if m.get('name') == mod_name), None)
        
        # If not found, try normalized matching
        if not mod_to_remove:
            normalized_search = normalize_mod_name(mod_name)
            mod_to_remove = next((m for m in mods if normalize_mod_name(m.get('name', '')) == normalized_search), None)
        
        if mod_to_remove:
            self.modlist_data['mods'].remove(mod_to_remove)
            self.log(f"Removed mod: {mod_to_remove.get('name')}")
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
            if direction == -1:
                # Moving up - find category above (excluding current)
                target_category = self._find_category_above(self.selected_mod_line, current_category)
            else:
                # Moving down - find category below (should be different from current)
                target_category = self._find_category_below(self.selected_mod_line)
                # Make sure it's different from current category
                if target_category == current_category:
                    target_category = None
            
            if target_category:
                current_mod['category'] = target_category
                self.log(f"Moved '{mod_name}' to category '{target_category}'")
                self.save_modlist_config()
                self.display_modlist_info()
                self.find_and_select_mod(mod_name)
    
    def toggle_expand_categories(self):
        """Toggle expand/collapse all categories (placeholder for future implementation)."""
        self.log("Category expand/collapse not yet implemented", debug=True)
    
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
            # Category lines don't start with status icons
            if check_text and not (check_text.startswith("✓") or check_text.startswith("○") or check_text.startswith("↑")):
                if current_category is None or check_text != current_category:
                    return check_text
            check_line -= 1
        return None
    
    def _find_category_below(self, line_num):
        """Find category header below given line."""
        try:
            max_line = int(self.mod_listbox.index('end-1c').split('.')[0])
        except (tk.TclError, ValueError):
            max_line = 1
        
        check_line = line_num + 1
        while check_line <= max_line:
            check_text = self.mod_listbox.get(f"{check_line}.0", f"{check_line}.end").strip()
            # Category lines don't start with status icons
            if check_text and not (check_text.startswith("✓") or check_text.startswith("○") or check_text.startswith("↑")):
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
    
    def edit_modlist_metadata(self):
        """Open dialog to edit modlist metadata (name, version, description, etc.)."""
        if not self.modlist_data:
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Modlist Metadata")
        dialog.geometry("500x400")
        dialog.configure(bg=TriOSTheme.SURFACE)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Title
        tk.Label(dialog, text="Modlist Metadata", font=("Arial", 14, "bold"),
                bg=TriOSTheme.SURFACE, fg=TriOSTheme.PRIMARY).pack(pady=(15, 20))
        
        # Form frame
        form_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        # Fields
        fields = [
            ("Modlist Name:", "modlist_name", self.modlist_data.get("modlist_name", "")),
            ("Version:", "version", self.modlist_data.get("version", "")),
            ("Starsector Version:", "starsector_version", self.modlist_data.get("starsector_version", "")),
            ("Author:", "author", self.modlist_data.get("author", "")),
        ]
        
        entries = {}
        for i, (label_text, key, value) in enumerate(fields):
            tk.Label(form_frame, text=label_text, font=("Arial", 10),
                    bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY,
                    anchor=tk.W).grid(row=i, column=0, sticky="w", pady=5)
            
            entry = tk.Entry(form_frame, font=("Arial", 10),
                           bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                           insertbackground=TriOSTheme.PRIMARY)
            entry.insert(0, value)
            entry.grid(row=i, column=1, sticky="ew", pady=5, padx=(10, 0))
            entries[key] = entry
        
        form_frame.columnconfigure(1, weight=1)
        
        # Description field (multi-line)
        tk.Label(form_frame, text="Description:", font=("Arial", 10),
                bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY,
                anchor=tk.W).grid(row=len(fields), column=0, sticky="nw", pady=5)
        
        desc_text = tk.Text(form_frame, font=("Arial", 10), height=6,
                          bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                          insertbackground=TriOSTheme.PRIMARY, wrap=tk.WORD)
        desc_text.insert("1.0", self.modlist_data.get("description", ""))
        desc_text.grid(row=len(fields), column=1, sticky="ew", pady=5, padx=(10, 0))
        entries['description'] = desc_text
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        def save_metadata():
            """Save the edited metadata."""
            self.modlist_data["modlist_name"] = entries["modlist_name"].get().strip()
            self.modlist_data["version"] = entries["version"].get().strip()
            self.modlist_data["starsector_version"] = entries["starsector_version"].get().strip()
            self.modlist_data["author"] = entries["author"].get().strip()
            self.modlist_data["description"] = desc_text.get("1.0", tk.END).strip()
            
            self.save_modlist_config()
            self.display_modlist_info()
            self.log("Modlist metadata updated")
            dialog.destroy()
            custom_dialogs.showsuccess("Success", "Modlist metadata has been updated.")
        
        from .ui_builder import _create_button
        
        save_btn = _create_button(button_frame, "Save", save_metadata, width=12, button_type="success")
        save_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        cancel_btn = _create_button(button_frame, "Cancel", dialog.destroy, width=12, button_type="secondary")
        cancel_btn.pack(side=tk.LEFT)
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    
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
        
        # Configure category and selection tags (TriOS theme colors)
        self.mod_listbox.tag_configure('category', background=TriOSTheme.CATEGORY_BG, 
            foreground=TriOSTheme.CATEGORY_FG, justify='center')
        self.mod_listbox.tag_configure('selected', background=TriOSTheme.ITEM_SELECTED_BG, 
            foreground=TriOSTheme.ITEM_SELECTED_FG)
        
        # Configure tags for installed/not installed mods
        self.mod_listbox.tag_configure('installed', foreground=TriOSTheme.SUCCESS)
        self.mod_listbox.tag_configure('not_installed', foreground=TriOSTheme.TEXT_SECONDARY)
        self.mod_listbox.tag_configure('outdated', foreground='#e67e22')  # Orange for update available
        
        # Group mods by category
        mods = self.modlist_data.get('mods', [])
        
        # Apply search filter if active
        if self.search_filter:
            mods = [m for m in mods if self.search_filter in m.get('name', '').lower()]
        
        categories = {}
        for mod in mods:
            cat = mod.get('category', 'Uncategorized')
            categories.setdefault(cat, []).append(mod)
        
        # Check installation status
        starsector_path = self.starsector_path.get()
        mods_dir = Path(starsector_path) / "mods" if starsector_path else None
        
        # Display all categories (even empty ones)
        for cat in self.categories:
            self.mod_listbox.insert(tk.END, f"{cat}\n", 'category')
            
            # Display mods in this category (if any)
            if cat in categories:
                for mod in categories[cat]:
                    # Check if mod is installed
                    is_installed = False
                    if mods_dir and mods_dir.exists():
                        is_installed = self.mod_installer.is_mod_already_installed(mod, mods_dir)
                    
                    # Choose icon based on installation status
                    icon = "✓" if is_installed else "○"
                    tag = 'installed' if is_installed else 'not_installed'
                    
                    self.mod_listbox.insert(tk.END, f"  {icon} {mod['name']}\n", ('mod', tag))
        
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
            line_stripped = line_text.strip()
            # Check if it's a mod line (starts with ✓, ○, or ↑)
            if (line_stripped.startswith("✓") or line_stripped.startswith("○") or line_stripped.startswith("↑")) and mod_name in line_text:
                self.selected_mod_line = line_num
                self.highlight_selected_mod()
                return
        
        self.selected_mod_line = None
    
    # ============================================
    # Utility Methods
    # ============================================
    
    def _get_mod_game_version(self, mod):
        """Get game_version from mod dict, handling legacy 'version' field.
        
        Args:
            mod: Mod dictionary
            
        Returns:
            str: Game version or empty string
        """
        return mod.get('game_version') or mod.get('version') or ''
    
    def _extract_mod_name_from_line(self, line_text):
        """Extract mod name from a listbox line."""
        line = line_text.strip()
        # Check if it's a mod line (starts with ✓, ○, or ↑)
        if not (line.startswith("✓") or line.startswith("○") or line.startswith("↑")):
            return None
        # Remove icon prefix and extract name (before version if present)
        name_part = line_text.replace("  ✓ ", "").replace("  ○ ", "").replace("  ↑ ", "")
        return name_part.split(" v")[0].strip()
    
    def _find_mod_by_name(self, mod_name):
        """Find a mod dict by name using exact match or normalized matching.
        
        Args:
            mod_name: Name to search for
            
        Returns:
            dict: Mod dictionary or None if not found
        """
        mods = self.modlist_data.get('mods', [])
        
        # First try exact match (fastest)
        exact_match = next((m for m in mods if m.get('name') == mod_name), None)
        if exact_match:
            return exact_match
        
        # Try normalized matching as fallback
        normalized_search = normalize_mod_name(mod_name)
        for mod in mods:
            mod_config_name = mod.get('name', '')
            if normalize_mod_name(mod_config_name) == normalized_search:
                return mod
        
        return None
    
    def log(self, message, error=False, info=False, warning=False, debug=False, success=False):
        """Append a message to the log with different severity levels.
        
        Args:
            message: Message to log
            error: If True, display in red (for errors)
            info: If True, display in blue (for informational messages)
            warning: If True, display in orange (for warnings)
            debug: If True, display in gray (for debug messages)
            success: If True, display in green (for success messages)
        """
        # Filter debug messages if log level is not DEBUG
        if debug and self.log_level != 'DEBUG':
            return
        
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self.log(message, error=error, info=info, warning=warning, debug=debug, success=success))
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
        
        # Configure tag colors for different log levels (TriOS theme)
        if error:
            tag = "error"
            self.log_text.tag_config("error", foreground=TriOSTheme.LOG_ERROR)
        elif warning:
            tag = "warning"
            self.log_text.tag_config("warning", foreground=TriOSTheme.LOG_WARNING)
        elif success:
            tag = "success"
            self.log_text.tag_config("success", foreground=TriOSTheme.LOG_SUCCESS)
        elif info:
            tag = "info"
            self.log_text.tag_config("info", foreground=TriOSTheme.LOG_INFO)
        elif debug:
            tag = "debug"
            self.log_text.tag_config("debug", foreground=TriOSTheme.LOG_DEBUG)
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
        """Auto-detect Starsector installation using StarsectorPathValidator."""
        # Only auto-detect if path is not already set
        if self.starsector_path.get():
            self._auto_detected = False
            return
        
        detected_path = StarsectorPathValidator.auto_detect()
        if detected_path:
            self.starsector_path.set(str(detected_path))
            self._auto_detected = True
            self.log(f"✓ Auto-detected Starsector installation: {detected_path}", info=True)
        else:
            self._auto_detected = False
            self.log("⚠ Could not auto-detect Starsector. Please set path manually.", warning=True)
    
    def validate_starsector_path(self, path_str):
        """Validate Starsector installation path."""
        if not path_str:
            return False, "Path is empty"
        
        path = Path(path_str)
        if StarsectorPathValidator.validate(path):
            return True, "Valid"
        else:
            friendly_msg = get_user_friendly_error('invalid_path')
            return False, friendly_msg
    
    def check_disk_space(self, required_gb=MIN_FREE_SPACE_GB):
        """Check if there's enough free disk space."""
        if not self.starsector_path.get():
            return True, ""
        
        has_space, free_gb = StarsectorPathValidator.check_disk_space(
            Path(self.starsector_path.get()), required_gb
        )
        
        if not has_space:
            friendly_msg = get_user_friendly_error('disk_space')
            return False, friendly_msg
        return True, f"{free_gb:.1f}GB free"
    
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
        """Toggle pause/resume during installation."""
        if not self.is_installing:
            return
        
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.log("Installation paused", warning=True)
            self.pause_install_btn.config(text="▶")
            # Update tooltip dynamically
            from .ui_builder import ToolTip
            # Clear existing tooltip bindings
            try:
                self.pause_install_btn.unbind("<Enter>")
                self.pause_install_btn.unbind("<Leave>")
            except:
                pass
            ToolTip(self.pause_install_btn, "Resume installation")
        else:
            self.log("Installation resumed", info=True)
            self.pause_install_btn.config(text="⏸")
            # Update tooltip dynamically
            from .ui_builder import ToolTip
            # Clear existing tooltip bindings
            try:
                self.pause_install_btn.unbind("<Enter>")
                self.pause_install_btn.unbind("<Leave>")
            except:
                pass
            ToolTip(self.pause_install_btn, "Pause installation")
            self.log("Installation resumed")
    
    def refresh_mod_metadata(self):
        """Manually refresh mod metadata from installed mods without full installation."""
        starsector_dir = self.starsector_path.get()
        
        if not starsector_dir:
            custom_dialogs.showerror("Error", "Starsector path not set. Please configure it in settings.")
            return
        
        mods_dir = Path(starsector_dir) / "mods"
        
        if not mods_dir.exists():
            custom_dialogs.showerror("Error", f"Mods directory not found: {mods_dir}")
            return
        
        # Disable button during refresh
        if self.refresh_btn:
            self.refresh_btn.config(state=tk.DISABLED, text="↻")
        
        self.log("=" * 50)
        self.log("Refreshing mod metadata from installed mods...")
        self.log("Reloading modlist configuration...")
        
        try:
            # Reload modlist configuration from file
            self.modlist_data = self.config_manager.load_modlist_config()
            
            # Update mod metadata from installed mods
            self._update_mod_metadata_from_installed(mods_dir)
            self.save_modlist_config()
            self.display_modlist_info()
            self.log("✓ Metadata refresh complete!")
            custom_dialogs.showsuccess("Success", "Mod metadata has been refreshed from installed mods")
        except Exception as e:
            self.log(f"✗ Error refreshing metadata: {e}", error=True)
            custom_dialogs.showerror("Error", f"Failed to refresh metadata: {e}")
        finally:
            # Re-enable button
            if self.refresh_btn:
                self.refresh_btn.config(state=tk.NORMAL, text="↻")
    
    def enable_all_installed_mods(self):
        """Enable all currently installed mods in Starsector by updating enabled_mods.json."""
        starsector_dir = self.starsector_path.get()
        
        if not starsector_dir:
            custom_dialogs.showerror("Error", "Starsector path not set. Please configure it in settings.")
            return
        
        mods_dir = Path(starsector_dir) / "mods"
        
        if not mods_dir.exists():
            custom_dialogs.showerror("Error", f"Mods directory not found: {mods_dir}")
            return
        
        self.log("=" * 50)
        self.log("Enabling all installed mods...")
        
        try:
            # Scan all installed mods
            all_installed_folders = []
            for folder, metadata in scan_installed_mods(mods_dir):
                all_installed_folders.append(folder.name)
                self.log(f"  Found: {folder.name}", debug=True)
            
            if not all_installed_folders:
                custom_dialogs.showwarning("No Mods Found", "No mods were found in the mods directory.")
                return
            
            # Update enabled_mods.json with all installed mods
            success = self.mod_installer.update_enabled_mods(mods_dir, all_installed_folders, merge=False)
            
            if success:
                self.log(f"✓ Enabled {len(all_installed_folders)} mod(s) in enabled_mods.json")
                custom_dialogs.showsuccess("Success", f"Successfully enabled {len(all_installed_folders)} mod(s).\n\nYour mods should now be active when you start Starsector.")
            else:
                custom_dialogs.showerror("Error", "Failed to update enabled_mods.json")
        except Exception as e:
            self.log(f"✗ Error enabling mods: {e}", error=True)
            custom_dialogs.showerror("Error", f"Failed to enable mods: {e}")
    
    def restore_backup_dialog(self):
        """Show dialog to restore a backup."""
        starsector_dir = self.starsector_path.get()
        if not starsector_dir:
            custom_dialogs.showerror("Error", "Starsector path not set. Please configure it in settings.")
            return
        
        try:
            backup_manager = BackupManager(starsector_dir)
            backups = backup_manager.list_backups()
            
            if not backups:
                custom_dialogs.showinfo("No Backups", "No backups found. Backups are created automatically before installation.")
                return
            
            # Create simple list dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Restore Backup")
            dialog.geometry("500x400")
            dialog.configure(bg=TriOSTheme.SURFACE)
            dialog.transient(self.root)
            dialog.grab_set()
            
            tk.Label(dialog, text="Select a backup to restore:", font=("Arial", 12), 
                    bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).pack(pady=10)
            
            # Listbox with scrollbar
            frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                                bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                                selectbackground=TriOSTheme.PRIMARY, selectforeground=TriOSTheme.SURFACE_DARK,
                                font=("Arial", 10))
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Populate list
            for backup_path, metadata in backups:
                timestamp = metadata.get('timestamp', 'Unknown')
                # Format timestamp
                try:
                    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                    formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    formatted = timestamp
                listbox.insert(tk.END, formatted)
            
            selected_backup = [None]
            
            def on_restore():
                selection = listbox.curselection()
                if not selection:
                    custom_dialogs.showwarning("No Selection", "Please select a backup to restore.")
                    return
                
                idx = selection[0]
                backup_path, metadata = backups[idx]
                
                # Confirm restore
                timestamp = metadata.get('timestamp', 'Unknown')
                if not custom_dialogs.askyesno("Confirm Restore", f"Restore backup from {timestamp}?\n\nThis will replace your current enabled_mods.json file."):
                    return
                
                # Perform restore
                success, error = backup_manager.restore_backup(backup_path)
                if success:
                    self.log(f"✓ Backup restored from {timestamp}")
                    custom_dialogs.showsuccess("Success", "Backup restored successfully!\n\nYour mod configuration has been restored.")
                    dialog.destroy()
                else:
                    custom_dialogs.showerror("Restore Failed", f"Failed to restore backup:\n{error}")
            
            def on_delete():
                selection = listbox.curselection()
                if not selection:
                    custom_dialogs.showwarning("No Selection", "Please select a backup to delete.")
                    return
                
                idx = selection[0]
                backup_path, metadata = backups[idx]
                timestamp = metadata.get('timestamp', 'Unknown')
                
                if not custom_dialogs.askyesno("Confirm Delete", f"Delete backup from {timestamp}?"):
                    return
                
                success, error = backup_manager.delete_backup(backup_path)
                if success:
                    self.log(f"✓ Deleted backup: {timestamp}")
                    listbox.delete(idx)
                    backups.pop(idx)
                    if not backups:
                        custom_dialogs.showinfo("No Backups", "All backups deleted.")
                        dialog.destroy()
                else:
                    custom_dialogs.showerror("Delete Failed", f"Failed to delete backup:\n{error}")
            
            # Buttons
            btn_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
            btn_frame.pack(pady=10)
            
            from .ui_builder import _create_button
            restore_btn = _create_button(btn_frame, "Restore", on_restore, button_type="success")
            restore_btn.pack(side=tk.LEFT, padx=5)
            
            delete_btn = _create_button(btn_frame, "Delete", on_delete, button_type="danger")
            delete_btn.pack(side=tk.LEFT, padx=5)
            
            cancel_btn = _create_button(btn_frame, "Cancel", dialog.destroy, button_type="plain")
            cancel_btn.pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            self.log(f"✗ Error accessing backups: {e}", error=True)
            custom_dialogs.showerror("Error", f"Failed to access backups:\n{e}")
    
    def _run_pre_installation_checks(self, starsector_dir):
        """Run comprehensive pre-installation checks.
        
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        mods_dir = starsector_dir / "mods"
        
        # 1. Check disk space
        has_space, space_msg = self.check_disk_space()
        if not has_space:
            self.log(space_msg, warning=True)
            if not custom_dialogs.askyesno("Low Disk Space", f"{space_msg}\n\nContinue anyway?"):
                return False, "Installation cancelled due to low disk space"
        
        # 2. Check write permissions
        try:
            test_file = mods_dir / ".write_test"
            mods_dir.mkdir(exist_ok=True)
            test_file.write_text("test")
            test_file.unlink()
            self.log("✓ Write permissions verified", debug=True)
        except (PermissionError, OSError) as e:
            friendly_msg = get_user_friendly_error('permission_denied')
            return False, f"{friendly_msg}\n\nTechnical: {e}"
        
        # 3. Check internet connection (quick test)
        try:
            import socket
            socket.create_connection(("www.google.com", 80), timeout=3)
            self.log("✓ Internet connection verified", debug=True)
        except (socket.error, socket.timeout):
            self.log("⚠ Internet connection may be unavailable", warning=True)
            if not custom_dialogs.askyesno("Connection Warning", "Could not verify internet connection.\n\nContinue anyway?"):
                return False, "Installation cancelled due to connection issues"
        
        # 4. Check for potential version conflicts (basic check)
        starsector_version = self.modlist_data.get('starsector_version', 'Unknown')
        
        # 6. Check dependencies
        dependency_issues = self._check_dependencies(mods_dir)
        if dependency_issues:
            issues_text = "\n".join([f"  • {mod_name}: missing {', '.join(deps)}" 
                                     for mod_name, deps in dependency_issues.items()])
            self.log(f"⚠ Dependency issues found:\n{issues_text}", warning=True)
            
            message = f"Some mods have missing dependencies:\n\n{issues_text}\n\nThese dependencies will be installed if they're in the modlist.\n\nContinue?"
            if not custom_dialogs.askyesno("Missing Dependencies", message):
                return False, "Installation cancelled due to missing dependencies"
        else:
            self.log("✓ No dependency issues found", debug=True)
        
        return True, None
    
    def _check_dependencies(self, mods_dir):
        """Check for missing dependencies in the modlist.
        
        Args:
            mods_dir: Path to mods directory
            
        Returns:
            dict: {mod_name: [list of missing dependency IDs]}
        """
        from utils.mod_utils import extract_dependencies_from_text, check_missing_dependencies
        
        # First, extract dependencies from modlist mods
        for mod in self.modlist_data.get('mods', []):
            mod_id = mod.get('mod_id')
            if not mod_id:
                continue
            
            # If dependencies not already in mod data, we'll check installed mods later
            if 'dependencies' not in mod:
                mod['dependencies'] = []
        
        # Get installed mod IDs
        installed_mod_ids = set()
        for folder, metadata in scan_installed_mods(mods_dir):
            mod_id = metadata.get('id')
            if mod_id:
                installed_mod_ids.add(mod_id)
        
        # Add modlist mod IDs (they will be installed)
        modlist_mod_ids = {m.get('mod_id') for m in self.modlist_data.get('mods', []) if m.get('mod_id')}
        all_available_ids = installed_mod_ids | modlist_mod_ids
        
        # Check for missing dependencies
        missing_deps_by_id = check_missing_dependencies(self.modlist_data.get('mods', []), all_available_ids)
        
        # Convert to user-friendly format (mod name instead of ID)
        dependency_issues = {}
        for mod_id, missing_deps in missing_deps_by_id.items():
            # Find mod name
            mod = next((m for m in self.modlist_data.get('mods', []) if m.get('mod_id') == mod_id), None)
            if mod:
                mod_name = mod.get('name', mod_id)
                dependency_issues[mod_name] = missing_deps
        
        return dependency_issues
    
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
        
        if not self.modlist_data:
            custom_dialogs.showerror("Error", "No modlist configuration loaded")
            return
        
        # Run comprehensive pre-installation checks
        self.log("\n" + "─" * 60)
        self.log("Running pre-installation checks...")
        check_success, check_error = self._run_pre_installation_checks(starsector_dir)
        if not check_success:
            custom_dialogs.showerror("Pre-Installation Check Failed", check_error)
            return
        self.log("✓ All pre-installation checks passed")
        
        # Validate URLs asynchronously
        self.log("Validating mod URLs (this may take a moment)...")
        self.install_modlist_btn.config(text="Validating URLs...")
        
        # _validate_urls_async now handles the rest asynchronously
        self._validate_urls_async()
    
    def _continue_installation_after_validation(self, results):
        """Continue installation after URL validation completes."""
        if not results:
            return
        
        # Show validation summary and check if user wants to continue
        if not self._show_validation_summary(results):
            return
        
        # Get starsector directory again
        starsector_dir = Path(self.starsector_path.get())
        
        # Check for outdated mods before installation
        mods_dir = starsector_dir / "mods"
        if mods_dir.exists():
            self.log("\nChecking for outdated mods...")
            outdated = self.mod_installer.detect_outdated_mods(mods_dir, self.modlist_data['mods'])
            
            if outdated:
                self.log(f"\n⚠ Found {len(outdated)} outdated mod(s):", warning=True)
                for mod_info in outdated:
                    self.log(f"  • {mod_info['name']}: v{mod_info['installed_version']} → v{mod_info['expected_version']}", warning=True)
                
                # Ask user if they want to update
                msg = f"{len(outdated)} mod(s) will be updated:\n\n"
                for mod_info in outdated[:5]:  # Show max 5 in dialog
                    msg += f"• {mod_info['name']}: v{mod_info['installed_version']} → v{mod_info['expected_version']}\n"
                if len(outdated) > 5:
                    msg += f"... +{len(outdated) - 5} more\n"
                
                custom_dialogs.showinfo("Outdated Mods", msg)
        else:
            self.log(f"\nMods directory not found at {mods_dir}, skipping version checks", debug=True)
        
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
        
        # Wait with periodic UI updates (using after instead of update to prevent blocking)
        max_wait = 60
        start_time = time.time()
        
        def check_validation_status():
            if validation_result['error']:
                custom_dialogs.showerror("Validation Error", f"Failed to validate URLs: {validation_result['error']}")
                self.install_modlist_btn.config(text="Install Modlist")
                return
            
            if validation_result['data']:
                # Validation complete
                self.install_modlist_btn.config(text="Install Modlist")
                self._continue_installation_after_validation(validation_result['data'])
                return
            
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                custom_dialogs.showerror("Validation Timeout", "URL validation took too long. Try again or check your internet connection.")
                self.install_modlist_btn.config(text="Install Modlist")
                return
            
            # Check again in 100ms
            self.root.after(100, check_validation_status)
        
        # Start checking
        self.root.after(100, check_validation_status)
        return None  # Will be handled asynchronously
    
    def _show_validation_summary(self, results):
        """Show validation results summary and prompt user to continue.
        
        Returns:
            bool: True if user wants to continue, False otherwise
        """
        github_mods = results['github']
        gdrive_mods = results['google_drive']
        other_domains = results['other']
        failed_list = results['failed']
        
        total_other = sum(len(mods) for mods in other_domains.values())
        self.log(f"GitHub: {len(github_mods)}, Google Drive: {len(gdrive_mods)}, Other: {total_other}, Failed: {len(failed_list)}")
        
        if github_mods or gdrive_mods or other_domains or failed_list:
            action = custom_dialogs.show_validation_report(
                self.root,
                github_mods,
                gdrive_mods,
                other_domains,
                failed_list
            )
            
            if action == 'cancel':
                self.log("Installation cancelled by user")
                return False
        
        return True
    
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
        """Download mods in parallel. Delegates to InstallationController."""
        return self.installation_controller.download_mods_parallel(mods_to_download, skip_gdrive_check, max_workers)

    def _install_mods_internal(self, mods_to_install, skip_gdrive_check=False):
        """Internal method to install a list of mods. Delegates to InstallationController."""
        return self.installation_controller.install_mods_internal(mods_to_install, skip_gdrive_check)
    
    def _finalize_installation_cancelled(self):
        """Cleanup and reset UI after installation cancellation. Delegates to InstallationController."""
        return self.installation_controller.finalize_installation_cancelled()
    
    def _extract_downloaded_mods(self, download_results, mods_dir):
        """Extract all downloaded mods sequentially. Delegates to InstallationController."""
        report = InstallationReport()
        return self.installation_controller.extract_downloaded_mods_with_report(download_results, mods_dir, report)
    
    def _extract_downloaded_mods_with_report(self, download_results, mods_dir, report):
        """Extract all downloaded mods sequentially. Delegates to InstallationController."""
        return self.installation_controller.extract_downloaded_mods_with_report(download_results, mods_dir, report)
    
    def _cleanup_remaining_downloads(self, download_results, start_index):
        """Clean up unprocessed downloaded files. Delegates to InstallationController."""
        return self.installation_controller.cleanup_remaining_downloads(download_results, start_index)
    
    def _auto_detect_game_version(self, mod, temp_path, is_7z):
        """Auto-detect and update game_version and mod_version. Delegates to InstallationController."""
        return self.installation_controller.auto_detect_game_version(mod, temp_path, is_7z)
    
    def _update_mod_metadata_from_installed(self, mods_dir):
        """Auto-detect and update mod metadata from installed mods. Delegates to InstallationController."""
        return self.installation_controller.update_mod_metadata_from_installed(mods_dir)
    
    def _finalize_installation_with_report(self, report, mods_dir, download_results, total_mods,
                                           gdrive_failed=None, extraction_failures=None):
        """Finalize installation with InstallationReport. Delegates to InstallationController."""
        return self.installation_controller.finalize_installation_with_report(
            report, mods_dir, download_results, total_mods, gdrive_failed, extraction_failures
        )
    
    def _show_installation_complete_message(self):
        """Display the installation complete banner (used for Google Drive cancellation)."""
        self.log("\n✓ Installation workflow complete.", success=True)

    def _propose_fix_google_drive_urls(self, failed_mods):
        """Propose to fix Google Drive URLs after installation is complete.
        
        Args:
            failed_mods: List of mod dictionaries that failed to download
        """
        def on_confirm(mods_to_download):
            # Log fixed URLs
            for mod, original_mod in zip(mods_to_download, failed_mods):
                if mod['download_url'] != original_mod['download_url']:
                    self.log(f"🔧 Fixed Google Drive URL: {mod.get('name')}", info=True)
            
            # Start download with fixed URLs
            self.install_specific_mods(
                [mod['name'] for mod in mods_to_download],
                temp_mods=mods_to_download,
                skip_gdrive_check=True
            )
        
        def on_cancel():
            # Show installation complete message when user cancels
            self._show_installation_complete_message()
        
        # Show the dialog in the main thread to avoid TclError
        def show_dialog():
            try:
                show_google_drive_confirmation_dialog(
                    self.root,
                    failed_mods,
                    on_confirm,
                    on_cancel
                )
            except tk.TclError:
                # Window was destroyed, just complete installation
                self._show_installation_complete_message()
        
        # Schedule dialog display in main thread
        self.root.after(0, show_dialog)


