"""
UI builder for the Modlist Installer application.
Contains functions to create the user interface components.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
from utils.theme import TriOSTheme

from core import (
    UI_BOTTOM_BUTTON_HEIGHT
)

# Detect macOS
IS_MACOS = sys.platform == 'darwin'


class ThemedButton(tk.Canvas):
    """Custom button widget that respects colors on macOS."""
    
    def __init__(self, parent, text, command=None, bg=None, fg=None, 
                 activebackground=None, activeforeground=None, width=100, 
                 font=("Arial", 9, "bold"), state=tk.NORMAL, **kwargs):
        # Calculate height from font size
        font_size = font[1] if isinstance(font, tuple) else 9
        height = font_size + 16
        
        # Remove 'state' from kwargs if it exists
        kwargs.pop('state', None)
        
        # Store width to handle dynamic resizing
        self.requested_width = width
        
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, bg=bg or TriOSTheme.PRIMARY, **kwargs)
        
        self.command = command
        self.bg_color = bg or TriOSTheme.PRIMARY
        self.fg_color = fg or TriOSTheme.SURFACE_DARK
        self.active_bg = activebackground or self.bg_color
        self.active_fg = activeforeground or self.fg_color
        self.text = text
        self.font = font
        self.is_pressed = False
        self.is_disabled = (state == tk.DISABLED)
        
        # Draw button
        self.rect = self.create_rectangle(0, 0, width, height, 
                                          fill=self.bg_color, outline="", width=0)
        self.text_item = self.create_text(width//2, height//2, text=text, 
                                         fill=self.fg_color, font=font)
        
        # Bind to configure event to redraw on resize
        self.bind("<Configure>", self._on_resize)
        
        # Apply initial state
        if self.is_disabled:
            self.itemconfig(self.rect, fill=TriOSTheme.SURFACE_LIGHT)
            self.itemconfig(self.text_item, fill=TriOSTheme.TEXT_DISABLED)
        else:
            # Bind events only if not disabled
            self.bind("<Button-1>", self.on_press)
            self.bind("<ButtonRelease-1>", self.on_release)
            self.bind("<Enter>", self.on_enter)
            self.bind("<Leave>", self.on_leave)
    
    def _on_resize(self, event):
        """Redraw button when canvas is resized."""
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
        # Check if mouse is still over button (protect against widget destruction)
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
            # Widget was destroyed, ignore
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
        """Allow configuration like normal widgets."""
        if 'text' in kwargs:
            # Handle text changes
            new_text = kwargs.pop('text')
            self.text = new_text
            self.itemconfig(self.text_item, text=new_text)
        
        if 'state' in kwargs:
            # Handle state changes (for disable/enable)
            if kwargs['state'] == tk.DISABLED:
                self.is_disabled = True
                self.itemconfig(self.rect, fill=TriOSTheme.SURFACE_LIGHT)
                self.itemconfig(self.text_item, fill=TriOSTheme.TEXT_DISABLED)
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


# Helper function to create buttons with consistent styling
def _create_button(parent, text, command, width=10, font_size=9, button_type="primary", **kwargs):
    """Create a standard button with consistent styling using TriOS theme."""
    style = TriOSTheme.get_button_style(button_type)
    
    if IS_MACOS:
        # Use custom Canvas-based button for macOS
        # Augmenter la largeur pour éviter le crop du texte
        pixel_width = max(width * 9, len(text) * 8 + 20)  # Plus de marge pour le texte
        return ThemedButton(
            parent, 
            text=text, 
            command=command,
            bg=style.get('bg'),
            fg=style.get('fg'),
            activebackground=style.get('activebackground'),
            activeforeground=style.get('activeforeground'),
            width=pixel_width,
            font=("Arial", font_size, "bold")
        )
    else:
        # Use standard tk.Button for other platforms
        style.update({
            'relief': tk.FLAT,
            'borderwidth': 1,
            'highlightthickness': 0,
            'padx': 8,
            'pady': 5
        })
        style.update(kwargs)
        return tk.Button(parent, text=text, command=command, 
                        font=("Arial", font_size, "bold"), width=width, **style)


def create_header(root):
    """Create the header frame with title."""
    header_frame = tk.Frame(root, height=50, bg=TriOSTheme.SURFACE)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)
    
    title_label = tk.Label(
        header_frame,
        text="Modlist Installer",
        font=("Arial", 14, "bold"),
        bg=TriOSTheme.SURFACE,
        fg=TriOSTheme.PRIMARY
    )
    title_label.pack(pady=10)
    
    return header_frame


def create_path_section(main_frame, path_var, browse_callback):
    """Create the Starsector path selection section."""
    path_frame = tk.LabelFrame(main_frame, text="Starsector Installation Path", padx=5, pady=5,
                              bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY)
    path_frame.pack(fill=tk.X, pady=(0, 5))
    
    path_container = tk.Frame(path_frame, bg=TriOSTheme.SURFACE)
    path_container.pack(fill=tk.X)
    
    path_entry = tk.Entry(
        path_container,
        textvariable=path_var,
        font=("Arial", 10),
        bg=TriOSTheme.SURFACE_DARK,
        fg=TriOSTheme.TEXT_PRIMARY,
        insertbackground=TriOSTheme.PRIMARY,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=TriOSTheme.BORDER,
        highlightcolor=TriOSTheme.PRIMARY
    )
    path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    
    browse_btn = _create_button(path_container, "Browse...", browse_callback, button_type="secondary")
    browse_btn.pack(side=tk.RIGHT)
    
    path_status_label = tk.Label(
        path_frame,
        text="",
        font=("Arial", 8),
        bg=TriOSTheme.SURFACE,
        fg=TriOSTheme.TEXT_SECONDARY
    )
    path_status_label.pack(fill=tk.X, pady=(3, 0))
    
    return path_frame, path_entry, browse_btn, path_status_label


def create_modlist_section(main_frame, mod_click_callback, pane_resize_callback, search_callback=None):
    """Create the modlist information section with optional search."""
    info_frame = tk.LabelFrame(main_frame, text="Current Modlist", padx=5, pady=5,
                              bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY)
    info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
    
    # Horizontal container for modlist and buttons
    main_container = tk.Frame(info_frame, bg=TriOSTheme.SURFACE)
    main_container.pack(fill=tk.BOTH, expand=True)
    
    # NOTE: Right side (buttons) must be created first with pack(side=tk.RIGHT)
    # Then left side (modlist) with pack(side=tk.LEFT, expand=True)
    # This is done by caller: first create_modlist_section, then create_button_panel
    
    # Left side: Header and modlist (will be packed after buttons are created)
    left_container = tk.Frame(main_container, bg=TriOSTheme.SURFACE)
    
    # Header text - uses system theme colors
    header_text = tk.Text(
        left_container, 
        height=4, 
        wrap=tk.WORD, 
        state=tk.DISABLED,
        bg=TriOSTheme.SURFACE_DARK,
        fg=TriOSTheme.TEXT_PRIMARY,
        insertbackground=TriOSTheme.PRIMARY,
        relief=tk.FLAT,
        highlightthickness=0,
        borderwidth=0
    )
    header_text.pack(fill=tk.X, pady=(0, 5))
    
    # Search bar (if callback provided)
    search_var = None
    if search_callback:
        search_frame = tk.Frame(left_container, bg=TriOSTheme.SURFACE)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(search_frame, text="🔍", font=("Arial", 12),
                bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).pack(side=tk.LEFT, padx=(0, 5))
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Arial", 10),
                               bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                               insertbackground=TriOSTheme.PRIMARY, relief=tk.FLAT,
                               highlightthickness=1, highlightbackground=TriOSTheme.BORDER,
                               highlightcolor=TriOSTheme.PRIMARY)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        clear_btn = _create_button(search_frame, "✕", lambda: search_var.set(""),
                                   width=3, font_size=10, button_type="secondary")
        clear_btn.pack(side=tk.RIGHT)
        
        # Bind search callback
        search_var.trace_add('write', lambda *args: search_callback(search_var.get()))
    
    # Modlist container with scrollbar
    list_container = tk.Frame(left_container, bg=TriOSTheme.SURFACE)
    list_container.pack(fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(list_container, bg=TriOSTheme.SURFACE)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    mod_listbox = tk.Text(
        list_container, 
        yscrollcommand=scrollbar.set, 
        height=6, 
        font=("Courier", 11),
        wrap=tk.WORD,
        state=tk.DISABLED,
        cursor="arrow",
        bg=TriOSTheme.SURFACE_DARK,
        fg=TriOSTheme.TEXT_PRIMARY,
        insertbackground=TriOSTheme.PRIMARY,
        selectbackground=TriOSTheme.PRIMARY,
        selectforeground=TriOSTheme.SURFACE_DARK,
        relief=tk.FLAT,
        highlightthickness=0,
        borderwidth=0
    )
    mod_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=mod_listbox.yview)
    
    mod_listbox.bind('<Button-1>', mod_click_callback)
    
    # Return container and left_container so buttons can be added first
    return info_frame, main_container, left_container, header_text, mod_listbox, search_var


def create_button_panel(main_container, left_container, callbacks):
    """
    Create the right-side button panel.
    
    Args:
        main_container: The main container Frame
        left_container: The left container Frame (will be packed after buttons)
        callbacks: Dictionary with callback functions for each button
    """
    # Create buttons on the right FIRST
    right_frame = tk.Frame(main_container, width=100, bg=TriOSTheme.SURFACE)
    right_frame.pack(side=tk.RIGHT, fill=tk.Y)
    right_frame.pack_propagate(False)
    
    # NOW pack the left container to fill remaining space
    left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
    
    # Installation section
    install_section = tk.LabelFrame(right_frame, text="Installation", padx=5, pady=5,
                                   bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY)
    install_section.pack(fill=tk.X, pady=(0, 5))
    
    reset_btn = _create_button(install_section, "Reset", callbacks['reset'], button_type="danger")
    reset_btn.pack(pady=(0, 3), fill=tk.X)
    
    pause_btn = _create_button(install_section, "Pause", callbacks['pause'], state=tk.DISABLED, button_type="warning")
    pause_btn.pack(pady=(0, 0), fill=tk.X)
    
    # Reorder section
    reorder_section = tk.LabelFrame(right_frame, text="Reorder", padx=5, pady=3,
                                   bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY)
    reorder_section.pack(fill=tk.X, pady=(0, 5))
    
    up_btn = _create_button(reorder_section, "↑", callbacks['move_up'], width=3, font_size=11, button_type="secondary")
    up_btn.pack(pady=(0, 3))
    
    down_btn = _create_button(reorder_section, "↓", callbacks['move_down'], width=3, font_size=11, button_type="secondary")
    down_btn.pack(pady=(3, 0))
    
    # Management section
    management_section = tk.LabelFrame(right_frame, text="Management", padx=5, pady=8,
                                      bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY)
    management_section.pack(fill=tk.X, pady=(0, 5))
    
    # Refresh button with icon and no background, directly under Management title
    refresh_container = tk.Frame(management_section, bg=TriOSTheme.SURFACE)
    refresh_container.pack(pady=(0, 8), fill=tk.X)
    
    if IS_MACOS:
        refresh_btn = ThemedButton(refresh_container, "↻", command=callbacks['refresh'],
                                  bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY,
                                  activebackground=TriOSTheme.SURFACE_LIGHT, activeforeground=TriOSTheme.TEXT_PRIMARY,
                                  font=("Arial", 14))
    else:
        refresh_btn = tk.Button(refresh_container, text="↻", command=callbacks['refresh'],
                               bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY,
                               activebackground=TriOSTheme.SURFACE_LIGHT, activeforeground=TriOSTheme.TEXT_PRIMARY,
                               relief=tk.FLAT, font=("Arial", 14), cursor="hand2")
    refresh_btn.pack(fill=tk.X)
    
    categories_btn = _create_button(management_section, "Categories", callbacks['categories'], button_type="plain")
    categories_btn.pack(pady=(0, 3), fill=tk.X)
    
    add_btn = _create_button(management_section, "Add Mod", callbacks['add'], button_type="plain")
    add_btn.pack(pady=(0, 3), fill=tk.X)
    
    edit_btn = _create_button(management_section, "Edit Mod", callbacks['edit'], button_type="plain")
    edit_btn.pack(pady=(0, 3), fill=tk.X)
    
    remove_btn = _create_button(management_section, "Remove Mod", callbacks['remove'], button_type="plain")
    remove_btn.pack(pady=(0, 3), fill=tk.X)

    import_btn = _create_button(management_section, "Import CSV", callbacks['import_csv'], button_type="plain")
    import_btn.pack(pady=(0, 3), fill=tk.X)

    export_btn = _create_button(management_section, "Export CSV", callbacks['export_csv'], button_type="plain")
    export_btn.pack(pady=(0, 3), fill=tk.X)
    
    restore_backup_btn = _create_button(management_section, "Restore Backup", callbacks.get('restore_backup', lambda: None), button_type="warning")
    restore_backup_btn.pack(pady=(0, 3), fill=tk.X)
    
    enable_mods_btn = _create_button(management_section, "Enable All Mods", callbacks.get('enable_mods', lambda: None), button_type="success")
    enable_mods_btn.pack(pady=(0, 0), fill=tk.X)
    
    return {
        'reset': reset_btn,
        'pause': pause_btn,
        'up': up_btn,
        'down': down_btn,
        'categories': categories_btn,
        'add': add_btn,
        'edit': edit_btn,
        'remove': remove_btn,
        'import': import_btn,
        'export': export_btn,
        'refresh': refresh_btn,
        'enable_mods': enable_mods_btn,
        'restore_backup': restore_backup_btn
    }


def create_log_section(main_frame, current_mod_var=None):
    """Create the log section with progress bar and optional current mod label."""
    log_frame = tk.LabelFrame(main_frame, text="Installation Log", padx=5, pady=5,
                             bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY)
    log_frame.pack(fill=tk.BOTH, expand=True)
    
    # Current mod label (if variable provided)
    if current_mod_var:
        current_mod_label = tk.Label(
            log_frame,
            textvariable=current_mod_var,
            font=("Arial", 9, "italic"),
            fg=TriOSTheme.PRIMARY,
            bg=TriOSTheme.SURFACE,
            anchor=tk.W
        )
        current_mod_label.pack(fill=tk.X, pady=(0, 3))
    
    progress_bar = ttk.Progressbar(log_frame, mode='determinate')
    progress_bar.pack(fill=tk.X, pady=(0, 5))
    
    log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED, height=40, width=130,
                                         bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                                         insertbackground=TriOSTheme.PRIMARY,
                                         relief=tk.FLAT, highlightthickness=0, borderwidth=0)
    log_text.pack(fill=tk.BOTH, expand=True)
    
    return log_frame, progress_bar, log_text


def create_bottom_buttons(main_frame, install_callback, quit_callback):
    """Create the bottom button panel."""
    button_frame = tk.Frame(main_frame, bg=TriOSTheme.SURFACE)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X)
    button_frame.configure(height=UI_BOTTOM_BUTTON_HEIGHT)
    button_frame.pack_propagate(False)

    button_container = tk.Frame(button_frame, bg=TriOSTheme.SURFACE)
    button_container.pack(fill=tk.BOTH, expand=True)
    button_container.columnconfigure(0, weight=1)
    button_container.columnconfigure(1, weight=1)

    install_btn = _create_button(button_container, "Install Modlist", install_callback, height=1, button_type="success")
    install_btn.grid(row=0, column=0, sticky="we", padx=(0, 3))

    quit_btn = _create_button(button_container, "Quit", quit_callback, height=1, button_type="danger")
    quit_btn.grid(row=0, column=1, sticky="we", padx=(3, 0))
    
    return button_frame, install_btn, quit_btn
