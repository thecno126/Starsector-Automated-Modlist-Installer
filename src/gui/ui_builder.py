import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
from utils.theme import AppTheme
from utils.symbols import UISymbols
from core import UI_BOTTOM_BUTTON_HEIGHT
import platform


IS_MACOS = sys.platform == 'darwin'


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self._bind_events()
    
    def _bind_events(self):
        """Bind tooltip events to widget."""
        self.widget.bind("<Enter>", self.show_tooltip, add="+")
        self.widget.bind("<Leave>", self.hide_tooltip, add="+")
    
    def show_tooltip(self, event=None):
        if not self.text:
            return
        # Always hide any existing tooltip first
        self.hide_tooltip()
        
        try:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
        except:
            return
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                background=AppTheme.SURFACE_LIGHT, foreground=AppTheme.TEXT_PRIMARY,
                        relief=tk.SOLID, borderwidth=1, font=("Arial", 9))
        label.pack(ipadx=5, ipady=3)
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None


class ThemedButton(tk.Canvas):
    """Canvas-based button for macOS (standard tk.Button colors don't work reliably on macOS)."""
    
    def __init__(self, parent, text, command=None, bg=None, fg=None, 
                 activebackground=None, activeforeground=None, width=100, 
                 font=("Arial", 9, "bold"), state=tk.NORMAL, **kwargs):
        font_size = font[1] if isinstance(font, tuple) else 9
        height = font_size + 16
        kwargs.pop('state', None)
        self.requested_width = width
        
        super().__init__(parent, width=width, height=height, 
                highlightthickness=0, bg=bg or AppTheme.PRIMARY, **kwargs)
        
        self.command = command
        self.bg_color = bg or AppTheme.PRIMARY
        self.fg_color = fg or AppTheme.SURFACE_DARK
        self.active_bg = activebackground or self.bg_color
        self.active_fg = activeforeground or self.fg_color
        self.text = text
        self.font = font
        self.is_pressed = False
        self.is_disabled = (state == tk.DISABLED)
        
        self.rect = self.create_rectangle(0, 0, width, height, 
                                          fill=self.bg_color, outline="", width=0)
        self.text_item = self.create_text(width//2, height//2, text=text, 
                                         fill=self.fg_color, font=font)
        
        self.bind("<Configure>", self._on_resize)
        
        if self.is_disabled:
            self.itemconfig(self.rect, fill=AppTheme.SURFACE_LIGHT)
            self.itemconfig(self.text_item, fill=AppTheme.TEXT_DISABLED)
        else:
            self.bind("<Button-1>", self.on_press)
            self.bind("<ButtonRelease-1>", self.on_release)
            self.bind("<Enter>", self.on_enter)
            self.bind("<Leave>", self.on_leave)
    
    def _on_resize(self, event):
        width = event.width
        height = event.height
        self.coords(self.rect, 0, 0, width, height)
        self.coords(self.text_item, width//2, height//2)
    
    def on_press(self, event):
        self.is_pressed = True
        self.itemconfig(self.rect, fill=self.active_bg)
        self.itemconfig(self.text_item, fill=self.active_fg)
    
    def on_release(self, event):
        if self.is_pressed and self.command:
            self.command()
        self.is_pressed = False
        try:
            x, y = event.x, event.y
            width = self.winfo_width()
            height = self.winfo_height()
            if 0 <= x <= width and 0 <= y <= height:
                self.itemconfig(self.rect, fill=self.active_bg)
                self.itemconfig(self.text_item, fill=self.active_fg)
            else:
                self.itemconfig(self.rect, fill=self.bg_color)
                self.itemconfig(self.text_item, fill=self.fg_color)
        except tk.TclError:
            pass
    
    def on_enter(self, event):
        if not self.is_pressed:
            self.itemconfig(self.rect, fill=self.active_bg)
            self.itemconfig(self.text_item, fill=self.active_fg)
    
    def on_leave(self, event):
        if not self.is_pressed:
            self.itemconfig(self.rect, fill=self.bg_color)
            self.itemconfig(self.text_item, fill=self.fg_color)
    
    def configure(self, **kwargs):
        if 'command' in kwargs:
            self.command = kwargs.pop('command')
        
        if 'text' in kwargs:
            new_text = kwargs.pop('text')
            self.text = new_text
            self.itemconfig(self.text_item, text=new_text)
        
        if 'state' in kwargs:
            if kwargs['state'] == tk.DISABLED:
                self.is_disabled = True
                self.itemconfig(self.rect, fill=AppTheme.SURFACE_LIGHT)
                self.itemconfig(self.text_item, fill=AppTheme.TEXT_DISABLED)
                self.unbind("<Button-1>")
                self.unbind("<ButtonRelease-1>")
                self.unbind("<Enter>")
                self.unbind("<Leave>")
            elif kwargs['state'] == tk.NORMAL:
                self.is_disabled = False
                self.itemconfig(self.rect, fill=self.bg_color)
                self.itemconfig(self.text_item, fill=self.fg_color)
                self.bind("<Button-1>", self.on_press)
                self.bind("<ButtonRelease-1>", self.on_release)
                self.bind("<Enter>", self.on_enter)
                self.bind("<Leave>", self.on_leave)
            kwargs = {k: v for k, v in kwargs.items() if k != 'state'}
        
        if kwargs:  # Only call super if there are remaining kwargs
            super().configure(**kwargs)
    
    config = configure  # Alias


def _create_button(parent, text, command, width=10, font_size=9, button_type="primary", **kwargs):
    style = AppTheme.get_button_style(button_type)
    
    if IS_MACOS:
        pixel_width = max(width * 9, len(text) * 8 + 20)
        return ThemedButton(
            parent, text=text, command=command,
            bg=style.get('bg'), fg=style.get('fg'),
            activebackground=style.get('activebackground'),
            activeforeground=style.get('activeforeground'),
            width=pixel_width, font=("Arial", font_size, "bold")
        )
    else:
        style.update({'relief': tk.FLAT, 'borderwidth': 1, 'highlightthickness': 0, 'padx': 8, 'pady': 5})
        style.update(kwargs)
        return tk.Button(parent, text=text, command=command, 
                        font=("Arial", font_size, "bold"), width=width, **style)


def create_header(root):
    """Create the header frame with title."""
    header_frame = tk.Frame(root, height=50, bg=AppTheme.SURFACE)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)
    
    title_label = tk.Label(
        header_frame,
        text="Modlist Installer",
        font=("Arial", 14, "bold"),
        bg=AppTheme.SURFACE,
        fg=AppTheme.PRIMARY
    )
    title_label.pack(pady=10)
    
    return header_frame


def create_path_section(main_frame, path_var, browse_callback):
    """Create the Starsector path selection section."""
    path_frame = tk.LabelFrame(main_frame, text="Starsector Installation Path", padx=5, pady=5,
                              bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY)
    path_frame.pack(fill=tk.X, pady=(0, 5))
    
    path_container = tk.Frame(path_frame, bg=AppTheme.SURFACE)
    path_container.pack(fill=tk.X)
    
    path_entry = tk.Entry(
        path_container,
        textvariable=path_var,
        font=("Arial", 10),
        bg=AppTheme.SURFACE_DARK,
        fg=AppTheme.TEXT_PRIMARY,
        insertbackground=AppTheme.PRIMARY,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=AppTheme.BORDER,
        highlightcolor=AppTheme.PRIMARY
    )
    path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    
    browse_btn = _create_button(path_container, "Browse...", browse_callback, button_type="secondary")
    browse_btn.pack(side=tk.RIGHT)
    
    path_status_label = tk.Label(
        path_frame,
        text="",
        font=("Arial", 8),
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_SECONDARY
    )
    path_status_label.pack(fill=tk.X, pady=(3, 0))
    
    return path_frame, path_entry, browse_btn, path_status_label


def create_modlist_section(main_frame, mod_click_callback, pane_resize_callback, search_callback=None, import_callback=None, export_callback=None, refresh_callback=None, restore_callback=None, clear_callback=None, edit_metadata_callback=None, import_preset_callback=None, patch_lunalib_callback=None):
    """Create the modlist information section with optional search and action buttons."""
    # Container for the whole section
    section_container = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    section_container.pack(fill=tk.BOTH, expand=True)
    
    # Top bar with action buttons (above LabelFrame)
    header_buttons = {}
    if import_callback or export_callback or refresh_callback or edit_metadata_callback or import_preset_callback or patch_lunalib_callback:
        top_bar = tk.Frame(section_container, bg=AppTheme.SURFACE)
        top_bar.pack(fill=tk.X, pady=(0, 3))
        
        # Spacer to push buttons to the right
        tk.Frame(top_bar, bg=AppTheme.SURFACE).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        button_container = tk.Frame(top_bar, bg=AppTheme.SURFACE)
        button_container.pack(side=tk.RIGHT)
        
        if edit_metadata_callback:
            edit_metadata_btn = _create_button(button_container, UISymbols.FILE, edit_metadata_callback, width=3, font_size=16, button_type="secondary")
            edit_metadata_btn.pack(side=tk.LEFT, padx=(0, 8))
            ToolTip(edit_metadata_btn, "Edit modlist infos")
            header_buttons['edit_metadata'] = edit_metadata_btn
        
        if import_preset_callback:
            import_preset_btn = _create_button(button_container, UISymbols.OPEN_FOLDER, import_preset_callback, width=3, font_size=16, button_type="secondary")
            import_preset_btn.pack(side=tk.LEFT, padx=(0, 8))
            ToolTip(import_preset_btn, "Import modlist")
            header_buttons['import_preset'] = import_preset_btn

        if restore_callback:
            export_modlist_btn = _create_button(button_container, UISymbols.SAVE, restore_callback, width=3, font_size=16, button_type="secondary")
            export_modlist_btn.pack(side=tk.LEFT, padx=(0, 8))
            ToolTip(export_modlist_btn, "Export modlist")
            header_buttons['export_modlist'] = export_modlist_btn
    
    # LabelFrame with title
    info_frame = tk.LabelFrame(section_container, text="Current Modlist", padx=5, pady=5,
                              bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY)
    info_frame.pack(fill=tk.BOTH, expand=True)
    
    left_container = tk.Frame(info_frame, bg=AppTheme.SURFACE)
    left_container.pack(fill=tk.BOTH, expand=True)
    
    # Mod counter label positioned in top-right corner using place (created after left_container to be on top)
    modlist_title_var = tk.StringVar(value="")
    mod_counter_label = tk.Label(info_frame, textvariable=modlist_title_var,
                                font=("Arial", 9, "italic"), bg=AppTheme.SURFACE, fg=AppTheme.PRIMARY)
    mod_counter_label.place(relx=1.0, x=-10, y=2, anchor=tk.NE)
    mod_counter_label.lift()  # Ensure it's on top
    
    header_text = tk.Text(
        left_container, 
        height=5, 
        wrap=tk.WORD, 
        state=tk.DISABLED,
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_PRIMARY,
        insertbackground=AppTheme.PRIMARY,
        relief=tk.FLAT,
        highlightthickness=0,
        borderwidth=0
    )
    header_text.pack(fill=tk.X, pady=(0, 5))
    
    search_var = None
    mod_action_buttons = {}
    if search_callback:
        search_frame = tk.Frame(left_container, bg=AppTheme.SURFACE)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(search_frame, text=UISymbols.SEARCH, font=("Arial", 12),
                bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY).pack(side=tk.LEFT, padx=(0, 5))
        
        # Clear button right after magnifying glass
        clear_btn = _create_button(search_frame, UISymbols.CLEAR, lambda: search_var.set(""),
                                   width=3, font_size=10, button_type="secondary")
        clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        ToolTip(clear_btn, "Clear search")
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Arial", 10),
                               bg=AppTheme.SURFACE_DARK, fg=AppTheme.TEXT_PRIMARY,
                               insertbackground=AppTheme.PRIMARY, relief=tk.FLAT,
                               highlightthickness=1, highlightbackground=AppTheme.BORDER,
                               highlightcolor=AppTheme.PRIMARY)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Action buttons from right to left: Remove, Add, Categories, Edit
        remove_btn = _create_button(search_frame, UISymbols.MINUS, None, width=3, font_size=16, button_type="secondary")
        remove_btn.pack(side=tk.RIGHT, padx=(2, 0))
        ToolTip(remove_btn, "Remove selected mod")
        
        add_btn = _create_button(search_frame, UISymbols.PLUS, None, width=3, font_size=16, button_type="secondary")
        add_btn.pack(side=tk.RIGHT, padx=2)
        ToolTip(add_btn, "Add new mod to the list")
        
        gear_btn = _create_button(search_frame, UISymbols.SETTINGS, None, width=3, font_size=16, button_type="secondary")
        gear_btn.pack(side=tk.RIGHT, padx=2)
        ToolTip(gear_btn, "Manage categories")
        
        edit_btn = _create_button(search_frame, UISymbols.EDIT_METADATA, None, width=3, font_size=16, button_type="plain")
        edit_btn.pack(side=tk.RIGHT, padx=2)
        ToolTip(edit_btn, "Edit selected mod")
        
        mod_action_buttons = {'add': add_btn, 'edit': edit_btn, 'remove': remove_btn, 'categories': gear_btn}
        
        # Bind search callback
        search_var.trace_add('write', lambda *args: search_callback(search_var.get()))
    
    # Modlist container with scrollbar
    list_container = tk.Frame(left_container, bg=AppTheme.SURFACE)
    list_container.pack(fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(list_container, bg=AppTheme.SURFACE)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    mod_listbox = tk.Text(
        list_container, 
        yscrollcommand=scrollbar.set, 
        height=20, 
        font=("Courier", 11),
        wrap=tk.WORD,
        state=tk.DISABLED,
        cursor="arrow",
        bg=AppTheme.SURFACE_DARK,
        fg=AppTheme.TEXT_PRIMARY,
        insertbackground=AppTheme.PRIMARY,
        selectbackground=AppTheme.PRIMARY,
        selectforeground=AppTheme.SURFACE_DARK,
        relief=tk.FLAT,
        highlightthickness=0,
        borderwidth=0
    )
    mod_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=mod_listbox.yview)
    
    mod_listbox.bind('<Button-1>', mod_click_callback)
    
    # Bottom action bar: Reorder buttons + Restore/Clear
    bottom_bar = tk.Frame(left_container, bg=AppTheme.SURFACE)
    bottom_bar.pack(fill=tk.X, pady=(5, 0))
    
    # Left side: Reorder buttons
    reorder_container = tk.Frame(bottom_bar, bg=AppTheme.SURFACE)
    reorder_container.pack(side=tk.LEFT)
    
    tk.Label(reorder_container, text="Reorder:", font=("Arial", 9),
            bg=AppTheme.SURFACE, fg=AppTheme.TEXT_SECONDARY).pack(side=tk.LEFT, padx=(0, 5))
    
    up_btn = _create_button(reorder_container, UISymbols.ARROW_UP, None, width=3, font_size=16, button_type="secondary")
    up_btn.pack(side=tk.LEFT, padx=(0, 2))
    ToolTip(up_btn, "Move selected mod up")
    header_buttons['up'] = up_btn
    
    down_btn = _create_button(reorder_container, UISymbols.ARROW_DOWN, None, width=3, font_size=16, button_type="secondary")
    down_btn.pack(side=tk.LEFT)
    ToolTip(down_btn, "Move selected mod down")
    header_buttons['down'] = down_btn
    
    # Right side: Refresh and Clear All buttons
    action_container = tk.Frame(bottom_bar, bg=AppTheme.SURFACE)
    action_container.pack(side=tk.RIGHT)
    
    if clear_callback:
        clear_all_btn = _create_button(action_container, UISymbols.REMOVE, clear_callback, width=3, font_size=16, button_type="secondary")
        clear_all_btn.pack(side=tk.RIGHT, padx=(3, 0))
        # Add red border outline
        clear_all_btn.configure(highlightthickness=0.5, highlightbackground=AppTheme.ERROR, highlightcolor=AppTheme.ERROR)
        ToolTip(clear_all_btn, "Wipe modlist (mods + infos)")
        header_buttons['clear'] = clear_all_btn

    if refresh_callback:
        refresh_btn = _create_button(action_container, UISymbols.REFRESH, refresh_callback, width=3, font_size=16, button_type="secondary")
        refresh_btn.pack(side=tk.RIGHT, padx=(0, 3))
        # Add blue border outline
        refresh_btn.configure(highlightthickness=0.5, highlightbackground=AppTheme.INFO, highlightcolor=AppTheme.INFO)
        ToolTip(refresh_btn, "Refresh mods infos (from .json)")
        header_buttons['refresh'] = refresh_btn  

    # Return container and left_container so buttons can be added first
    return info_frame, left_container, header_text, mod_listbox, search_var, mod_action_buttons, header_buttons, modlist_title_var


def create_log_section(main_frame, current_mod_var=None, pause_callback=None, enable_mods_callback=None):
    """Create the log section with progress bar, pause/resume button, and optional current mod label."""
    log_frame = tk.LabelFrame(main_frame, text="Installation Log", padx=5, pady=5,
                             bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
    
    # Top bar with current mod label and pause button
    top_bar = tk.Frame(log_frame, bg=AppTheme.SURFACE)
    top_bar.pack(fill=tk.X, pady=(0, 3))
    
    # Current mod label (if variable provided)
    if current_mod_var:
        current_mod_label = tk.Label(
            top_bar,
            textvariable=current_mod_var,
            font=("Arial", 9, "italic"),
            fg=AppTheme.PRIMARY,
            bg=AppTheme.SURFACE,
            anchor=tk.W
        )
        current_mod_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # Pause/Resume button in top right
    pause_btn = None
    if pause_callback:
        pause_btn = _create_button(top_bar, UISymbols.PAUSE, pause_callback, width=4, font_size=14, 
                                   state=tk.DISABLED, button_type="secondary")
        pause_btn.pack(side=tk.RIGHT)
        ToolTip(pause_btn, "Pause installation")
    
    progress_bar = ttk.Progressbar(log_frame, mode='determinate')
    progress_bar.pack(fill=tk.X, pady=(0, 5))
    
    log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED, height=40, width=130,
                                         bg=AppTheme.SURFACE_DARK, fg=AppTheme.TEXT_PRIMARY,
                                         insertbackground=AppTheme.PRIMARY,
                                         relief=tk.FLAT, highlightthickness=0, borderwidth=0)
    log_text.pack(fill=tk.BOTH, expand=True)
    
    return log_frame, progress_bar, log_text, pause_btn


def create_enable_mods_section(main_frame, enable_mods_callback, patch_lunalib_callback=None):
    """Create the Enable All Mods button section between log and bottom buttons."""
    # Use exact same structure as create_bottom_buttons for perfect alignment
    enable_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    enable_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
    enable_frame.configure(height=UI_BOTTOM_BUTTON_HEIGHT)
    enable_frame.pack_propagate(False)
    
    button_container = tk.Frame(enable_frame, bg=AppTheme.SURFACE)
    button_container.pack(fill=tk.BOTH, expand=True, padx=50)
    
    # Enable All Mods button (left side)
    enable_mods_btn = _create_button(button_container, "Enable All Mods", enable_mods_callback, height=1, button_type="starsector_blue")
    enable_mods_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ToolTip(enable_mods_btn, "Activate all installed mods in Starsector")
    
    # Lunalib Patch button (right side) if callback provided
    patch_lunalib_btn = None
    if patch_lunalib_callback:
        patch_lunalib_btn = _create_button(button_container, "Apply Lunalib Patch", patch_lunalib_callback, height=1, button_type="pastel_purple")
        patch_lunalib_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        ToolTip(patch_lunalib_btn, "Patch LunaSettings from preset")
    
    return enable_frame, enable_mods_btn, patch_lunalib_btn


def create_bottom_buttons(main_frame, install_callback, quit_callback):
    """Create the bottom button panel with Install and Quit."""
    button_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    button_frame.configure(height=UI_BOTTOM_BUTTON_HEIGHT)
    button_frame.pack_propagate(False)

    button_container = tk.Frame(button_frame, bg=AppTheme.SURFACE)
    button_container.pack(fill=tk.BOTH, expand=True, padx=50)
    button_container.columnconfigure(0, weight=1)
    button_container.columnconfigure(1, weight=1)

    install_btn = _create_button(button_container, "Install Modlist", install_callback, height=1, button_type="success")
    install_btn.grid(row=0, column=0, sticky="we", padx=(0, 3))
    ToolTip(install_btn, "Start downloading and installing all mods")

    quit_btn = _create_button(button_container, "Quit", quit_callback, height=1, button_type="danger")
    quit_btn.grid(row=0, column=1, sticky="we", padx=(3, 0))
    ToolTip(quit_btn, "Exit the application")
    
    return button_frame, install_btn, quit_btn
