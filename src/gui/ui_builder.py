"""
UI builder for the Modlist Installer application.
Contains functions to create the user interface components.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext


def create_header(root):
    """Create the header frame with title."""
    header_frame = tk.Frame(root, bg="#34495e", height=50)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)
    
    title_label = tk.Label(
        header_frame,
        text="Modlist Installer",
        font=("Arial", 14, "bold"),
        bg="#34495e",
        fg="white"
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
        font=("Arial", 10),
        state="readonly"
    )
    path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
    
    browse_btn = tk.Button(
        path_container,
        text="Browse...",
        command=browse_callback,
        bg="#3498db",
        fg="black",
        font=("Arial", 9, "bold"),
        width=10
    )
    browse_btn.pack(side=tk.RIGHT)
    
    path_status_label = tk.Label(
        path_frame,
        text="",
        font=("Arial", 8),
        fg="#27ae60"
    )
    path_status_label.pack(fill=tk.X, pady=(3, 0))
    
    return path_frame, path_entry, browse_btn, path_status_label


def create_modlist_section(main_frame, mod_click_callback, pane_resize_callback, theme_manager):
    """Create the modlist information section."""
    info_frame = tk.LabelFrame(main_frame, text="Current Modlist", padx=5, pady=5)
    info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
    
    # Single PanedWindow for both header and modlist
    main_paned = tk.PanedWindow(info_frame, orient=tk.HORIZONTAL, sashwidth=5, sashrelief=tk.RAISED)
    main_paned.pack(fill=tk.BOTH, expand=True)
    
    # Left side: Header and modlist
    left_container = tk.Frame(main_paned)
    main_paned.add(left_container, stretch="always")
    
    # Get theme colors from centralized manager
    colors = theme_manager.get_colors()
    
    # Header text
    header_text = tk.Text(
        left_container, 
        height=4, 
        wrap=tk.WORD, 
        state=tk.DISABLED,
        bg=colors['listbox_bg'],
        fg=colors['listbox_fg']
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
        cursor="arrow",
        bg=colors['listbox_bg'],
        fg=colors['listbox_fg']
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
    
    install_btn = tk.Button(
        install_section,
        text="Install Modlist",
        command=callbacks['install'],
        bg="#27ae60",
        fg="black",
        font=("Arial", 9, "bold"),
        width=10
    )
    install_btn.pack(pady=(0, 3))
    
    pause_btn = tk.Button(
        install_section,
        text="Pause",
        command=callbacks['pause'],
        bg="#f39c12",
        fg="black",
        font=("Arial", 9, "bold"),
        width=10,
        state=tk.DISABLED
    )
    pause_btn.pack(pady=(0, 0))
    
    # Reorder section
    reorder_section = tk.LabelFrame(right_frame, text="Reorder", padx=5, pady=3)
    reorder_section.pack(fill=tk.X, pady=(0, 5))
    
    up_btn = tk.Button(
        reorder_section,
        text="↑",
        command=callbacks['move_up'],
        bg="#95a5a6",
        fg="black",
        font=("Arial", 11, "bold"),
        width=3
    )
    up_btn.pack(pady=(0, 3))
    
    down_btn = tk.Button(
        reorder_section,
        text="↓",
        command=callbacks['move_down'],
        bg="#95a5a6",
        fg="black",
        font=("Arial", 11, "bold"),
        width=3
    )
    down_btn.pack(pady=(3, 0))
    
    # Management section
    management_section = tk.LabelFrame(right_frame, text="Management", padx=5, pady=8)
    management_section.pack(fill=tk.X, pady=(0, 5))
    
    categories_btn = tk.Button(
        management_section,
        text="Categories",
        command=callbacks['categories'],
        bg="#9b59b6",
        fg="black",
        font=("Arial", 9, "bold"),
        width=10
    )
    categories_btn.pack(pady=(0, 3))
    
    add_btn = tk.Button(
        management_section,
        text="Add Mod",
        command=callbacks['add'],
        bg="#3498db",
        fg="black",
        font=("Arial", 9, "bold"),
        width=10
    )
    add_btn.pack(pady=(0, 3))
    
    remove_btn = tk.Button(
        management_section,
        text="Remove Mod",
        command=callbacks['remove'],
        bg="#e74c3c",
        fg="black",
        font=("Arial", 9, "bold"),
        width=10
    )
    remove_btn.pack(pady=(0, 3))

    import_btn = tk.Button(
        management_section,
        text="Import CSV",
        command=callbacks['import_csv'],
        bg="#f39c12",
        fg="black",
        font=("Arial", 9, "bold"),
        width=10
    )
    import_btn.pack(pady=(0, 3))

    export_btn = tk.Button(
        management_section,
        text="Export CSV",
        command=callbacks['export_csv'],
        bg="#16a085",
        fg="black",
        font=("Arial", 9, "bold"),
        width=10
    )
    export_btn.pack(pady=(0, 0))
    
    return {
        'install': install_btn,
        'pause': pause_btn,
        'up': up_btn,
        'down': down_btn,
        'categories': categories_btn,
        'add': add_btn,
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


def create_bottom_buttons(main_frame, reset_callback, quit_callback):
    """Create the bottom button panel."""
    button_frame = tk.Frame(main_frame)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X)
    button_frame.configure(height=35)
    button_frame.pack_propagate(False)

    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=1)

    reset_btn = tk.Button(
        button_frame,
        text="Reset",
        command=reset_callback,
        bg="#e67e22",
        fg="black",
        font=("Arial", 9, "bold"),
        height=1
    )
    reset_btn.grid(row=0, column=0, sticky="we", padx=(0, 3))

    quit_btn = tk.Button(
        button_frame,
        text="Close",
        command=quit_callback,
        bg="#e74c3c",
        fg="black",
        font=("Arial", 9, "bold"),
        height=1
    )
    quit_btn.grid(row=0, column=1, sticky="we", padx=(3, 0))
    
    return button_frame, reset_btn, quit_btn
