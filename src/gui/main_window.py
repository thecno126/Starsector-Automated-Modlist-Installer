import tkinter as tk
from tkinter import filedialog, ttk
import re
from . import dialogs as custom_dialogs
from pathlib import Path
import threading
import concurrent.futures
from datetime import datetime
import os
import shutil
import time

from core import (
    LOG_FILE,
    URL_VALIDATION_TIMEOUT_HEAD, MIN_FREE_SPACE_GB,
    MAX_DOWNLOAD_WORKERS,
    UI_MIN_WINDOW_WIDTH, UI_MIN_WINDOW_HEIGHT,
    UI_DEFAULT_WINDOW_WIDTH, UI_DEFAULT_WINDOW_HEIGHT,
    ModInstaller, ConfigManager, InstallationReport
)
from utils.mod_utils import is_mod_up_to_date, resolve_mod_dependencies
from utils.network_utils import validate_mod_urls
from .dialogs import (
    open_add_mod_dialog,
    open_manage_categories_dialog,
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
from utils.theme import AppTheme
from utils.mod_utils import (
    normalize_mod_name,
    is_mod_name_match,
    scan_installed_mods,
    check_missing_dependencies,
    refresh_mod_metadata,
    enable_all_installed_mods,
    enable_modlist_mods,
    check_mod_dependencies
)
from utils.validators import StarsectorPathValidator, URLValidator
from utils.error_messages import get_user_friendly_error
from utils import installation_checks
from utils import listbox_helpers
from utils.category_navigator import CategoryNavigator
from utils.symbols import LogSymbols, UISymbols



class ModlistInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("Starsector Automated Modlist Installer")
        self.root.geometry(f"{UI_DEFAULT_WINDOW_WIDTH}x{UI_DEFAULT_WINDOW_HEIGHT}")
        self.root.resizable(True, True)
        self.root.minsize(UI_MIN_WINDOW_WIDTH, UI_MIN_WINDOW_HEIGHT)
        
        self.root.configure(bg=AppTheme.SURFACE_DARK)
        self.style = ttk.Style()
        AppTheme.configure_ttk_styles(self.style)
        
        self.config_manager = ConfigManager()
        
        self.modlist_data = None
        self.categories = self.config_manager.load_categories()
        
        self.starsector_path = tk.StringVar()
        self.is_installing = False
        self.is_paused = False
        self.download_futures = []
        self.current_executor = None
        self.downloaded_temp_files = []
        self.current_mod_name = tk.StringVar(value="")
        self.url_validator = URLValidator()
        
        self.mod_installer = ModInstaller(self.log)
        self.installation_controller = None
        self.log_level = 'INFO'
        self.backup_manager = None  # Initialized after starsector_path is set
        
        self.load_preferences()
        self.create_ui()
        self.auto_detect_starsector()
        
        self.category_navigator = CategoryNavigator(self.mod_listbox)
        self.installation_controller = InstallationController(self)
        self.modlist_data = self.config_manager.load_modlist_config()
        self.display_modlist_info()
        
        self.root.bind('<Configure>', self.on_window_resize)
        self._resize_after_id = None
        self.root.protocol("WM_DELETE_WINDOW", self.safe_quit)
        
        self.root.bind('<Control-q>', lambda e: self.root.destroy())
        self.root.bind('<Control-s>', lambda e: self.save_modlist_config(log_message=True))
        self.root.bind('<Control-a>', lambda e: self.open_add_mod_dialog())
        
        self.drag_start_line = None
        self.drag_start_y = None
        self._setup_drag_and_drop()
    
    def _setup_drag_and_drop(self):
        self.mod_listbox.bind('<Button-1>', self._on_drag_start, add="+")
        self.mod_listbox.bind('<B1-Motion>', self._on_drag_motion)
        self.mod_listbox.bind('<ButtonRelease-1>', self._on_drag_end, add="+")
    
    def _is_mod_line(self, line_text):
        """Check if line is a mod (not category).
        
        Args:
            line_text: Text from listbox line
            
        Returns:
            bool: True if line is mod line (starts with icon)
        """
        line_stripped = line_text.strip()
        return line_stripped and line_stripped.startswith((LogSymbols.INSTALLED, LogSymbols.NOT_INSTALLED, LogSymbols.UPDATED))
    
    def _calculate_drop_position(self, category_start_line, target_line):
        """Calculate position in category for drop target.
        
        Args:
            category_start_line: Line number of category header
            target_line: Line number of drop target
            
        Returns:
            int: Position in category (0-indexed)
        """
        position = 0
        for line_num in range(category_start_line + 1, target_line + 1):
            line_text = self.mod_listbox.get(f"{line_num}.0", f"{line_num}.end")
            if self._is_mod_line(line_text):
                position += 1
        return position
    
    def _on_drag_start(self, event):
        index = self.mod_listbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        line_text = self.mod_listbox.get(f"{line_num}.0", f"{line_num}.end")
        
        if self._is_mod_line(line_text):
            self.drag_start_line = line_num
            self.drag_start_y = event.y
        else:
            self.drag_start_line = None
    
    def _on_drag_motion(self, event):
        if self.drag_start_line is None:
            return
        pass
    
    def _on_drag_end(self, event):
        if self.drag_start_line is None:
            return
        
        try:
            index = self.mod_listbox.index(f"@{event.x},{event.y}")
            target_line = int(index.split('.')[0])
            
            if abs(target_line - self.drag_start_line) < 1:
                self.drag_start_line = None
                return
            
            source_text = self.mod_listbox.get(f"{self.drag_start_line}.0", f"{self.drag_start_line}.end")
            source_mod_name = self._extract_mod_name_from_line(source_text)
            
            if not source_mod_name:
                self.drag_start_line = None
                return
            
            source_mod = self._find_mod_by_name(source_mod_name)
            if not source_mod:
                self.drag_start_line = None
                return
            
            target_category = self._find_category_above(target_line)
            if not target_category:
                self.drag_start_line = None
                return
            
            category_start_line = self._find_category_line(target_category)
            if category_start_line is None:
                self.drag_start_line = None
                return
            
            position = self._calculate_drop_position(category_start_line, target_line)
            self._move_mod_to_category_position(source_mod_name, source_mod, target_category, position)
            
        except Exception as e:
            self.log(f"Drag and drop error: {e}", debug=True)
        finally:
            self.drag_start_line = None
    
    def _find_category_line(self, category_name):
        """Find line number of category header."""
        return self.category_navigator.find_category_line(category_name)
    
    def _move_mod_to_category_position(self, mod_name, mod, target_category, position):
        """Move mod to specific position in target category with safety checks."""
        if not mod or not mod_name:
            self.log(f"{LogSymbols.ERROR} Cannot move mod: invalid mod data", debug=True)
            return
        
        if target_category not in self.categories:
            self.log(f"{LogSymbols.ERROR} Cannot move mod to non-existent category: {target_category}", debug=True)
            return
        
        # Remove mod from current position
        mods = self.modlist_data.get('mods', [])
        mods = [m for m in mods if m.get('name') != mod_name]
        
        # Update mod category
        mod['category'] = target_category
        
        # Group remaining mods by category in order
        grouped = {}
        for cat in self.categories:
            grouped[cat] = [m for m in mods if m.get('category', 'Uncategorized') == cat]
        
        # Insert mod at specified position in target category
        target_mods = grouped.get(target_category, [])
        position = max(0, min(position, len(target_mods)))
        target_mods.insert(position, mod)
        grouped[target_category] = target_mods
        
        # Rebuild global mods list maintaining category order
        self.modlist_data['mods'] = []
        for category in self.categories:
            if category in grouped:
                self.modlist_data['mods'].extend(grouped[category])
        
        self.save_modlist_config()
        self.display_modlist_info()
        self.log(f"{LogSymbols.SUCCESS} Moved '{mod_name}' to {target_category} (position {position})", debug=True)
    
    def _configure_mod_action_buttons(self, mod_action_buttons):
        """Configure mod action buttons (add, edit, remove, categories).
        
        Args:
            mod_action_buttons: Dictionary of button widgets
        """
        if not mod_action_buttons:
            return
        
        mod_action_buttons['add'].config(command=self.open_add_mod_dialog)
        mod_action_buttons['edit'].config(command=self.edit_selected_mod)
        mod_action_buttons['remove'].config(command=self.remove_selected_mod)
        mod_action_buttons['categories'].config(command=self.open_manage_categories_dialog)
        
        self.add_btn = mod_action_buttons['add']
        self.edit_btn = mod_action_buttons['edit']
        self.remove_btn = mod_action_buttons['remove']
        self.categories_btn = mod_action_buttons['categories']
    
    def _configure_header_buttons(self, header_buttons):
        """Configure header buttons (import, export, refresh, etc.).
        
        Args:
            header_buttons: Dictionary of button widgets
        """
        if not header_buttons:
            return
        
        self.import_btn = header_buttons.get('import')
        self.export_btn = header_buttons.get('export')
        self.refresh_btn = header_buttons.get('refresh')
        self.clear_all_btn = header_buttons.get('clear')
        self.edit_metadata_btn = header_buttons.get('edit_metadata')
        self.up_btn = header_buttons.get('up')
        self.down_btn = header_buttons.get('down')
        
        if self.up_btn:
            self.up_btn.config(command=self.move_mod_up)
        if self.down_btn:
            self.down_btn.config(command=self.move_mod_down)
    
    def create_ui(self):
        create_header(self.root)
        
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=12, sashpad=8, sashrelief=tk.RAISED,
                           bg=AppTheme.SURFACE)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        left_frame = tk.Frame(main_container, bg=AppTheme.SURFACE)
        left_frame.pack_configure(padx=10, pady=10)
        main_container.add(left_frame, minsize=550, stretch="always")
        
        path_frame, self.path_entry, self.browse_btn, self.path_status_label = create_path_section(
            left_frame, self.starsector_path, self.select_starsector_path
        )
        # Bind validation when user manually edits path
        self.starsector_path.trace_add('write', lambda *args: self.on_path_changed())
        self.update_path_status()
        
        # Create bottom buttons FIRST (before expandable sections) to ensure they stay visible
        button_frame, self.install_modlist_btn, self.quit_btn = create_bottom_buttons(
            left_frame,
            self.start_installation,
            self.safe_quit
        )
        
        info_frame, left_container, self.header_text, self.mod_listbox, self.search_var, mod_action_buttons, header_buttons, self.modlist_title_var = create_modlist_section(
            left_frame,
            self.on_mod_click,
            lambda e: None,  # No resize callback needed anymore
            self.on_search_mods,
            None,  # import_callback removed (CSV deprecated)
            None,  # export_callback removed (CSV deprecated)
            self.refresh_mod_metadata,
            self.open_export_preset_dialog,
            self.reset_modlist_config,
            self.edit_modlist_metadata,
            self.open_import_preset_dialog,
            self.open_patch_lunalib_dialog
        )
        
        self.selected_mod_line = None
        self.search_filter = ""
        
        self._configure_mod_action_buttons(mod_action_buttons)
        self._configure_header_buttons(header_buttons)
        
        right_frame = tk.Frame(main_container, bg=AppTheme.SURFACE)
        right_frame.pack_configure(padx=10, pady=10)
        main_container.add(right_frame, minsize=700, stretch="always")
        
        # Create enable mods button FIRST (before expandable log section) to ensure it stays visible
        enable_frame, self.enable_mods_btn, self.patch_lunalib_btn = create_enable_mods_section(
            right_frame,
            self.enable_all_installed_mods,
            self.open_patch_lunalib_dialog
        )
        
        log_frame, self.install_progress_bar, self.log_text, self.pause_install_btn = create_log_section(
            right_frame, 
            self.current_mod_name,
            self.toggle_pause
        )
        
        self.root.update_idletasks()
        try:
            main_container.sash_place(0, 600, 1)
        except Exception:
            pass
    
    def on_window_resize(self, event):
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
            
            self.log("\n" + "=" * 50)
            self.log("User requested shutdown - canceling installation...", error=True)
            self.log("=" * 50)
            
            if self.current_executor:
                try:
                    self.current_executor.shutdown(wait=False, cancel_futures=True)
                    self.log("Download tasks canceled")
                except (RuntimeError, AttributeError) as e:
                    self.log(f"Error canceling tasks: {type(e).__name__}", error=True)
            
            self._cleanup_temp_files()
            
            self.is_installing = False
            self.is_paused = False
        
        self.save_modlist_config()
        self.log("Application closing...")
        self.root.destroy()
    
    def on_mod_click(self, event):
        index = self.mod_listbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        line_text = self.mod_listbox.get(f"{line_num}.0", f"{line_num}.end")
        
        line_stripped = line_text.strip()
        if line_stripped.startswith(LogSymbols.INSTALLED) or line_stripped.startswith(LogSymbols.NOT_INSTALLED) or line_stripped.startswith(LogSymbols.UPDATED):
            self.selected_mod_line = line_num
            self.highlight_selected_mod()
    
    def on_search_mods(self, search_text):
        self.search_filter = search_text.lower().strip()
        self.display_modlist_info()
    
    def open_add_mod_dialog(self):
        open_add_mod_dialog(self.root, self)
    
    def open_manage_categories_dialog(self):
        open_manage_categories_dialog(self.root, self)
    
    def open_import_preset_dialog(self):
        from .dialogs import open_import_preset_dialog
        open_import_preset_dialog(self.root, self)
    
    def open_patch_lunalib_dialog(self):
        """Show dialog to patch LunaSettings from a preset."""
        from .dialogs import open_patch_lunalib_dialog
        open_patch_lunalib_dialog(self.root, self)
    
    def validate_url(self, url: str, use_cache: bool = True) -> bool:
        """Validate URL using URLValidator.
        
        Args:
            url: URL to validate
            use_cache: If True, use cached results (default: True)
            
        Returns:
            bool: True if URL is valid, False otherwise
        """
        return self.url_validator.validate(url, use_cache=use_cache)

    def add_mod_to_config(self, mod: dict) -> None:
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
    
    def _swap_adjacent_mods(self, current_mod, category_mods, pos_in_category, direction):
        """Swap mod with adjacent mod in same category.
        
        Args:
            current_mod: Mod dictionary
            category_mods: List of mods in current category
            pos_in_category: Position of current mod in category
            direction: 1 for down, -1 for up
        """
        mods = self.modlist_data.get('mods', [])
        adjacent_mod = category_mods[pos_in_category + direction]
        idx_current = mods.index(current_mod)
        idx_adjacent = mods.index(adjacent_mod)
        mods[idx_current], mods[idx_adjacent] = mods[idx_adjacent], mods[idx_current]
        
        self.save_modlist_config()
        self.display_modlist_info()
        self.selected_mod_line = max(1, self.selected_mod_line + direction)
        self.highlight_selected_mod()
    
    def _move_to_adjacent_category(self, mod_name, current_mod, current_category, direction):
        """Move mod to adjacent category.
        
        Args:
            mod_name: Name of the mod
            current_mod: Mod dictionary
            current_category: Current category name
            direction: 1 for down, -1 for up
        """
        if direction == -1:
            target_category = self._find_category_above(self.selected_mod_line, current_category)
        else:
            target_category = self._find_category_below(self.selected_mod_line)
            if target_category == current_category:
                target_category = None
        
        if target_category:
            current_mod['category'] = target_category
            self.log(f"Moved '{mod_name}' to category '{target_category}'")
            self.save_modlist_config()
            self.display_modlist_info()
            self.find_and_select_mod(mod_name)
    
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
        
        can_move_in_category = (
            (direction == -1 and pos_in_category > 0) or
            (direction == 1 and pos_in_category < len(category_mods) - 1)
        )
        
        if can_move_in_category:
            self._swap_adjacent_mods(current_mod, category_mods, pos_in_category, direction)
        else:
            self._move_to_adjacent_category(mod_name, current_mod, current_category, direction)
    
    def toggle_expand_categories(self):
        """Toggle expand/collapse all categories.
        
        TODO: Not implemented yet. Requires:
        - UI button binding
        - State tracking for expanded/collapsed categories
        - Display logic update in display_modlist_info()
        """
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
        """Find category header above given line."""
        return self.category_navigator.find_category_above(line_num, current_category)
    
    def _find_category_below(self, line_num):
        """Find category header below given line."""
        return self.category_navigator.find_category_below(line_num)
    
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
        from .dialogs import open_edit_modlist_metadata_dialog
        open_edit_modlist_metadata_dialog(self.root, self)
    
    def _update_header_text(self):
        """Update header text widget with modlist metadata."""
        self.header_text.config(state=tk.NORMAL)
        self.header_text.delete(1.0, tk.END)
        
        header_info = (
            f"Name: {self.modlist_data.get('modlist_name') or 'Unnamed'}\n"
            f"Author: {self.modlist_data.get('author') or 'n/a'}\n"
            f"Version: {self.modlist_data.get('version') or 'n/a'}\n"
            f"Compatible with: {self.modlist_data.get('starsector_version') or 'N/A'}\n"
            f"Description: {self.modlist_data.get('description') or 'n/a'}"
        )
        
        self.header_text.insert(1.0, header_info)
        self.header_text.config(state=tk.DISABLED)
    
    def _configure_listbox_tags(self):
        """Configure Tkinter tags for listbox (category, selection, status)."""
        self.mod_listbox.tag_configure('category', background=AppTheme.CATEGORY_BG, 
            foreground=AppTheme.CATEGORY_FG, justify='center')
        self.mod_listbox.tag_configure('selected', background=AppTheme.ITEM_SELECTED_BG, 
            foreground=AppTheme.ITEM_SELECTED_FG)
        self.mod_listbox.tag_configure('installed', foreground=AppTheme.SUCCESS)
        self.mod_listbox.tag_configure('not_installed', foreground=AppTheme.TEXT_SECONDARY)
        self.mod_listbox.tag_configure('outdated', foreground='#e67e22')
    
    def _group_mods_by_category(self, mods):
        """Group mods by category, applying search filter.
        
        Args:
            mods: List of mod dictionaries
            
        Returns:
            dict: {category: [mod1, mod2, ...]}
        """
        if self.search_filter:
            mods = [m for m in mods if self.search_filter in m.get('name', '').lower()]
        
        categories = {}
        for mod in mods:
            cat = mod.get('category', 'Uncategorized')
            categories.setdefault(cat, []).append(mod)
        return categories
    
    def _get_mod_installation_status(self, mod, mods_dir):
        """Check if mod is installed and up-to-date.
        
        Args:
            mod: Mod dictionary
            mods_dir: Path to mods directory
            
        Returns:
            tuple: (icon, tag) for display
        """
        is_installed = False
        if mods_dir and mods_dir.exists():
            mod_name = mod.get('name', '')
            expected_version = mod.get('mod_version')
            if mod_name:
                check = is_mod_up_to_date(mod_name, expected_version, mods_dir)
                is_installed = check.is_current if expected_version else (check.installed_version is not None)
        
        icon = LogSymbols.INSTALLED if is_installed else LogSymbols.NOT_INSTALLED
        tag = 'installed' if is_installed else 'not_installed'
        return (icon, tag)
    
    def display_modlist_info(self):
        """Display the modlist information."""
        if not self.modlist_data:
            return
        
        # Update mod counter
        mod_count = len(self.modlist_data.get('mods', []))
        self.modlist_title_var.set(f"{mod_count} mod{'s' if mod_count != 1 else ''}")
        
        self._update_header_text()
        
        self.mod_listbox.config(state=tk.NORMAL)
        self.mod_listbox.delete(1.0, tk.END)
        self._configure_listbox_tags()
        
        mods = self.modlist_data.get('mods', [])
        grouped_mods = self._group_mods_by_category(mods)
        
        starsector_path = self.starsector_path.get()
        mods_dir = Path(starsector_path) / "mods" if starsector_path else None
        
        for cat in self.categories:
            self.mod_listbox.insert(tk.END, f"{cat}\n", 'category')
            
            if cat in grouped_mods:
                for mod in grouped_mods[cat]:
                    icon, tag = self._get_mod_installation_status(mod, mods_dir)
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
            # Check if it's a mod line (starts with icon)
            if (line_stripped.startswith(LogSymbols.INSTALLED) or line_stripped.startswith(LogSymbols.NOT_INSTALLED) or line_stripped.startswith(LogSymbols.UPDATED)) and mod_name in line_text:
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
        return listbox_helpers.extract_mod_name_from_line(line_text)
    
    def _find_mod_by_name(self, mod_name):
        """Find a mod dict by name using exact match or normalized matching."""
        mods = self.modlist_data.get('mods', [])
        return listbox_helpers.find_mod_by_name(mod_name, mods)
    
    def _format_log_entry(self, message, error=False, info=False, warning=False, debug=False, success=False):
        """Format log entry with timestamp and level prefix.
        
        Args:
            message: Message to log
            error, info, warning, debug, success: Log level flags
            
        Returns:
            tuple: (formatted_entry: str, tag: str)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if error:
            prefix, tag = 'ERROR: ', 'error'
        elif warning:
            prefix, tag = 'WARN: ', 'warning'
        elif info:
            prefix, tag = 'INFO: ', 'info'
        elif debug:
            prefix, tag = 'DEBUG: ', 'debug'
        elif success:
            prefix, tag = '', 'success'
        else:
            prefix, tag = '', 'normal'
        
        log_entry = f"[{timestamp}] {prefix}{message}\n"
        return (log_entry, tag)
    
    def _write_log_to_file(self, log_entry):
        """Write log entry to file.
        
        Args:
            log_entry: Formatted log entry string
        """
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass
    
    def _configure_log_tag(self, tag):
        """Configure Tkinter tag color for log level.
        
        Args:
            tag: Tag name (error, warning, info, debug, success, normal)
        """
        tag_colors = {
            'error': AppTheme.LOG_ERROR,
            'warning': AppTheme.LOG_WARNING,
            'success': AppTheme.LOG_SUCCESS,
            'info': AppTheme.LOG_INFO,
            'debug': AppTheme.LOG_DEBUG
        }
        if tag in tag_colors:
            self.log_text.tag_config(tag, foreground=tag_colors[tag])
    
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
        if debug and self.log_level != 'DEBUG':
            return
        
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self.log(message, error=error, info=info, warning=warning, debug=debug, success=success))
            return
        
        log_entry, tag = self._format_log_entry(message, error=error, info=info, warning=warning, debug=debug, success=success)
        self._write_log_to_file(log_entry)
        
        self.log_text.config(state=tk.NORMAL)
        self._configure_log_tag(tag)
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
            self.log(f"{LogSymbols.SUCCESS} Auto-detected Starsector installation: {detected_path}", info=True)
        else:
            self._auto_detected = False
            self.log(f"{LogSymbols.WARNING} Could not auto-detect Starsector. Please set path manually.", warning=True)
    
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
            parent=self.root,
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
            self.path_status_label.config(text=f"{LogSymbols.WARNING} No Starsector installation detected", fg="#e67e22")
            return
        
        is_valid, message = self.validate_starsector_path(path)
        if is_valid:
            if hasattr(self, '_auto_detected') and self._auto_detected:
                self.path_status_label.config(text=f"{LogSymbols.SUCCESS} Auto-detected", fg="#27ae60")
            else:
                self.path_status_label.config(text=f"{LogSymbols.SUCCESS} Valid path", fg="#27ae60")
        else:
            self.path_status_label.config(text=f"{LogSymbols.ERROR} {message}", fg="#e74c3c")
    
    def toggle_pause(self):
        """Toggle pause/resume during installation."""
        if not self.is_installing:
            return
        
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.log("Installation paused", warning=True)
            self.pause_install_btn.config(text=UISymbols.PLAY)
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
            self.pause_install_btn.config(text=UISymbols.PAUSE)
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
        
        has_space, space_msg = self.check_disk_space()
        self.log(f"Disk space: {space_msg}")
        
        self.log("=" * 50)
        self.log("Refreshing mod metadata from installed mods...")
        
        try:
            self.modlist_data = self.config_manager.load_modlist_config()
            
            updated_count, error = refresh_mod_metadata(
                self.modlist_data, mods_dir, log_callback=self.log
            )
            
            if error:
                raise Exception(error)
            
            self.save_modlist_config()
            self.display_modlist_info()
            self.log(f"{LogSymbols.SUCCESS} Metadata refresh complete! Updated {updated_count} mod(s)")
            custom_dialogs.showsuccess("Success", f"Refreshed metadata for {updated_count} mod(s)", parent=self.root)
        except Exception as e:
            self.log(f"{LogSymbols.ERROR} Error refreshing metadata: {e}", error=True)
            custom_dialogs.showerror("Error", f"Failed to refresh metadata: {e}", parent=self.root)
    
    def enable_all_installed_mods(self):
        """Enable mods from the current modlist that are installed (updates enabled_mods.json)."""
        starsector_dir = self.starsector_path.get()
        
        if not starsector_dir:
            custom_dialogs.showerror("Error", "Starsector path not set. Please configure it in settings.")
            return
        
        mods_dir = Path(starsector_dir) / "mods"
        
        if not mods_dir.exists():
            custom_dialogs.showerror("Error", f"Mods directory not found: {mods_dir}")
            return
        
        self.log("=" * 50)
        
        try:
            enabled_count, error = enable_modlist_mods(
                mods_dir, self.mod_installer, self.modlist_data, log_callback=self.log
            )
            
            if error:
                if "No mods found" in error:
                    custom_dialogs.showwarning("No Mods Found", error)
                else:
                    custom_dialogs.showerror("Error", error)
                return
            
            custom_dialogs.showsuccess("Success", f"Successfully enabled {enabled_count} mod(s) from the current modlist.\n\nYour mods should now be active when you start Starsector.")
        except Exception as e:
            self.log(f"{LogSymbols.ERROR} Error enabling mods: {e}", error=True)
            custom_dialogs.showerror("Error", f"Failed to enable mods: {e}")
    
    def open_export_preset_dialog(self):
        """Show dialog to export current modlist as a preset."""
        from .dialogs import open_export_preset_dialog
        open_export_preset_dialog(self.root, self)
    
    def check_disk_space(self):
        """Check if there's enough disk space."""
        if not self.starsector_path.get():
            return True, "Starsector path not set"
        
        return installation_checks.check_disk_space(self.starsector_path.get(), MIN_FREE_SPACE_GB)
    
    def _run_pre_installation_checks(self, starsector_dir):
        """Run comprehensive pre-installation checks.
        
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        def log_wrapper(msg, level='info'):
            if level == 'warning':
                self.log(msg, warning=True)
            elif level == 'debug':
                self.log(msg, debug=True)
            else:
                self.log(msg)
        
        def prompt_wrapper(title, message):
            return custom_dialogs.askyesno(title, message)
        
        mods_dir = starsector_dir / "mods"
        check_deps_func = lambda md: self._check_dependencies(md)
        
        return installation_checks.run_all_pre_installation_checks(
            starsector_dir,
            self.modlist_data,
            check_deps_func,
            log_callback=log_wrapper,
            prompt_callback=prompt_wrapper,
            min_disk_gb=MIN_FREE_SPACE_GB
        )
    
    def _check_dependencies(self, mods_dir):
        """Check for missing dependencies in the modlist.
        
        Args:
            mods_dir: Path to mods directory
            
        Returns:
            dict: {mod_name: [list of missing dependency IDs]}
        """
        # Delegate to mod_utils
        missing_deps, error = check_mod_dependencies(self.modlist_data, mods_dir)
        
        if error:
            self.log(f"Error checking dependencies: {error}", debug=True)
            return {}
        
        return missing_deps
    
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
                folder = filedialog.askdirectory(parent=self.root, title="Select Starsector folder")
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
        self.log("\n" + LogSymbols.SEPARATOR * 60)
        self.log("Running pre-installation checks...")
        check_success, check_error = self._run_pre_installation_checks(starsector_dir)
        if not check_success:
            custom_dialogs.showerror("Pre-Installation Check Failed", check_error)
            return
        self.log(f"{LogSymbols.SUCCESS} All pre-installation checks passed")
        
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
                    self.log(f"  {LogSymbols.BULLET} {mod_info['name']}: v{mod_info['installed_version']} {LogSymbols.ARROW_RIGHT} v{mod_info['expected_version']}", warning=True)
                
                # Ask user if they want to update
                msg = f"{len(outdated)} mod(s) will be updated:\n\n"
                for mod_info in outdated[:5]:  # Show max 5 in dialog
                    msg += f"{LogSymbols.BULLET} {mod_info['name']}: v{mod_info['installed_version']} {LogSymbols.ARROW_RIGHT} v{mod_info['expected_version']}\n"
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
                    progress_callback=None,
                    timeout=URL_VALIDATION_TIMEOUT_HEAD
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
        mediafire_mods = results['mediafire']
        other_domains = results['other']
        failed_list = results['failed']
        
        total_other = sum(len(mods) for mods in other_domains.values())
        self.log(f"GitHub: {len(github_mods)}, Google Drive: {len(gdrive_mods)}, Mediafire: {len(mediafire_mods)}, Other: {total_other}, Failed: {len(failed_list)}")
        
        if github_mods or gdrive_mods or mediafire_mods or other_domains or failed_list:
            action = custom_dialogs.show_validation_report(
                self.root,
                github_mods,
                gdrive_mods,
                mediafire_mods,
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
            self.installation_controller.install_mods_internal(mods_to_install, skip_gdrive_check=skip_gdrive_check)
        
        thread = threading.Thread(target=run_specific_installation, daemon=True)
        thread.start()
    
    def install_mods(self):
        self.installation_controller.install_mods_internal(self.modlist_data['mods'])
    
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
    
    def _show_installation_complete_message(self):
        """Display the installation complete banner (used for Google Drive cancellation)."""
        self.log(f"\n{LogSymbols.SUCCESS} Installation workflow complete.", success=True)

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


