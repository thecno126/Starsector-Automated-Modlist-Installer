"""
Mod List Controller - Handles mod list management, display, and reordering.

Extracted from MainWindow to improve code organization and maintainability.
"""

import tkinter as tk
from pathlib import Path

from . import custom_dialogs
from .dialogs import open_edit_mod_dialog
from utils.theme import TriOSTheme
from utils.mod_utils import normalize_mod_name


class ModListController:
    """Handles all mod list management operations."""
    
    def __init__(self, parent):
        """Initialize the mod list controller.
        
        Args:
            parent: Reference to MainWindow instance
        """
        self.parent = parent
        self.selected_mod_line = None
        self.search_filter = ""
        
        # Drag and drop state
        self.drag_start_line = None
        self.drag_start_y = None
    
    def setup_drag_and_drop(self, mod_listbox):
        """Set up drag and drop handlers for mod list reordering."""
        mod_listbox.bind('<Button-1>', self._on_drag_start, add="+")
        mod_listbox.bind('<B1-Motion>', self._on_drag_motion)
        mod_listbox.bind('<ButtonRelease-1>', self._on_drag_end, add="+")
    
    def _on_drag_start(self, event):
        """Handle start of drag operation."""
        index = self.parent.mod_listbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        line_text = self.parent.mod_listbox.get(f"{line_num}.0", f"{line_num}.end").strip()
        
        if line_text and (line_text.startswith("✓") or line_text.startswith("○") or line_text.startswith("↑")):
            self.drag_start_line = line_num
            self.drag_start_y = event.y
        else:
            self.drag_start_line = None
    
    def _on_drag_motion(self, event):
        """Handle drag motion."""
        if self.drag_start_line is None:
            return
    
    def _on_drag_end(self, event):
        """Handle end of drag operation - reorder mod."""
        if self.drag_start_line is None:
            return
        
        try:
            index = self.parent.mod_listbox.index(f"@{event.x},{event.y}")
            target_line = int(index.split('.')[0])
            
            if abs(target_line - self.drag_start_line) < 1:
                self.drag_start_line = None
                return
            
            source_text = self.parent.mod_listbox.get(f"{self.drag_start_line}.0", f"{self.drag_start_line}.end")
            source_mod_name = self._extract_mod_name_from_line(source_text)
            
            if not source_mod_name:
                self.drag_start_line = None
                return
            
            source_mod = self.find_mod_by_name(source_mod_name)
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
            
            position = 0
            for line_num in range(category_start_line + 1, target_line + 1):
                line_text = self.parent.mod_listbox.get(f"{line_num}.0", f"{line_num}.end").strip()
                if line_text and (line_text.startswith("✓") or line_text.startswith("○") or line_text.startswith("↑")):
                    position += 1
            
            self._move_mod_to_category_position(source_mod_name, source_mod, target_category, position)
            
        except Exception as e:
            self.parent.log(f"Drag and drop error: {e}", debug=True)
        finally:
            self.drag_start_line = None
    
    def _find_category_line(self, category_name):
        """Find the line number of a category header."""
        try:
            max_line = int(self.parent.mod_listbox.index('end-1c').split('.')[0])
        except (tk.TclError, ValueError):
            return None
        
        for line_num in range(1, max_line + 1):
            line_text = self.parent.mod_listbox.get(f"{line_num}.0", f"{line_num}.end").strip()
            if line_text == category_name:
                return line_num
        return None
    
    def _move_mod_to_category_position(self, mod_name, mod, target_category, position):
        """Move a mod to a specific position within a category."""
        source_category = mod.get('category', 'Uncategorized')
        
        if source_category in self.parent.modlist_data.get('mods_by_category', {}):
            category_mods = self.parent.modlist_data['mods_by_category'][source_category]
            category_mods = [m for m in category_mods if m.get('name') != mod_name]
            self.parent.modlist_data['mods_by_category'][source_category] = category_mods
        
        mod['category'] = target_category
        
        if target_category not in self.parent.modlist_data.get('mods_by_category', {}):
            self.parent.modlist_data['mods_by_category'][target_category] = []
        
        category_mods = self.parent.modlist_data['mods_by_category'][target_category]
        position = max(0, min(position, len(category_mods)))
        category_mods.insert(position, mod)
        
        self.parent.modlist_data['mods'] = []
        for category in self.parent.categories:
            if category in self.parent.modlist_data['mods_by_category']:
                self.parent.modlist_data['mods'].extend(self.parent.modlist_data['mods_by_category'][category])
        
        self.parent.save_modlist_config()
        self.display_modlist_info()
        self.parent.log(f"✓ Moved '{mod_name}' to {target_category} (position {position})", debug=True)
    
    def on_mod_click(self, event):
        """Handle click on mod list."""
        index = self.parent.mod_listbox.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        line_text = self.parent.mod_listbox.get(f"{line_num}.0", f"{line_num}.end")
        
        line_stripped = line_text.strip()
        if line_stripped.startswith("✓") or line_stripped.startswith("○") or line_stripped.startswith("↑"):
            self.selected_mod_line = line_num
            self.highlight_selected_mod()
    
    def on_search_mods(self, search_text):
        """Handle search filter changes."""
        self.search_filter = search_text.lower().strip()
        self.display_modlist_info()
    
    def add_mod_to_config(self, mod: dict) -> None:
        """Add a new mod to the configuration."""
        if not self.parent.modlist_data:
            self.parent.modlist_data = {'mods': [], 'modlist_name': 'Custom Modlist', 'version': '1.0'}
        
        self.parent.modlist_data['mods'].append(mod)
        self.parent.save_modlist_config()
        self.display_modlist_info()
        self.parent.log(f"Added mod: {mod['name']}")
    
    def remove_selected_mod(self):
        """Remove the currently selected mod."""
        if self.selected_mod_line is None:
            custom_dialogs.showwarning("No Selection", "Please select a mod to remove")
            return
        
        line_text = self.parent.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        
        if not mod_name:
            custom_dialogs.showwarning("Invalid Selection", "Please select a mod (not a category header)")
            return
        
        if not custom_dialogs.askyesno(
            "Confirm Removal",
            f"Are you sure you want to remove '{mod_name}' from the modlist?\n\nThis action cannot be undone."
        ):
            return
        
        mods = self.parent.modlist_data.get('mods', [])
        mod_to_remove = next((m for m in mods if m.get('name') == mod_name), None)
        
        if not mod_to_remove:
            normalized_search = normalize_mod_name(mod_name)
            mod_to_remove = next((m for m in mods if normalize_mod_name(m.get('name', '')) == normalized_search), None)
        
        if mod_to_remove:
            self.parent.modlist_data['mods'].remove(mod_to_remove)
            self.parent.log(f"Removed mod: {mod_to_remove.get('name')}")
            self.parent.save_modlist_config()
            self.display_modlist_info()
            self.selected_mod_line = None
        else:
            custom_dialogs.showerror("Error", f"Mod '{mod_name}' not found in configuration")
    
    def edit_selected_mod(self):
        """Edit the currently selected mod."""
        if self.selected_mod_line is None:
            custom_dialogs.showwarning("No Selection", "Please select a mod to edit")
            return
        
        line_text = self.parent.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        
        if not mod_name:
            custom_dialogs.showwarning("Invalid Selection", "Please select a mod (not a category header)")
            return
        
        current_mod = self.find_mod_by_name(mod_name)
        if not current_mod:
            custom_dialogs.showerror("Error", f"Mod '{mod_name}' not found in configuration")
            return
        
        open_edit_mod_dialog(self.parent.root, self.parent, current_mod)
    
    def move_mod_up(self):
        """Move selected mod up."""
        if self.selected_mod_line is None:
            return
        
        line_text = self.parent.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        if not mod_name:
            return
        
        current_mod = self.find_mod_by_name(mod_name)
        if current_mod:
            self._move_mod_in_category(mod_name, current_mod, -1)
    
    def move_mod_down(self):
        """Move selected mod down."""
        if self.selected_mod_line is None:
            return
        
        line_text = self.parent.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        if not mod_name:
            return
        
        current_mod = self.find_mod_by_name(mod_name)
        if current_mod:
            self._move_mod_in_category(mod_name, current_mod, 1)
    
    def _move_mod_in_category(self, mod_name, current_mod, direction):
        """Move mod up or down within category or to adjacent category."""
        mods = self.parent.modlist_data.get('mods', [])
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
            adjacent_mod = category_mods[pos_in_category + direction]
            idx_current = mods.index(current_mod)
            idx_adjacent = mods.index(adjacent_mod)
            mods[idx_current], mods[idx_adjacent] = mods[idx_adjacent], mods[idx_current]
            
            self.parent.save_modlist_config()
            self.display_modlist_info()
            self.selected_mod_line = max(1, self.selected_mod_line + direction)
            self.highlight_selected_mod()
        else:
            if direction == -1:
                target_category = self._find_category_above(self.selected_mod_line, current_category)
            else:
                target_category = self._find_category_below(self.selected_mod_line)
                if target_category == current_category:
                    target_category = None
            
            if target_category:
                current_mod['category'] = target_category
                self.parent.log(f"Moved '{mod_name}' to category '{target_category}'")
                self.parent.save_modlist_config()
                self.display_modlist_info()
                self.find_and_select_mod(mod_name)
    
    def _find_category_above(self, line_num, current_category=None):
        """Find category header above given line."""
        check_line = line_num - 1
        while check_line >= 1:
            check_text = self.parent.mod_listbox.get(f"{check_line}.0", f"{check_line}.end").strip()
            if check_text and not (check_text.startswith("✓") or check_text.startswith("○") or check_text.startswith("↑")):
                if current_category is None or check_text != current_category:
                    return check_text
            check_line -= 1
        return None
    
    def _find_category_below(self, line_num):
        """Find category header below given line."""
        try:
            max_line = int(self.parent.mod_listbox.index('end-1c').split('.')[0])
        except (tk.TclError, ValueError):
            max_line = 1
        
        check_line = line_num + 1
        while check_line <= max_line:
            check_text = self.parent.mod_listbox.get(f"{check_line}.0", f"{check_line}.end").strip()
            if check_text and not (check_text.startswith("✓") or check_text.startswith("○") or check_text.startswith("↑")):
                return check_text
            check_line += 1
        return None
    
    def display_modlist_info(self):
        """Display the modlist information."""
        if not self.parent.modlist_data:
            return
        
        # Update header
        self.parent.header_text.config(state=tk.NORMAL)
        self.parent.header_text.delete(1.0, tk.END)
        
        header_info = (
            f"Name: {self.parent.modlist_data.get('modlist_name') or 'Unnamed'}\n"
            f"Version: {self.parent.modlist_data.get('version') or 'n/a'}\n"
            f"Compatible with: {self.parent.modlist_data.get('starsector_version') or 'N/A'}\n"
            f"Description: {self.parent.modlist_data.get('description') or 'n/a'}"
        )
        
        self.parent.header_text.insert(1.0, header_info)
        self.parent.header_text.config(state=tk.DISABLED)
        
        # Update mod list
        self.parent.mod_listbox.config(state=tk.NORMAL)
        self.parent.mod_listbox.delete(1.0, tk.END)
        
        # Configure tags
        self.parent.mod_listbox.tag_configure('category', background=TriOSTheme.CATEGORY_BG, 
            foreground=TriOSTheme.CATEGORY_FG, justify='center')
        self.parent.mod_listbox.tag_configure('selected', background=TriOSTheme.ITEM_SELECTED_BG, 
            foreground=TriOSTheme.ITEM_SELECTED_FG)
        self.parent.mod_listbox.tag_configure('installed', foreground=TriOSTheme.SUCCESS)
        self.parent.mod_listbox.tag_configure('not_installed', foreground=TriOSTheme.TEXT_SECONDARY)
        self.parent.mod_listbox.tag_configure('outdated', foreground='#e67e22')
        
        mods = self.parent.modlist_data.get('mods', [])
        
        if self.search_filter:
            mods = [m for m in mods if self.search_filter in m.get('name', '').lower()]
        
        categories = {}
        for mod in mods:
            cat = mod.get('category', 'Uncategorized')
            categories.setdefault(cat, []).append(mod)
        
        starsector_path = self.parent.starsector_path.get()
        mods_dir = Path(starsector_path) / "mods" if starsector_path else None
        
        for cat in self.parent.categories:
            self.parent.mod_listbox.insert(tk.END, f"{cat}\n", 'category')
            
            if cat in categories:
                for mod in categories[cat]:
                    is_installed = False
                    if mods_dir and mods_dir.exists():
                        is_installed = self.parent.mod_installer.is_mod_already_installed(mod, mods_dir)
                    
                    icon = "✓" if is_installed else "○"
                    tag = 'installed' if is_installed else 'not_installed'
                    
                    self.parent.mod_listbox.insert(tk.END, f"  {icon} {mod['name']}\n", ('mod', tag))
        
        self.parent.mod_listbox.config(state=tk.DISABLED)
    
    def highlight_selected_mod(self):
        """Highlight the selected mod."""
        if self.selected_mod_line is None:
            return
            
        self.parent.mod_listbox.config(state=tk.NORMAL)
        self.parent.mod_listbox.tag_remove('selected', '1.0', tk.END)
        self.parent.mod_listbox.tag_add('selected', f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        self.parent.mod_listbox.config(state=tk.DISABLED)
    
    def find_and_select_mod(self, mod_name):
        """Find and select a mod by name."""
        max_line = int(self.parent.mod_listbox.index('end-1c').split('.')[0])
        
        for line_num in range(1, max_line + 1):
            line_text = self.parent.mod_listbox.get(f"{line_num}.0", f"{line_num}.end")
            line_stripped = line_text.strip()
            if (line_stripped.startswith("✓") or line_stripped.startswith("○") or line_stripped.startswith("↑")) and mod_name in line_text:
                self.selected_mod_line = line_num
                self.highlight_selected_mod()
                return
        
        self.selected_mod_line = None
    
    def find_mod_by_name(self, mod_name):
        """Find a mod dict by name using exact match or normalized matching."""
        mods = self.parent.modlist_data.get('mods', [])
        
        exact_match = next((m for m in mods if m.get('name') == mod_name), None)
        if exact_match:
            return exact_match
        
        normalized_search = normalize_mod_name(mod_name)
        for mod in mods:
            mod_config_name = mod.get('name', '')
            if normalize_mod_name(mod_config_name) == normalized_search:
                return mod
        
        return None
    
    def _extract_mod_name_from_line(self, line_text):
        """Extract mod name from a listbox line."""
        line = line_text.strip()
        if not (line.startswith("✓") or line.startswith("○") or line.startswith("↑")):
            return None
        name_part = line_text.replace("  ✓ ", "").replace("  ○ ", "").replace("  ↑ ", "")
        return name_part.split(" v")[0].strip()
