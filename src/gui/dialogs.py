"""
Dialog windows for the Modlist Installer application.
Contains all popup dialogs for adding, editing, importing, and exporting mods.
"""

import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
import csv
import threading
import re
from pathlib import Path
from . import custom_dialogs
from .ui_builder import _create_button
from utils.theme import TriOSTheme


def fix_google_drive_url(url):
    """Fix Google Drive URL if it has issues with large file downloads.
    
    Converts drive.google.com/file/d/ID/view URLs to drive.usercontent.google.com format
    and adds the confirm parameter to bypass the virus scan warning for large files.
    
    Args:
        url: The original Google Drive URL
        
    Returns:
        The fixed URL if it's a Google Drive link, otherwise the original URL
    """
    if 'drive.google.com' not in url:
        return url
    
    # Extract file ID from various Google Drive URL formats
    file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if not file_id_match:
        file_id_match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    
    if file_id_match:
        file_id = file_id_match.group(1)
        # Create the direct download URL with confirm parameter
        fixed_url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
        return fixed_url
    
    return url


def open_add_mod_dialog(parent, app):
    """Open a modal dialog to add a mod via the UI - downloads and extracts metadata automatically."""
    dlg = tk.Toplevel(parent)
    dlg.title("Add Mod")
    dlg.geometry("550x180")
    dlg.resizable(False, False)
    dlg.configure(bg=TriOSTheme.SURFACE)

    url_var = tk.StringVar()
    category_var = tk.StringVar(value="Uncategorized")
    status_var = tk.StringVar(value="")

    tk.Label(dlg, text="Download URL:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).grid(row=0, column=0, sticky="e", padx=8, pady=(12, 6))
    url_entry = tk.Entry(dlg, textvariable=url_var, width=45, bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY, 
            insertbackground=TriOSTheme.PRIMARY, relief=tk.FLAT, highlightthickness=1, 
            highlightbackground=TriOSTheme.BORDER, highlightcolor=TriOSTheme.PRIMARY)
    url_entry.grid(row=0, column=1, padx=8, pady=(12, 6))
    url_entry.focus()

    tk.Label(dlg, text="Category:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).grid(row=1, column=0, sticky="e", padx=8, pady=6)
    category_combo = ttk.Combobox(dlg, textvariable=category_var, width=42, values=app.categories, state='readonly')
    category_combo.grid(row=1, column=1, padx=8, pady=6)

    # Status label
    status_label = tk.Label(dlg, textvariable=status_var, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, wraplength=500)
    status_label.grid(row=2, column=0, columnspan=2, padx=8, pady=6)

    def submit():
        url = url_var.get().strip()
        if not url:
            custom_dialogs.showerror("Error", "Download URL is required")
            return

        # Disable buttons during download
        add_button.config(state=tk.DISABLED)
        cancel_button.config(state=tk.DISABLED)
        status_var.set("⬇ Downloading and extracting metadata...")
        dlg.update()

        try:
            import tempfile
            from pathlib import Path
            
            # Download the archive
            status_var.set("⬇ Downloading archive...")
            dlg.update()
            temp_file, is_7z = app.mod_installer.download_archive({'download_url': url, 'name': 'temp'})
            
            if not temp_file:
                custom_dialogs.showerror("Error", "Failed to download archive from URL")
                add_button.config(state=tk.NORMAL)
                cancel_button.config(state=tk.NORMAL)
                status_var.set("")
                return
            
            try:
                # Extract metadata
                status_var.set("📦 Extracting metadata...")
                dlg.update()
                metadata = app.mod_installer.extract_mod_metadata(temp_file, is_7z)
                
                if not metadata or not metadata.get('id'):
                    custom_dialogs.showerror("Error", "Could not extract mod metadata (mod_info.json not found or missing 'id' field)")
                    add_button.config(state=tk.NORMAL)
                    cancel_button.config(state=tk.NORMAL)
                    status_var.set("")
                    return
                
                # Build mod object with extracted metadata
                mod = {
                    "mod_id": metadata.get('id'),
                    "name": metadata.get('name', metadata.get('id')),
                    "download_url": url,
                    "mod_version": metadata.get('version', ''),
                    "game_version": metadata.get('gameVersion', ''),
                    "category": category_var.get().strip() or "Uncategorized"
                }
                
                # Check if mod already exists (by mod_id)
                existing_mods = app.modlist_data.get('mods', [])
                for existing_mod in existing_mods:
                    if existing_mod.get('mod_id') == mod['mod_id']:
                        custom_dialogs.showerror("Error", f"Mod '{mod['name']}' (ID: {mod['mod_id']}) already exists in modlist")
                        add_button.config(state=tk.NORMAL)
                        cancel_button.config(state=tk.NORMAL)
                        status_var.set("")
                        return
                
                app.add_mod_to_config(mod)
                custom_dialogs.showsuccess("Success", f"Mod '{mod['name']}' (v{mod['mod_version']}) has been added")
                dlg.destroy()
                
            finally:
                # Cleanup temp file
                try:
                    if temp_file and Path(temp_file).exists():
                        Path(temp_file).unlink()
                except Exception:
                    pass
                    
        except Exception as e:
            custom_dialogs.showerror("Error", f"Failed to process mod: {e}")
            add_button.config(state=tk.NORMAL)
            cancel_button.config(state=tk.NORMAL)
            status_var.set("")

    btn_frame = tk.Frame(dlg, bg=TriOSTheme.SURFACE)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=12)
    
    # Centrer les boutons
    btn_container = tk.Frame(btn_frame, bg=TriOSTheme.SURFACE)
    btn_container.pack(expand=True)
    
    add_button = _create_button(btn_container, "Add Mod", submit, width=12, button_type="success")
    add_button.pack(side=tk.LEFT, padx=6)
    
    cancel_button = _create_button(btn_container, "Cancel", dlg.destroy, width=12, button_type="secondary")
    cancel_button.pack(side=tk.LEFT, padx=6)


def open_edit_mod_dialog(parent, app, current_mod):
    """Open a modal dialog to view mod info and update name, download URL and category."""
    dlg = tk.Toplevel(parent)
    dlg.title(f"Mod Info: {current_mod.get('name', 'Unknown')}")
    dlg.geometry("550x320")
    dlg.resizable(False, False)
    dlg.configure(bg=TriOSTheme.SURFACE)

    # Get mod info
    mod_id_value = current_mod.get('mod_id', 'N/A')
    mod_name_value = current_mod.get('name', 'Unknown')
    mod_version_value = current_mod.get('mod_version', 'N/A')
    game_version_value = current_mod.get('game_version', current_mod.get('version', 'N/A'))
    category_value = current_mod.get('category', 'Uncategorized')
    url_value = current_mod.get('download_url', '')

    name_var = tk.StringVar(value=mod_name_value)
    url_var = tk.StringVar(value=url_value)
    category_var = tk.StringVar(value=category_value)

    # Readonly fields (labels with values)
    row = 0
    
    tk.Label(dlg, text="Mod ID:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=(12, 6))
    tk.Label(dlg, text=mod_id_value, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=(12, 6))
    row += 1
    
    # Editable Name field (display only, mod_id is the real key)
    tk.Label(dlg, text="Display Name:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    name_entry = tk.Entry(dlg, textvariable=name_var, width=45, bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY, 
            insertbackground=TriOSTheme.PRIMARY, relief=tk.FLAT, highlightthickness=1, 
            highlightbackground=TriOSTheme.BORDER, highlightcolor=TriOSTheme.PRIMARY)
    name_entry.grid(row=row, column=1, padx=8, pady=6)
    row += 1
    
    tk.Label(dlg, text="Mod Version:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    tk.Label(dlg, text=mod_version_value, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=6)
    row += 1
    
    tk.Label(dlg, text="Game Version:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    tk.Label(dlg, text=game_version_value, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=6)
    row += 1
    
    # Editable Category field
    tk.Label(dlg, text="Category:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    category_combo = ttk.Combobox(dlg, textvariable=category_var, width=42, values=app.categories, state='readonly')
    category_combo.grid(row=row, column=1, sticky="w", padx=8, pady=6)
    row += 1
    
    # Editable URL field
    tk.Label(dlg, text="Download URL:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    url_entry = tk.Entry(dlg, textvariable=url_var, width=45, bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY, 
            insertbackground=TriOSTheme.PRIMARY, relief=tk.FLAT, highlightthickness=1, 
            highlightbackground=TriOSTheme.BORDER, highlightcolor=TriOSTheme.PRIMARY)
    url_entry.grid(row=row, column=1, padx=8, pady=6)
    row += 1

    def submit():
        name = name_var.get().strip()
        url = url_var.get().strip()
        category = category_var.get().strip()
        
        if not name:
            custom_dialogs.showerror("Error", "Display name cannot be empty")
            return
        
        if not url:
            custom_dialogs.showerror("Error", "Download URL is required")
            return

        # Update name, URL and category in the modlist
        mods = app.modlist_data.get('mods', [])
        mod_id = current_mod.get('mod_id')
        
        for mod in mods:
            # Match by mod_id if available, fallback to name
            if (mod_id and mod.get('mod_id') == mod_id) or (not mod_id and mod['name'] == current_mod['name']):
                mod['name'] = name
                mod['download_url'] = url
                mod['category'] = category or 'Uncategorized'
                break
        
        app.save_modlist_config()
        app.display_modlist_info()
        app.log(f"Updated mod info for: {name}")
        custom_dialogs.showsuccess("Success", f"Mod info for '{name}' has been updated")
        dlg.destroy()

    btn_frame = tk.Frame(dlg, bg=TriOSTheme.SURFACE)
    btn_frame.grid(row=row, column=0, columnspan=2, pady=12)
    
    # Centrer les boutons
    btn_container = tk.Frame(btn_frame, bg=TriOSTheme.SURFACE)
    btn_container.pack(expand=True)
    
    _create_button(btn_container, "Save Changes", submit, width=14, button_type="success").pack(side=tk.LEFT, padx=6)
    
    _create_button(btn_container, "Close", dlg.destroy, width=12, button_type="secondary").pack(side=tk.LEFT, padx=6)


def open_manage_categories_dialog(parent, app):
    """Open dialog to manage categories."""
    dlg = tk.Toplevel(parent)
    dlg.title("Manage Categories")
    dlg.geometry("500x450")
    dlg.resizable(True, True)
    dlg.minsize(400, 350)
    dlg.configure(bg=TriOSTheme.SURFACE)
    
    tk.Label(dlg, text="Categories (in display order):", font=("Arial", 12, "bold"),
            bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).pack(pady=(10, 5))
    
    # Frame for listbox and move buttons
    main_frame = tk.Frame(dlg, bg=TriOSTheme.SURFACE)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
    
    # Listbox for categories
    list_frame = tk.Frame(main_frame, bg=TriOSTheme.SURFACE)
    list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(list_frame, bg=TriOSTheme.SURFACE)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    cat_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=15,
                            bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                            selectbackground=TriOSTheme.PRIMARY, selectforeground=TriOSTheme.SURFACE_DARK,
                            relief=tk.FLAT, highlightthickness=0, borderwidth=0)
    cat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=cat_listbox.yview)
    
    # Move buttons (↑↓)
    move_frame = tk.Frame(main_frame, bg=TriOSTheme.SURFACE)
    move_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
    
    def refresh_category_listbox(selected_idx=None):
        """Refresh category listbox and optionally select an item."""
        cat_listbox.delete(0, tk.END)
        for cat in app.categories:
            cat_listbox.insert(tk.END, cat)
        if selected_idx is not None:
            cat_listbox.selection_set(selected_idx)
        app.config_manager.save_categories(app.categories)
        app.display_modlist_info()
    
    def move_up():
        selection = cat_listbox.curselection()
        if not selection or selection[0] == 0:
            return
        idx = selection[0]
        app.categories[idx], app.categories[idx-1] = app.categories[idx-1], app.categories[idx]
        refresh_category_listbox(idx-1)
    
    def move_down():
        selection = cat_listbox.curselection()
        if not selection or selection[0] >= len(app.categories) - 1:
            return
        idx = selection[0]
        app.categories[idx], app.categories[idx+1] = app.categories[idx+1], app.categories[idx]
        refresh_category_listbox(idx+1)
    
    up_btn = _create_button(move_frame, "↑", move_up, width=3, font_size=14, button_type="secondary")
    up_btn.pack(pady=(0, 5))
    
    down_btn = _create_button(move_frame, "↓", move_down, width=3, font_size=14, button_type="secondary")
    down_btn.pack(pady=(5, 0))
        
    # Populate categories
    refresh_category_listbox()
    
    # Buttons frame
    btn_frame = tk.Frame(dlg, bg=TriOSTheme.SURFACE)
    btn_frame.pack(fill=tk.X, padx=20, pady=10)
    
    def add_category():
        new_cat = tk.simpledialog.askstring("Add Category", "Enter new category name:", parent=dlg)
        if new_cat and new_cat.strip():
            new_cat = new_cat.strip()
            if new_cat not in app.categories:
                app.categories.append(new_cat)
                cat_listbox.insert(tk.END, new_cat)
                app.config_manager.save_categories(app.categories)
                app.log(f"Added category: {new_cat}")
            else:
                custom_dialogs.showwarning("Duplicate", f"Category '{new_cat}' already exists", parent=dlg)
    
    def rename_category():
        selection = cat_listbox.curselection()
        if not selection:
            custom_dialogs.showwarning("No Selection", "Please select a category to rename", parent=dlg)
            return
        
        idx = selection[0]
        old_name = app.categories[idx]
        new_name = tk.simpledialog.askstring("Rename Category", f"Rename '{old_name}' to:", 
                                              initialvalue=old_name, parent=dlg)
        if new_name and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            if new_name in app.categories:
                custom_dialogs.showwarning("Duplicate", f"Category '{new_name}' already exists", parent=dlg)
                return
            
            # Update category in all mods
            for mod in app.modlist_data.get('mods', []):
                if mod.get('category') == old_name:
                    mod['category'] = new_name
            
            app.categories[idx] = new_name
            cat_listbox.delete(idx)
            cat_listbox.insert(idx, new_name)
            cat_listbox.selection_set(idx)
            
            app.config_manager.save_categories(app.categories)
            app.save_modlist_config()
            app.display_modlist_info()
            app.log(f"Renamed category: {old_name} → {new_name}")
    
    def delete_category():
        selection = cat_listbox.curselection()
        if not selection:
            custom_dialogs.showwarning("No Selection", "Please select a category to delete", parent=dlg)
            return
        
        idx = selection[0]
        cat_name = app.categories[idx]
        
        # Check if category is in use
        in_use = any(mod.get('category') == cat_name for mod in app.modlist_data.get('mods', []))
        
        if in_use:
            response = custom_dialogs.askyesno("Category in Use", 
                f"Category '{cat_name}' is used by some mods.\nMods will be moved to 'Uncategorized'.\nContinue?",
                parent=dlg)
            if not response:
                return
            
            # Move mods to Uncategorized
            for mod in app.modlist_data.get('mods', []):
                if mod.get('category') == cat_name:
                    mod['category'] = 'Uncategorized'
            app.save_modlist_config()
        
        del app.categories[idx]
        cat_listbox.delete(idx)
        app.config_manager.save_categories(app.categories)
        app.display_modlist_info()
        app.log(f"Deleted category: {cat_name}")
    
    # Centrer tous les boutons
    center_frame = tk.Frame(btn_frame, bg=TriOSTheme.SURFACE)
    center_frame.pack(expand=True)
    
    btn_add = _create_button(center_frame, "Add", add_category, width=10, button_type="success")
    btn_add.pack(side=tk.LEFT, padx=5)
    
    btn_rename = _create_button(center_frame, "Rename", rename_category, width=10, button_type="info")
    btn_rename.pack(side=tk.LEFT, padx=5)
    
    btn_delete = _create_button(center_frame, "Delete", delete_category, width=10, button_type="danger")
    btn_delete.pack(side=tk.LEFT, padx=5)
    
    btn_close = _create_button(center_frame, "Close", dlg.destroy, width=10, button_type="secondary")
    btn_close.pack(side=tk.LEFT, padx=5)


def open_import_csv_dialog(parent, app):
    """Open a file dialog to select a CSV file and import mods."""
    csv_file = filedialog.askopenfilename(
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*")]
    )
    if not csv_file:
        return
    
    # Ask user if they want to replace or merge
    response = custom_dialogs.show_import_mode_dialog(parent)
    
    if response == 'cancel':
        return
    
    thread = threading.Thread(
        target=_import_csv_file, 
        args=(csv_file, app, response == 'replace'), 
        daemon=True
    )
    thread.start()


def open_export_csv_dialog(parent, app):
    """Open a file dialog to export mods to CSV."""
    csv_file = filedialog.asksaveasfilename(
        title="Export modlist to CSV",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*")]
    )
    
    if not csv_file:
        return
    
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            # Write metadata section
            metadata_writer = csv.writer(f)
            metadata_writer.writerow(['modlist_name', 'starsector_version', 'modlist_description', 'modlist_version'])
            metadata_writer.writerow([
                app.modlist_data.get('modlist_name', ''),
                app.modlist_data.get('starsector_version', ''),
                app.modlist_data.get('description', ''),
                app.modlist_data.get('version', '')
            ])
            
            # Write mods section
            writer = csv.DictWriter(f, fieldnames=['mod_id', 'name', 'download_url', 'mod_version', 'game_version', 'category'])
            writer.writeheader()
            
            for mod in app.modlist_data.get('mods', []):
                # Use game_version, fallback to legacy 'version' field
                game_ver = mod.get('game_version') or mod.get('version') or ''
                writer.writerow({
                    'mod_id': mod.get('mod_id', ''),
                    'name': mod.get('name', ''),
                    'download_url': mod.get('download_url', ''),
                    'mod_version': mod.get('mod_version', ''),
                    'game_version': game_ver,
                    'category': mod.get('category', 'Uncategorized')
                })
        
        app.log(f"✓ Exported {len(app.modlist_data.get('mods', []))} mods to {csv_file}", success=True)
    except Exception as e:
        app.log(f"✗ Export error: {e}", error=True)


def _import_csv_file(csv_path: str, app, replace_mode: bool = False):
    """Import CSV logic executed in a background thread.
    
    Args:
        csv_path: Path to the CSV file
        app: Main application instance
        replace_mode: If True, clear existing mods before import. If False, merge.
    """
    app.root.after(0, lambda: _set_ui_enabled(app, False))
    
    mode_str = "Replacing" if replace_mode else "Merging"
    app.log(f"{mode_str} modlist from CSV: {csv_path}...")
    
    # Clear existing mods if replace mode
    if replace_mode:
        original_count = len(app.modlist_data.get('mods', []))
        app.modlist_data['mods'] = []
        app.log(f"  Cleared {original_count} existing mod(s)")
    
    try:
        # Read all lines first to detect metadata
        with open(csv_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            raise ValueError("CSV file is empty")
        
        # Check if first line contains metadata
        first_line_headers = [h.strip() for h in lines[0].strip().split(',')]
        app.log(f"  First line headers: {first_line_headers}")
        
        has_metadata = any(h in first_line_headers for h in ['modlist_name', 'starsector_version', 'modlist_description', 'modlist_version'])
        has_mod_headers = any(h in first_line_headers for h in ['name', 'download_url', 'url'])
        
        app.log(f"  Has metadata: {has_metadata}, Has mod headers: {has_mod_headers}")
        
        metadata_updated = False
        start_line = 0
        
        # If first line has metadata and no mod headers, it's metadata-only
        if has_metadata and not has_mod_headers:
            app.log(f"  Parsing metadata section...")
            # Parse metadata from first line
            reader = csv.DictReader([lines[0], lines[1]])  # Header + values
            metadata_row = next(reader)
            
            app.log(f"  Detected metadata row keys: {list(metadata_row.keys())}")
            app.log(f"  Detected metadata row values: {list(metadata_row.values())}")
            
            # Update modlist metadata using mapping
            metadata_mapping = {
                'modlist_name': 'modlist_name',
                'starsector_version': 'starsector_version',
                'modlist_description': 'description',
                'modlist_version': 'version'
            }
            
            for csv_key, data_key in metadata_mapping.items():
                if csv_key in metadata_row and metadata_row.get(csv_key, '').strip():
                    app.modlist_data[data_key] = metadata_row[csv_key].strip()
                    app.log(f"  {data_key}: {app.modlist_data[data_key]}")
                    metadata_updated = True
            
            app.log(f"  Metadata updated: {metadata_updated}")
            
            if metadata_updated:
                # Save metadata updates using ConfigManager
                app.log(f"  Saving modlist configuration...")
                app.config_manager.save_modlist_config(app.modlist_data)
                app.log(f"  Config file saved successfully")
                # Refresh display
                app.root.after(0, app.display_modlist_info)
            
            # Skip metadata lines (header + value)
            start_line = 2
        else:
            app.log(f"  No metadata section detected, parsing as regular CSV")
        
        # Now parse mods starting from the appropriate line
        if start_line < len(lines):
            # Read mods section
            with open(csv_path, 'r', encoding='utf-8') as f:
                # Skip to mod section
                for _ in range(start_line):
                    f.readline()
                
                reader = csv.DictReader(f)
                # Clean up fieldnames (remove leading/trailing spaces)
                reader.fieldnames = [field.strip() if field else field for field in reader.fieldnames]
                rows = list(reader)
            
            added_count = 0
            new_categories = []
            
            for r in rows:
                mod_id = (r.get('mod_id') or '').strip()
                name = (r.get('name') or '').strip()
                url = (r.get('download_url') or r.get('url') or '').strip()
                # Support both 'game_version' and legacy 'version' field in CSV
                mod_version = (r.get('mod_version') or '').strip()
                game_version = (r.get('game_version') or r.get('version') or '').strip()
                category = (r.get('category') or '').strip()

                if not url:
                    app.log(f"  ℹ Skipped: Row {r} (missing URL)", info=True)
                    continue

                if not app.validate_url(url):
                    app.log(f"  ℹ Skipped: URL not reachable - {url}", info=True)
                    continue

                # If mod_id is missing but name/URL present, try to extract metadata from URL
                if not mod_id or not name:
                    app.log(f"  ⚠ CSV missing mod_id/name for {url}, attempting auto-detection...", info=True)
                    try:
                        temp_file, is_7z = app.mod_installer.download_archive({'download_url': url, 'name': 'temp'})
                        if temp_file:
                            try:
                                from pathlib import Path
                                metadata = app.mod_installer.extract_mod_metadata(temp_file, is_7z)
                                if metadata:
                                    mod_id = metadata.get('id', mod_id)
                                    name = metadata.get('name', name) or mod_id
                                    if not mod_version:
                                        mod_version = metadata.get('version', '')
                                    if not game_version:
                                        game_version = metadata.get('gameVersion', '')
                                    app.log(f"  ✓ Auto-detected: {name} (ID: {mod_id})", info=True)
                            finally:
                                Path(temp_file).unlink()
                    except Exception as e:
                        app.log(f"  ⚠ Auto-detection failed: {e}", info=True)
                
                if not mod_id:
                    app.log(f"  ℹ Skipped: Cannot determine mod_id for {url}", info=True)
                    continue

                mod_obj = {
                    "mod_id": mod_id,
                    "name": name or mod_id,
                    "download_url": url,
                    "category": category or 'Uncategorized'
                }
                if mod_version:
                    mod_obj['mod_version'] = mod_version
                if game_version:
                    mod_obj['game_version'] = game_version
                
                # Track new categories
                if category and category not in app.categories and category not in new_categories:
                    new_categories.append(category)

                before = len(app.modlist_data.get('mods', []))
                app.add_mod_to_config(mod_obj)
                after = len(app.modlist_data.get('mods', []))
                if after > before:
                    added_count += 1
                    app.log(f"  Added: {name}")
                else:
                    app.log(f"  ℹ Skipped: '{name}' (duplicate)", info=True)
            
            # Add new categories to the list
            if new_categories:
                # Insert new categories before "Uncategorized" if it exists
                try:
                    insert_pos = app.categories.index('Uncategorized')
                except ValueError:
                    insert_pos = len(app.categories)
                
                for new_cat in new_categories:
                    app.categories.insert(insert_pos, new_cat)
                    insert_pos += 1
                    app.log(f"  Added new category: {new_cat}")
                
                app.config_manager.save_categories(app.categories)

            summary = f"CSV import complete. {added_count} mod(s) added."
            if metadata_updated:
                summary += " Modlist metadata updated."
            app.log(summary)
            app.root.after(0, lambda: custom_dialogs.showsuccess("Import complete", summary))
        else:
            summary = "Modlist metadata updated."
            app.log(summary)
            app.root.after(0, lambda: custom_dialogs.showsuccess("Import complete", summary))
        
        app.root.after(0, lambda: _set_ui_enabled(app, True))
    except (FileNotFoundError, csv.Error, UnicodeDecodeError, ValueError) as e:
        app.log(f"  ✗ Error importing CSV: {type(e).__name__}: {e}", error=True)
        app.root.after(0, lambda: custom_dialogs.showerror("Import failed", f"Error during CSV import:\n{type(e).__name__}: {e}"))
        app.root.after(0, lambda: _set_ui_enabled(app, True))


def _set_UI_enabled(app, enabled: bool):
    """Enable or disable UI buttons."""
    state = 'normal' if enabled else 'disabled'
    try:
        app.add_btn.config(state=state)
        app.import_btn.config(state=state)
        app.export_btn.config(state=state)
        app.reset_btn.config(state=state)
        app.quit_btn.config(state=state)
    except (AttributeError, tk.TclError):
        pass  # Widget not available or destroyed


def show_google_drive_confirmation_dialog(parent, failed_mods, on_confirm_callback, on_cancel_callback):
    """Show a confirmation dialog for Google Drive mods that need virus scan bypass.
    
    Args:
        parent: Parent window
        failed_mods: List of mod dictionaries that failed Google Drive download
        on_confirm_callback: Callback function when user confirms (receives list of fixed mods)
        on_cancel_callback: Callback function when user cancels
    """
    dialog = tk.Toplevel(parent)
    dialog.title("Google Drive Confirmation Required")
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)
    dialog.configure(bg=TriOSTheme.SURFACE)
    
    # Main frame
    main_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Failed Google Drive mods section
    gdrive_frame = tk.Frame(main_frame, bg=TriOSTheme.SURFACE)
    gdrive_frame.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(gdrive_frame, text=f"{len(failed_mods)} Google Drive mod(s) need confirmation to download:", 
            font=("Arial", 10, "bold"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.ERROR).pack(anchor=tk.W, pady=(0, 8))
    
    # List Google Drive mods
    gdrive_list_frame = tk.Frame(gdrive_frame, bg=TriOSTheme.GDRIVE_BG)
    gdrive_list_frame.pack(fill=tk.X, pady=(0, 10))
    
    gdrive_text = tk.Text(gdrive_list_frame, height=min(5, len(failed_mods)), width=60,
                         font=("Courier", 9), wrap=tk.WORD, bg=TriOSTheme.GDRIVE_BG, fg=TriOSTheme.TEXT_PRIMARY, 
                         relief=tk.FLAT, highlightthickness=0, borderwidth=0)
    for mod in failed_mods:
        gdrive_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
    gdrive_text.config(state=tk.DISABLED)
    gdrive_text.pack(padx=5, pady=5)
    
    # Warning message
    warning_frame = tk.Frame(gdrive_frame, bg=TriOSTheme.SURFACE)
    warning_frame.pack(fill=tk.X, pady=(0, 0))
    
    warning_text = tk.Label(warning_frame, 
        text="⚠️  Google can't verify these files due to their size. Confirm only if from a trusted source.",
        font=("Arial", 9), bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, wraplength=500, justify=tk.LEFT)
    warning_text.pack(anchor=tk.W)
    
    # Buttons frame
    button_frame = tk.Frame(main_frame, bg=TriOSTheme.SURFACE)
    button_frame.pack(fill=tk.X, pady=(20, 0))
    
    def on_confirm():
        # Fix Google Drive URLs
        mods_to_download = []
        for mod in failed_mods:
            mod_copy = mod.copy()
            fixed_url = fix_google_drive_url(mod['download_url'])
            mod_copy['download_url'] = fixed_url
            mods_to_download.append(mod_copy)
        
        dialog.destroy()
        on_confirm_callback(mods_to_download)
    
    def on_cancel():
        dialog.destroy()
        on_cancel_callback()
    
    # Center the buttons
    button_container = tk.Frame(button_frame, bg=TriOSTheme.SURFACE)
    button_container.pack(anchor=tk.CENTER)
    
    _create_button(button_container, "Confirm Installation", on_confirm,
                  width=18, button_type="success").pack(side=tk.LEFT, padx=5)
    
    _create_button(button_container, "Cancel", on_cancel,
                  width=12, button_type="secondary").pack(side=tk.LEFT, padx=5)
    
    # Keyboard bindings
    dialog.bind("<Escape>", lambda e: on_cancel())
    
    # Center dialog on screen (with protection against widget destruction)
    try:
        dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    except tk.TclError:
        # Dialog may be destroyed, use default position
        pass
    
    dialog.wait_window()
