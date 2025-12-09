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
    """Open a modal dialog to add a mod via the UI."""
    dlg = tk.Toplevel(parent)
    dlg.title("Add Mod")
    dlg.geometry("500x250")
    dlg.resizable(False, False)

    name_var = tk.StringVar()
    url_var = tk.StringVar()
    game_version_var = tk.StringVar()
    category_var = tk.StringVar(value="Uncategorized")

    tk.Label(dlg, text="Mod Name:").grid(row=0, column=0, sticky="e", padx=8, pady=(12, 6))
    tk.Entry(dlg, textvariable=name_var, width=45).grid(row=0, column=1, padx=8, pady=(12, 6))

    tk.Label(dlg, text="Download URL:").grid(row=1, column=0, sticky="e", padx=8, pady=6)
    tk.Entry(dlg, textvariable=url_var, width=45).grid(row=1, column=1, padx=8, pady=6)

    tk.Label(dlg, text="Game Version (optional):").grid(row=2, column=0, sticky="e", padx=8, pady=6)
    tk.Entry(dlg, textvariable=game_version_var, width=45).grid(row=2, column=1, padx=8, pady=6)

    tk.Label(dlg, text="Category:").grid(row=3, column=0, sticky="e", padx=8, pady=6)
    category_combo = ttk.Combobox(dlg, textvariable=category_var, width=42, values=app.categories)
    category_combo.grid(row=3, column=1, padx=8, pady=6)

    def submit():
        name = name_var.get().strip()
        url = url_var.get().strip()
        if not name or not url:
            custom_dialogs.showerror("Error", "Name and URL are required")
            return

        mod = {"name": name, "download_url": url}
        if game_version_var.get().strip():
            mod["game_version"] = game_version_var.get().strip()
        if category_var.get().strip():
            mod["category"] = category_var.get().strip()
        else:
            mod["category"] = "Uncategorized"

        app.add_mod_to_config(mod)
        custom_dialogs.showsuccess("Success", f"Mod '{name}' has been added to the modlist")
        dlg.destroy()

    btn_frame = tk.Frame(dlg)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=12)
    tk.Button(btn_frame, text="Cancel", command=dlg.destroy, width=10, bg="#95a5a6", fg="black",
             font=("Arial", 9, "bold"), cursor="hand2", relief=tk.RAISED, bd=1).pack(side=tk.RIGHT, padx=6)
    tk.Button(btn_frame, text="Add", command=submit, bg="#2ecc71", fg="white", width=10,
             font=("Arial", 9, "bold"), cursor="hand2", relief=tk.RAISED, bd=1).pack(side=tk.RIGHT)


def open_edit_mod_dialog(parent, app, current_mod):
    """Open a modal dialog to edit an existing mod."""
    dlg = tk.Toplevel(parent)
    dlg.title(f"Edit Mod: {current_mod['name']}")
    dlg.geometry("500x250")
    dlg.resizable(False, False)

    # Try to get game_version from installed mod first, fallback to modlist
    game_version_value = current_mod.get('game_version', current_mod.get('version', ''))
    
    # Check if mod is installed and read game_version from mod_info.json
    from pathlib import Path
    import re
    starsector_dir = app.starsector_path.get()
    if starsector_dir:
        mods_dir = Path(starsector_dir) / "mods"
        if mods_dir.exists():
            # Search for the mod folder
            mod_name = current_mod['name']
            for folder in mods_dir.iterdir():
                if folder.is_dir() and not folder.name.startswith('.'):
                    mod_info_file = folder / "mod_info.json"
                    if mod_info_file.exists():
                        try:
                            with open(mod_info_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            # Check if this is the right mod
                            if mod_name.lower() in content.lower() or mod_name.lower() in folder.name.lower():
                                # Extract gameVersion from the installed mod
                                version_match = re.search(r'["\']?gameVersion["\']?\s*:\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                                if version_match:
                                    game_version_value = version_match.group(1)
                                    break
                        except Exception:
                            pass

    name_var = tk.StringVar(value=current_mod['name'])
    url_var = tk.StringVar(value=current_mod['download_url'])
    game_version_var = tk.StringVar(value=game_version_value)
    category_var = tk.StringVar(value=current_mod.get('category', 'Uncategorized'))

    tk.Label(dlg, text="Mod Name:").grid(row=0, column=0, sticky="e", padx=8, pady=(12, 6))
    tk.Entry(dlg, textvariable=name_var, width=45).grid(row=0, column=1, padx=8, pady=(12, 6))

    tk.Label(dlg, text="Download URL:").grid(row=1, column=0, sticky="e", padx=8, pady=6)
    tk.Entry(dlg, textvariable=url_var, width=45).grid(row=1, column=1, padx=8, pady=6)

    tk.Label(dlg, text="Game Version (optional):").grid(row=2, column=0, sticky="e", padx=8, pady=6)
    tk.Entry(dlg, textvariable=game_version_var, width=45).grid(row=2, column=1, padx=8, pady=6)

    tk.Label(dlg, text="Category:").grid(row=3, column=0, sticky="e", padx=8, pady=6)
    category_combo = ttk.Combobox(dlg, textvariable=category_var, width=42, values=app.categories)
    category_combo.grid(row=3, column=1, padx=8, pady=6)

    def submit():
        name = name_var.get().strip()
        url = url_var.get().strip()
        if not name or not url:
            custom_dialogs.showerror("Error", "Name and URL are required")
            return

        # Update the mod in the modlist
        mods = app.modlist_data.get('mods', [])
        for mod in mods:
            if mod['name'] == current_mod['name']:
                mod['name'] = name
                mod['download_url'] = url
                mod['category'] = category_var.get().strip() or "Uncategorized"
                if game_version_var.get().strip():
                    mod['game_version'] = game_version_var.get().strip()
                    # Remove old 'version' field if it exists
                    if 'version' in mod:
                        del mod['version']
                elif 'game_version' in mod:
                    del mod['game_version']
                elif 'version' in mod:
                    del mod['version']
                break
        
        app.save_modlist_config()
        app.display_modlist_info()
        app.log(f"Updated mod: {name}")
        custom_dialogs.showsuccess("Success", f"Mod '{name}' has been updated")
        dlg.destroy()

    btn_frame = tk.Frame(dlg)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=12)
    tk.Button(btn_frame, text="Cancel", command=dlg.destroy, width=10, bg="#95a5a6", fg="black",
             font=("Arial", 9, "bold"), cursor="hand2", relief=tk.RAISED, bd=1).pack(side=tk.RIGHT, padx=6)
    tk.Button(btn_frame, text="Save", command=submit, width=10, bg="#3498db", fg="white",
             font=("Arial", 9, "bold"), cursor="hand2", relief=tk.RAISED, bd=1).pack(side=tk.RIGHT)


def open_manage_categories_dialog(parent, app):
    """Open dialog to manage categories."""
    dlg = tk.Toplevel(parent)
    dlg.title("Manage Categories")
    dlg.geometry("500x450")
    dlg.resizable(True, True)
    dlg.minsize(400, 350)
    
    tk.Label(dlg, text="Categories (in display order):", font=("Arial", 12, "bold")).pack(pady=(10, 5))
    
    # Frame for listbox and move buttons
    main_frame = tk.Frame(dlg)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
    
    # Listbox for categories
    list_frame = tk.Frame(main_frame)
    list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    cat_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=15)
    cat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=cat_listbox.yview)
    
    # Move buttons (↑↓)
    move_frame = tk.Frame(main_frame)
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
    
    up_btn = tk.Button(move_frame, text="↑", command=move_up, bg="#95a5a6", fg="black", font=("Arial", 14, "bold"), width=3,
                      cursor="hand2", relief=tk.RAISED, bd=1)
    up_btn.pack(pady=(0, 5))
    
    down_btn = tk.Button(move_frame, text="↓", command=move_down, bg="#95a5a6", fg="black", font=("Arial", 14, "bold"), width=3,
                        cursor="hand2", relief=tk.RAISED, bd=1)
    down_btn.pack(pady=(5, 0))
        
    # Populate categories
    refresh_category_listbox()
    
    # Buttons frame
    btn_frame = tk.Frame(dlg)
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
    
    # Create left-side buttons
    left_frame = tk.Frame(btn_frame)
    left_frame.pack(side=tk.LEFT)
    
    btn_add = tk.Button(left_frame, text="Add", command=add_category, bg="#2ecc71", fg="white",
                       font=("Arial", 9, "bold"), cursor="hand2", relief=tk.RAISED, bd=1)
    btn_rename = tk.Button(left_frame, text="Rename", command=rename_category, bg="#3498db", fg="white",
                          font=("Arial", 9, "bold"), cursor="hand2", relief=tk.RAISED, bd=1)
    btn_delete = tk.Button(left_frame, text="Delete", command=delete_category, bg="#e74c3c", fg="white",
                          font=("Arial", 9, "bold"), cursor="hand2", relief=tk.RAISED, bd=1)
    
    # Create right-side button
    right_frame = tk.Frame(btn_frame)
    right_frame.pack(side=tk.RIGHT)
    
    btn_close = tk.Button(right_frame, text="Close", command=dlg.destroy, bg="#95a5a6", fg="black",
                         font=("Arial", 9, "bold"), cursor="hand2", relief=tk.RAISED, bd=1)
    
    # Calculate width based on longest text
    max_text_width = max(len("Add"), len("Rename"), len("Delete"), len("Close"))
    for btn in [btn_add, btn_rename, btn_delete, btn_close]:
        btn.config(width=max_text_width)
    
    btn_add.pack(side=tk.LEFT, padx=5)
    btn_rename.pack(side=tk.LEFT, padx=5)
    btn_delete.pack(side=tk.LEFT, padx=5)
    btn_close.pack(padx=5)


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
            writer = csv.DictWriter(f, fieldnames=['name', 'download_url', 'game_version', 'category'])
            writer.writeheader()
            
            for mod in app.modlist_data.get('mods', []):
                writer.writerow({
                    'name': mod.get('name', ''),
                    'download_url': mod.get('download_url', ''),
                    'game_version': mod.get('game_version', mod.get('version', '')),
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
                name = (r.get('name') or '').strip()
                url = (r.get('download_url') or r.get('url') or '').strip()
                game_version = (r.get('game_version') or r.get('version') or '').strip()
                category = (r.get('category') or '').strip()

                if not name or not url:
                    app.log(f"  ℹ Skipped: Row {r} (missing name/url)", info=True)
                    continue

                if not app.validate_url(url):
                    app.log(f"  ℹ Skipped: URL not reachable - {url}", info=True)
                    continue

                mod_obj = {
                    "name": name,
                    "download_url": url,
                    "category": category or 'Uncategorized'
                }
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


def _set_ui_enabled(app, enabled: bool):
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
