"""
UI builder for the Modlist Installer application.
Contains functions to create the user interface components.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext


# Helper function to create buttons with consistent styling
def _create_button(parent, text, command, width=10, font_size=9, **kwargs):
    """Create a standard button with consistent styling."""
    return tk.Button(parent, text=text, command=command, 
                    font=("Arial", font_size, "bold"), width=width, **kwargs)


def create_header(root):
    """Create the header frame with title."""
    header_frame = tk.Frame(root, height=50)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)
    
    title_label = tk.Label(
        header_frame,
        text="Modlist Installer",
        font=("Arial", 14, "bold")
    )
    title_label.pack(pady=10)
    
    return header_frame


def create_path_section(main_frame, path_var, browse_callback):
    """Create the Starsector path selection section."""
    path_frame = tk.LabelFrame(main_frame, text="Starsector Installation Path", padx=5, pady=5)
    path_frame.pack(fill=tk.X, pady=(0, 5))
    
    path_container = tk.Frame(path_frame)
    path_container.pack(fill=tk.X)
    
    path_entry = tk.Entry(
        path_container,
        textvariable=path_var,
        font=("Arial", 10)
    )
    path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    
    browse_btn = _create_button(path_container, "Browse...", browse_callback)
    browse_btn.pack(side=tk.RIGHT)
    
    path_status_label = tk.Label(
        path_frame,
        text="",
        font=("Arial", 8)
    )
    path_status_label.pack(fill=tk.X, pady=(3, 0))
    
    return path_frame, path_entry, browse_btn, path_status_label


def create_modlist_section(main_frame, mod_click_callback, pane_resize_callback):
    """Create the modlist information section."""
    info_frame = tk.LabelFrame(main_frame, text="Current Modlist", padx=5, pady=5)
    info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
    
    # Single PanedWindow for both header and modlist
    main_paned = tk.PanedWindow(info_frame, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED)
    main_paned.pack(fill=tk.BOTH, expand=True)
    
    # Left side: Header and modlist
    left_container = tk.Frame(main_paned)
    main_paned.add(left_container, stretch="always")
    
    # Header text - uses system theme colors
    header_text = tk.Text(
        left_container, 
        height=4, 
        wrap=tk.WORD, 
        state=tk.DISABLED
    )
    header_text.pack(fill=tk.X, pady=(0, 5))
    
    # Modlist container with scrollbar
    list_container = tk.Frame(left_container)
    list_container.pack(fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(list_container)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    mod_listbox = tk.Text(
        list_container, 
        yscrollcommand=scrollbar.set, 
        height=6, 
        font=("Courier", 11),
        wrap=tk.WORD,
        state=tk.DISABLED,
        cursor="arrow"
    )
    mod_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=mod_listbox.yview)
    
    mod_listbox.bind('<Button-1>', mod_click_callback)
    main_paned.bind('<ButtonRelease-1>', pane_resize_callback)
    
    return info_frame, main_paned, header_text, mod_listbox


def create_button_panel(main_paned, callbacks):
    """
    Create the right-side button panel.
    
    Args:
        main_paned: The PanedWindow to add buttons to
        callbacks: Dictionary with callback functions for each button
    """
    right_frame = tk.Frame(main_paned, width=100)
    right_frame.pack_propagate(False)
    main_paned.add(right_frame, stretch="never", minsize=100)
    
    # Installation section
    install_section = tk.LabelFrame(right_frame, text="Installation", padx=5, pady=5)
    install_section.pack(fill=tk.X, pady=(0, 5))
    
    reset_btn = _create_button(install_section, "Reset", callbacks['reset'])
    reset_btn.pack(pady=(0, 3))
    
    pause_btn = _create_button(install_section, "Pause", callbacks['pause'], state=tk.DISABLED)
    pause_btn.pack(pady=(0, 0))
    
    # Reorder section
    reorder_section = tk.LabelFrame(right_frame, text="Reorder", padx=5, pady=3)
    reorder_section.pack(fill=tk.X, pady=(0, 5))
    
    up_btn = _create_button(reorder_section, "↑", callbacks['move_up'], width=3, font_size=11)
    up_btn.pack(pady=(0, 3))
    
    down_btn = _create_button(reorder_section, "↓", callbacks['move_down'], width=3, font_size=11)
    down_btn.pack(pady=(3, 0))
    
    # Management section
    management_section = tk.LabelFrame(right_frame, text="Management", padx=5, pady=8)
    management_section.pack(fill=tk.X, pady=(0, 5))
    
    categories_btn = _create_button(management_section, "Categories", callbacks['categories'])
    categories_btn.pack(pady=(0, 3))
    
    add_btn = _create_button(management_section, "Add Mod", callbacks['add'])
    add_btn.pack(pady=(0, 3))
    
    edit_btn = _create_button(management_section, "Edit Mod", callbacks['edit'])
    edit_btn.pack(pady=(0, 3))
    
    remove_btn = _create_button(management_section, "Remove Mod", callbacks['remove'])
    remove_btn.pack(pady=(0, 3))

    import_btn = _create_button(management_section, "Import CSV", callbacks['import_csv'])
    import_btn.pack(pady=(0, 3))

    export_btn = _create_button(management_section, "Export CSV", callbacks['export_csv'])
    export_btn.pack(pady=(0, 0))
    
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
        'export': export_btn
    }


def create_log_section(main_frame):
    """Create the log section with progress bar."""
    log_frame = tk.LabelFrame(main_frame, text="Installation Log", padx=5, pady=5)
    log_frame.pack(fill=tk.BOTH, expand=True)
    
    progress_bar = ttk.Progressbar(log_frame, mode='determinate')
    progress_bar.pack(fill=tk.X, pady=(0, 5))
    
    log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED, height=35)
    log_text.pack(fill=tk.BOTH, expand=True)
    
    return log_frame, progress_bar, log_text


def create_bottom_buttons(main_frame, install_callback, quit_callback, trust_gdrive_var=None):
    """Create the bottom button panel with optional Google Drive trust checkbox."""
    button_frame = tk.Frame(main_frame)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X)
    button_frame.configure(height=50 if trust_gdrive_var else 35)
    button_frame.pack_propagate(False)
    
    # Google Drive trust checkbox (if provided)
    if trust_gdrive_var is not None:
        gdrive_check_frame = tk.Frame(button_frame)
        gdrive_check_frame.pack(fill=tk.X, pady=(0, 5))
        
        gdrive_check = tk.Checkbutton(
            gdrive_check_frame,
            text="Trust Google Drive large files (bypass virus scan warning)",
            variable=trust_gdrive_var,
            font=("Arial", 9)
        )
        gdrive_check.pack(anchor=tk.W, padx=5)

    button_container = tk.Frame(button_frame)
    button_container.pack(fill=tk.BOTH, expand=True)
    button_container.columnconfigure(0, weight=1)
    button_container.columnconfigure(1, weight=1)

    install_btn = _create_button(button_container, "Install Modlist", install_callback, height=1)
    install_btn.grid(row=0, column=0, sticky="we", padx=(0, 3))

    quit_btn = _create_button(button_container, "Quit", quit_callback, height=1)
    quit_btn.grid(row=0, column=1, sticky="we", padx=(3, 0))
    
    return button_frame, install_btn, quit_btn
