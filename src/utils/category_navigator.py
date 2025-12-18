"""Category navigation and search helpers for Tkinter listbox."""

import tkinter as tk


class CategoryNavigator:
    """Helper class for navigating category headers in a Tkinter listbox."""
    
    def __init__(self, listbox):
        """Initialize with target listbox.
        
        Args:
            listbox: Tkinter Text widget used as listbox
        """
        self.listbox = listbox
    
    def find_category_line(self, category_name):
        """Find line number of category header.
        
        Args:
            category_name: Name of category to find
            
        Returns:
            int or None: Line number if found, None otherwise
        """
        try:
            max_line = int(self.listbox.index('end-1c').split('.')[0])
        except (tk.TclError, ValueError):
            return None
        
        for line_num in range(1, max_line + 1):
            line_text = self.listbox.get(f"{line_num}.0", f"{line_num}.end").strip()
            if line_text == category_name:
                return line_num
        return None
    
    def find_category_above(self, line_num, current_category=None):
        """Find category header above given line.
        
        Args:
            line_num: Line number to search from
            current_category: Optional category to exclude from results
            
        Returns:
            str or None: Category name if found
        """
        check_line = line_num - 1
        while check_line >= 1:
            check_text = self.listbox.get(f"{check_line}.0", f"{check_line}.end").strip()
            # Category lines don't start with status icons
            if check_text and not self._is_mod_line(check_text):
                if current_category is None or check_text != current_category:
                    return check_text
            check_line -= 1
        return None
    
    def find_category_below(self, line_num):
        """Find category header below given line.
        
        Args:
            line_num: Line number to search from
            
        Returns:
            str or None: Category name if found
        """
        try:
            max_line = int(self.listbox.index('end-1c').split('.')[0])
        except (tk.TclError, ValueError):
            max_line = 1
        
        check_line = line_num + 1
        while check_line <= max_line:
            check_text = self.listbox.get(f"{check_line}.0", f"{check_line}.end").strip()
            # Category lines don't start with status icons
            if check_text and not self._is_mod_line(check_text):
                return check_text
            check_line += 1
        return None
    
    @staticmethod
    def _is_mod_line(line_text):
        """Check if line is a mod entry (vs category header).
        
        Args:
            line_text: Text from listbox line
            
        Returns:
            bool: True if mod line
        """
        stripped = line_text.strip()
        return stripped.startswith("✓") or stripped.startswith("○") or stripped.startswith("↑")
