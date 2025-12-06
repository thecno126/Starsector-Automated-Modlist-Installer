"""
Main window for the Modlist Installer application.
Simplified version using modular components.
"""

import tkinter as tk
from tkinter import filedialog
import requests
from gui import custom_dialogs
from pathlib import Path
import threading
import concurrent.futures
from datetime import datetime
import sys
import shutil

# Import from our modules
from core import (
    LOG_FILE,
    URL_VALIDATION_TIMEOUT_HEAD, MIN_FREE_SPACE_GB,
    ModInstaller, ConfigManager
)
from core.installer import validate_mod_urls
from gui.dialogs import (
    open_add_mod_dialog,
    open_manage_categories_dialog,
    open_import_csv_dialog,
    open_export_csv_dialog,
    fix_google_drive_url
)
from gui.ui_builder import (
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
        self.root.geometry("1050x720")
        self.root.resizable(True, True)
        self.root.minsize(950, 670)
        
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
        self.trust_google_drive = tk.BooleanVar(value=False)  # User trust for Google Drive large files
        
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
        self.root.bind('<Control-s>', lambda e: self.save_modlist_config())
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
        info_frame, main_paned, self.header_text, self.mod_listbox = create_modlist_section(
            left_frame,
            self.on_mod_click,
            lambda e: self.root.after(100, self.display_modlist_info)
        )
        
        # Track selected line
        self.selected_mod_line = None
        
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
        
        # Bottom buttons (on left side) with Google Drive trust checkbox
        button_frame, self.install_modlist_btn, self.quit_btn = create_bottom_buttons(
            left_frame,
            self.start_installation,
            self.safe_quit,
            self.trust_google_drive
        )
        
        # Right side: Log panel
        right_frame = tk.Frame(main_container, padx=10, pady=10)
        main_container.add(right_frame, minsize=400, stretch="always")
        
        log_frame, self.install_progress_bar, self.log_text = create_log_section(right_frame)
        
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
                "Closing now will cancel all downloads and stop the installation.\n\n"
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
                except Exception as e:
                    self.log(f"Error canceling tasks: {e}", error=True)
            
            self.is_installing = False
            self.is_paused = False
        
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
    
    def validate_url(self, url: str) -> bool:
        """Return True if the URL appears reachable."""
        try:
            # Try HEAD first (lighter)
            resp = requests.head(url, timeout=URL_VALIDATION_TIMEOUT_HEAD, allow_redirects=True)
            if 200 <= resp.status_code < 400:
                return True
            # Some servers don't support HEAD, fallback to GET
            resp = requests.get(url, stream=True, timeout=URL_VALIDATION_TIMEOUT_HEAD, allow_redirects=True)
            return 200 <= resp.status_code < 400
        except Exception:
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
        from gui.dialogs import open_edit_mod_dialog
        open_edit_mod_dialog(self.root, self, current_mod)
    
    # ============================================
    # Mod Reordering
    # ============================================
    
    def move_mod_up(self):
        """Move selected mod up."""
        if self.selected_mod_line is None:
            return
        
        line_text = self.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        if not mod_name:
            return
        
        current_mod = self._find_mod_by_name(mod_name)
        if not current_mod:
            return
        
        mods = self.modlist_data.get('mods', [])
        current_category = current_mod.get('category', 'Uncategorized')
        category_mods = [m for m in mods if m.get('category', 'Uncategorized') == current_category]
        
        try:
            pos_in_category = category_mods.index(current_mod)
        except ValueError:
            return
        
        if pos_in_category > 0:
            prev_mod = category_mods[pos_in_category - 1]
            idx_current, idx_prev = mods.index(current_mod), mods.index(prev_mod)
            mods[idx_current], mods[idx_prev] = mods[idx_prev], mods[idx_current]
            
            self.save_modlist_config()
            self.display_modlist_info()
            self.selected_mod_line = max(1, self.selected_mod_line - 1)
            self.highlight_selected_mod()
        else:
            target_category = self._find_category_above(self.selected_mod_line, current_category)
            if target_category:
                current_mod['category'] = target_category
                self.log(f"Moved '{mod_name}' to category '{target_category}'")
                self.save_modlist_config()
                self.display_modlist_info()
                self.find_and_select_mod(mod_name)
    
    def move_mod_down(self):
        """Move selected mod down."""
        if self.selected_mod_line is None:
            return
        
        line_text = self.mod_listbox.get(f"{self.selected_mod_line}.0", f"{self.selected_mod_line}.end")
        mod_name = self._extract_mod_name_from_line(line_text)
        if not mod_name:
            return
        
        current_mod = self._find_mod_by_name(mod_name)
        if not current_mod:
            return
        
        mods = self.modlist_data.get('mods', [])
        current_category = current_mod.get('category', 'Uncategorized')
        category_mods = [m for m in mods if m.get('category', 'Uncategorized') == current_category]
        
        try:
            pos_in_category = category_mods.index(current_mod)
        except ValueError:
            return
        
        if pos_in_category < len(category_mods) - 1:
            next_mod = category_mods[pos_in_category + 1]
            idx_current, idx_next = mods.index(current_mod), mods.index(next_mod)
            mods[idx_current], mods[idx_next] = mods[idx_next], mods[idx_current]
            
            self.save_modlist_config()
            self.display_modlist_info()
            self.selected_mod_line += 1
            self.highlight_selected_mod()
        else:
            target_category = self._find_category_below(self.selected_mod_line)
            if target_category:
                current_mod['category'] = target_category
                self.log(f"Moved '{mod_name}' to category '{target_category}'")
                self.save_modlist_config()
                self.display_modlist_info()
                self.find_and_select_mod(mod_name)
    
    def _find_category_above(self, line_num, current_category):
        """Find category header above given line."""
        check_line = line_num - 1
        while check_line >= 1:
            check_text = self.mod_listbox.get(f"{check_line}.0", f"{check_line}.end").strip()
            if check_text and not check_text.startswith("•") and check_text != current_category:
                return check_text
            check_line -= 1
        return None
    
    def _find_category_below(self, line_num):
        """Find category header below given line."""
        max_line = int(self.mod_listbox.index('end-1c').split('.')[0])
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
    
    def save_modlist_config(self):
        """Save the current modlist configuration."""
        if not self.modlist_data:
            return
        self.config_manager.save_modlist_config(self.modlist_data)
        self.log("Configuration saved")
    
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
        categories = {}
        for mod in mods:
            cat = mod.get('category', 'Uncategorized')
            categories.setdefault(cat, []).append(mod)
        
        # Display categories
        for cat in self.categories:
            self.mod_listbox.insert(tk.END, f"{cat}\n", 'category')
            
            if cat in categories:
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
    
    def log(self, message, error=False, info=False):
        """Append a message to the log.
        
        Args:
            message: Message to log
            error: If True, display in red (for errors)
            info: If True, display in blue (for informational messages like skips)
        """
        if threading.current_thread() is not threading.main_thread():
            self.root.after(0, lambda: self.log(message, error, info))
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = 'ERROR: ' if error else 'INFO: ' if info else ''
        log_entry = f"[{timestamp}] {prefix}{message}\n"
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass

        self.log_text.config(state=tk.NORMAL)
        if error:
            tag = "error"
            self.log_text.tag_config("error", foreground="red")
        elif info:
            tag = "info"
            self.log_text.tag_config("info", foreground="#3498db")  # Blue
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
        
        # Check for Starsector-specific files/folders
        # macOS: Starsector.app with Contents/Home (JRE) or Contents/Resources/Java
        # Windows/Linux: jre folder and executables
        
        is_mac_app = (
            str(path).endswith('.app') and 
            (path / "Contents/Home").exists() and
            (path / "Contents/Resources/Java").exists()
        )
        
        has_jre = any([
            (path / "jre").exists(),
            (path / "jre_linux").exists(),
            (path / "Contents/Home").exists(),  # macOS JRE
        ])
        
        has_game_files = any([
            (path / "starsector.exe").exists(),
            (path / "starsector.sh").exists(),
            (path / "Contents/Resources/Java/starsector.command").exists(),  # macOS
            (path / "Contents/Resources/Java").exists(),  # macOS game files
        ])
        
        # Validate: Mac app bundle OR (JRE + game files)
        if not (is_mac_app or (has_jre and has_game_files)):
            return False, "Not a valid Starsector installation (missing JRE or game files)"
        
        # Create mods folder if it doesn't exist
        mods_folder = path / "mods"
        if not mods_folder.exists():
            try:
                mods_folder.mkdir(parents=True, exist_ok=True)
                self.log(f"Created mods folder: {mods_folder}")
            except Exception as e:
                return False, f"Cannot create mods folder: {e}"
        
        return True, "Valid"
    
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
            response = custom_dialogs.askyesno("Low Disk Space", f"{space_msg}\n\nContinue anyway?")
            if not response:
                return
        
        mods_dir = starsector_dir / "mods"
        
        if not self.modlist_data:
            custom_dialogs.showerror("Error", "No modlist configuration loaded")
            return
        
        # Validate all URLs before installation
        self.log("Validating mod URLs (this may take a moment)...")
        self.install_modlist_btn.config(text="Validating URLs...")
        
        # Run validation in separate thread (without UI updates from thread)
        validation_result = {'data': None, 'error': None}
        
        def run_validation():
            try:
                validation_result['data'] = validate_mod_urls(
                    self.modlist_data['mods'], 
                    progress_callback=None  # No UI updates during validation
                )
            except Exception as e:
                validation_result['error'] = str(e)
        
        validation_thread = threading.Thread(target=run_validation, daemon=True)
        validation_thread.start()
        
        # Wait for validation with periodic UI updates
        max_wait = 60  # seconds
        elapsed = 0
        while validation_thread.is_alive() and elapsed < max_wait:
            self.root.update()
            validation_thread.join(timeout=0.1)
            elapsed += 0.1
        
        if validation_result['error']:
            custom_dialogs.showerror("Validation Error", f"Failed to validate URLs: {validation_result['error']}")
            self.install_modlist_btn.config(text="Install Modlist")
            return
        
        if not validation_result['data']:
            custom_dialogs.showerror("Validation Timeout", "URL validation took too long. Try again or check your internet connection.")
            self.install_modlist_btn.config(text="Install Modlist")
            return
        
        results = validation_result['data']
        self.install_modlist_btn.config(text="Install Modlist")
        
        # Extract counts
        github_count = len(results['github'])
        gdrive_mods = results['google_drive']
        other_domains = results['other']
        failed_list = results['failed']
        
        total_other = sum(len(mods) for mods in other_domains.values())
        self.log(f"GitHub: {github_count}, Google Drive: {len(gdrive_mods)}, Other: {total_other}, Failed: {len(failed_list)}")
        
        # Always show validation report if there are mods to install
        if github_count > 0 or len(gdrive_mods) > 0 or other_domains or failed_list:
            action = custom_dialogs.show_validation_report(
                self.root,
                github_count,
                gdrive_mods,
                other_domains,
                failed_list
            )
            
            if action == 'cancel':
                self.log("Installation cancelled by user")
                return
            # If action == 'continue', proceed directly with installation
        
        # Start installation directly (validation already confirmed)
        self.is_installing = True
        self.is_paused = False
        self.install_modlist_btn.config(state=tk.DISABLED, text="Installing...")
        self.pause_install_btn.config(state=tk.NORMAL)
        self.install_progress_bar['value'] = 0
        
        thread = threading.Thread(target=self.install_mods, daemon=True)
        thread.start()
    
    def install_specific_mods(self, mod_names, temp_mods=None):
        """Install only specific mods by name.
        
        Args:
            mod_names: List of mod names to install
            temp_mods: Optional list of mod dictionaries with temporary URLs (e.g., fixed Google Drive)
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
            self._install_mods_internal(mods_to_install)
        
        thread = threading.Thread(target=run_specific_installation, daemon=True)
        thread.start()
    
    def install_mods(self):
        """Install the mods from the modlist using parallel downloads and sequential extraction."""
        self._install_mods_internal(self.modlist_data['mods'])
    
    def _install_mods_internal(self, mods_to_install):
        """Internal method to install a list of mods.
        
        Args:
            mods_to_install: List of mod dictionaries to install
        """
        mods_dir = Path(self.starsector_path.get()) / "mods"
        total_mods = len(mods_to_install)

        self.log(f"Starting installation of {total_mods} mod{'s' if total_mods > 1 else ''}...")
        self.log("=" * 50)
        
        # Reset failure tracking for this installation
        self.mod_installer.reset_failure_tracking()
        
        # Apply Google Drive URL fix automatically if trust is checked
        if self.trust_google_drive.get():
            from gui.dialogs import fix_google_drive_url
            fixed_mods = []
            for mod in mods_to_install:
                url = mod.get('download_url', '')
                if 'drive.google.com' in url or 'drive.usercontent.google.com' in url:
                    fixed_url = fix_google_drive_url(url)
                    if fixed_url != url:
                        mod_copy = mod.copy()
                        mod_copy['download_url'] = fixed_url
                        fixed_mods.append(mod_copy)
                        self.log(f"  🔧 Auto-fixed Google Drive URL: {mod.get('name')}", info=True)
                    else:
                        fixed_mods.append(mod)
                else:
                    fixed_mods.append(mod)
            mods_to_download = fixed_mods
        else:
            # If not trusted, attempt mods as-is (failures will be caught later)
            mods_to_download = mods_to_install

        # Step 1: parallel downloads
        download_results = []
        gdrive_ignored = []
        max_workers = 3
        self.log(f"Starting parallel downloads (workers={max_workers})...")
        self.current_executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_to_mod = {
                self.current_executor.submit(self.mod_installer.download_archive, mod): mod
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
                try:
                    temp_path, is_7z = future.result()
                    if temp_path:
                        download_results.append((mod, temp_path, is_7z))
                        self.log(f"  ✓ Downloaded: {mod.get('name')}")
                    else:
                        # Check if it's a Google Drive failure
                        url = mod.get('download_url', '')
                        if 'drive.google.com' in url or 'drive.usercontent.google.com' in url:
                            # Track all Google Drive failures for the recap
                            gdrive_ignored.append(mod)
                            self.log(f"  ✗ Failed to download (Google Drive): {mod.get('name')}", error=True)
                        else:
                            self.log(f"  ✗ Failed to download: {mod.get('name')}", error=True)
                except Exception as e:
                    self.log(f"  ✗ Download future error for {mod.get('name')}: {e}", error=True)
                completed += 1
                self.install_progress_bar['value'] = (completed / len(mods_to_download)) * 50  # downloads = first half
                self.root.update_idletasks()
        finally:
            # Clean up executor
            if self.current_executor:
                self.current_executor.shutdown(wait=True)
                self.current_executor = None
        
        # Check if installation was canceled during downloads
        if not self.is_installing:
            self.log("Installation aborted")
            self.install_modlist_btn.config(state=tk.NORMAL, text="Install Modlist")
            self.pause_install_btn.config(state=tk.DISABLED)
            return
        
        # Track Google Drive failures for recap
        all_gdrive_issues = gdrive_ignored

        # Step 2: sequential extraction
        self.log("Starting sequential extraction...")
        extracted = 0
        skipped = 0
        
        if not download_results:
            self.log("All mods were skipped (already installed or failed to download)", info=True)
            self.install_progress_bar['value'] = 100
        
        for i, (mod, temp_path, is_7z) in enumerate(download_results, 1):
            while self.is_paused:
                threading.Event().wait(0.1)
            mod_version = mod.get('version')
            if mod_version:
                self.log(f"\n[{i}/{len(download_results)}] Installing {mod['name']} v{mod_version}...")
            else:
                self.log(f"\n[{i}/{len(download_results)}] Installing {mod['name']}...")
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
                    skipped += 1
            except Exception as e:
                self.log(f"  ✗ Unexpected extraction error for {mod.get('name')}: {e}", error=True)
                skipped += 1
            # progress: second half (based on total attempted, not total in list)
            progress = 50 + ((extracted + skipped) / len(download_results)) * 50
            self.install_progress_bar['value'] = progress
            self.root.update_idletasks()

        # Final statistics
        self.install_progress_bar['value'] = 100
        
        # Calculate statistics correctly
        failed_downloads = total_mods - len(download_results) - len(all_gdrive_issues)
        already_installed = skipped  # skipped means already installed during extraction
        
        self.log("\n" + "=" * 50)
        self.log("Installation complete!")
        
        # Build detailed status message
        status_parts = []
        if extracted > 0:
            status_parts.append(f"{extracted} newly installed")
        if already_installed > 0:
            status_parts.append(f"{already_installed} already present")
        if failed_downloads > 0:
            status_parts.append(f"{failed_downloads} failed")
        if len(all_gdrive_issues) > 0:
            status_parts.append(f"{len(all_gdrive_issues)} Google Drive skipped/failed")
        
        if status_parts:
            self.log(f"  {', '.join(status_parts)}")
        
        if len(all_gdrive_issues) > 0:
            self.log("\nGoogle Drive mods not downloaded:")
            for mod in all_gdrive_issues:
                self.log(f"  - {mod.get('name')}", error=True)
        
        self.log("\nYou can now start Starsector to enable the mods.")

        self.is_installing = False
        self.install_modlist_btn.config(state=tk.NORMAL, text="Install Modlist")
        self.pause_install_btn.config(state=tk.DISABLED)

        # Propose to fix Google Drive URLs at the end
        if len(all_gdrive_issues) > 0:
            self._propose_fix_google_drive_urls(all_gdrive_issues)
        elif extracted > 0:
            # Show completion only if mods were installed and no Google Drive issues
            custom_dialogs.showinfo(
                "Installation complete",
                f"{extracted} mod(s) installed successfully!"
            )

    def _propose_fix_google_drive_urls(self, failed_mods):
        """Propose to fix Google Drive URLs after installation is complete.
        
        Args:
            failed_mods: List of mod dictionaries that failed to download
        """
        from gui.dialogs import fix_google_drive_url
        
        mod_names = [mod.get('name') for mod in failed_mods]
        
        self.log("\n" + "!" * 50)
        self.log(f"Google Drive URL fix available for {len(failed_mods)} mod(s)", error=True)
        self.log("!" * 50 + "\n")
        
        # Show trust warning if not already trusted
        if not self.trust_google_drive.get():
            response = custom_dialogs.askyesno(
                "Apply Google Drive URL Fix?",
                f"{len(failed_mods)} Google Drive mod(s) failed to download:\n{', '.join(mod_names)}\n\n"
                f"A URL fix can bypass Google's virus scan warning for large files.\n"
                f"Only proceed if you trust the mod author(s).\n\n"
                f"Apply the fix and retry downloading these mods?"
            )
            
            if not response:
                self.log("User declined to apply Google Drive URL fix")
                return
            
            # User accepted fix for this time (don't persist trust checkbox)
            self.log("User confirmed Google Drive URL fix")
        else:
            self.log("Google Drive trust already enabled, applying fix...")
        
        # Fix the URLs
        self.log("\nApplying Google Drive URL fix (temporary, config unchanged)...")
        fixed_count = 0
        fixed_mod_names = []
        fixed_mods_list = []  # Temporary list with fixed URLs for installation
        
        for failed_mod in failed_mods:
            original_url = failed_mod['download_url']
            fixed_url = fix_google_drive_url(original_url)
            
            if fixed_url != original_url:
                # Create a temporary copy with fixed URL (don't modify original config)
                mod_copy = failed_mod.copy()
                mod_copy['download_url'] = fixed_url
                fixed_mods_list.append(mod_copy)
                fixed_count += 1
                fixed_mod_names.append(failed_mod['name'])
                self.log(f"  ✓ Fixed URL for: {failed_mod['name']}")
        
        if fixed_count > 0:
            self.log(f"\n{fixed_count} Google Drive URL(s) fixed temporarily (config file unchanged)\n")
            
            # Ask if user wants to retry installation immediately
            retry_response = custom_dialogs.askyesno(
                "Retry Installation?",
                f"{fixed_count} URL(s) fixed.\n\nRetry installing now?\n(Only fixed mods will download)"
            )
            
            if retry_response:
                self.log(f"User chose to retry installation for: {', '.join(fixed_mod_names)}\n")
                # Trigger installation of only the fixed mods (with temporary fixed URLs)
                self.install_specific_mods(fixed_mod_names, temp_mods=fixed_mods_list)
            else:
                self.log("URLs fixed temporarily. User will retry installation manually later")
        else:
            custom_dialogs.showwarning(
                "No Changes",
                "No URLs could be automatically fixed."
            )

