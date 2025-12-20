import tkinter as tk
from tkinter import ttk, filedialog
import csv
import threading
import re
from pathlib import Path
from .ui_builder import _create_button
from utils.theme import TriOSTheme
from utils.symbols import LogSymbols, UISymbols


def _create_dialog(parent, title, width=None, height=None, resizable=False):
    """Create a centered Toplevel dialog with consistent styling.
    
    Args:
        parent: Parent window
        title: Dialog title
        width: Fixed width (if None, auto-size)
        height: Fixed height (if None, auto-size)
        resizable: Whether dialog is resizable
    
    Returns:
        tk.Toplevel: Configured dialog
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    if width and height:
        dialog.geometry(f"{width}x{height}")
    dialog.resizable(resizable, resizable)
    dialog.configure(bg=TriOSTheme.SURFACE)
    dialog.transient(parent)
    dialog.grab_set()
    return dialog


def _center_dialog(dialog, parent):
    """Center dialog on parent window."""
    try:
        # Skip centering if parent is None or doesn't have winfo methods
        if parent is None or not hasattr(parent, 'winfo_x'):
            return
            
        dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    except (tk.TclError, AttributeError):
        pass


def _create_form_field(parent, row, label_text, widget_type='entry', width=45, **widget_kwargs):
    """Create a form field with label and widget.
    
    Args:
        parent: Parent frame
        row: Grid row number
        label_text: Label text
        widget_type: 'entry' or 'combobox'
        width: Entry/Combobox width
        **widget_kwargs: Additional widget arguments (textvariable, values, etc.)
    
    Returns:
        tuple: (label, widget)
    """
    label = tk.Label(parent, text=label_text, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold'))
    label.grid(row=row, column=0, sticky="e", padx=8, pady=6)
    
    if widget_type == 'combobox':
        widget = ttk.Combobox(parent, width=width-3, **widget_kwargs)
    else:
        widget_kwargs.setdefault('bg', TriOSTheme.SURFACE_DARK)
        widget_kwargs.setdefault('fg', TriOSTheme.TEXT_PRIMARY)
        widget_kwargs.setdefault('insertbackground', TriOSTheme.PRIMARY)
        widget_kwargs.setdefault('relief', tk.FLAT)
        widget_kwargs.setdefault('highlightthickness', 1)
        widget_kwargs.setdefault('highlightbackground', TriOSTheme.BORDER)
        widget_kwargs.setdefault('highlightcolor', TriOSTheme.PRIMARY)
        widget = tk.Entry(parent, width=width, **widget_kwargs)
    
    widget.grid(row=row, column=1, padx=8, pady=6)
    return label, widget


class StyledDialog:
    def __init__(self, parent, title, message, dialog_type="info", buttons=None):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=TriOSTheme.SURFACE)
        
        # Main content frame
        content_frame = tk.Frame(self.dialog, bg=TriOSTheme.SURFACE)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Icon and message
        message_frame = tk.Frame(content_frame, bg=TriOSTheme.SURFACE)
        message_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Icon
        icons = {"info": LogSymbols.INFO, "success": LogSymbols.SUCCESS, "warning": LogSymbols.WARNING, "error": LogSymbols.ERROR, "question": LogSymbols.QUESTION}
        tk.Label(message_frame, text=icons.get(dialog_type, LogSymbols.INFO), 
                font=("Arial", 36, "bold"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.PRIMARY).pack(side=tk.LEFT, padx=(0, 15))
        
        # Message
        tk.Label(message_frame, text=message, font=("Arial", 11),
                wraplength=350, justify=tk.LEFT, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = tk.Frame(content_frame, bg=TriOSTheme.SURFACE)
        button_frame.pack(fill=tk.X)
        
        # Default buttons
        if buttons is None:
            buttons = [("Yes", True), ("No", False)] if dialog_type == "question" else [("OK", True)]
        
        # Center button container
        button_container = tk.Frame(button_frame, bg=TriOSTheme.SURFACE)
        button_container.pack(expand=True)
        
        # Create buttons
        for i, (label, value) in enumerate(buttons):
            btn_type = "success" if label in ["Yes", "OK"] else "secondary"
            btn = _create_button(button_container, label, lambda v=value: self._on_button_click(v),
                                width=12, button_type=btn_type)
            btn.pack(side=tk.LEFT, padx=5)
        
        # Keyboard bindings
        self.dialog.bind("<Return>", lambda e: self._on_button_click(buttons[0][1]))
        self.dialog.bind("<Escape>", lambda e: self._on_button_click(False if dialog_type == "question" else True))
        
        _center_dialog(self.dialog, parent)
        
    def _on_button_click(self, value):
        """Handle button click."""
        self.result = value
        self.dialog.destroy()
        
    def show(self):
        """Show dialog and wait for result."""
        self.dialog.wait_window()
        return self.result


# Helper functions for styled dialogs
def _show_dialog(dialog_type, title, message, parent=None, buttons=None):
    """Internal helper to show any dialog type."""
    if parent is None:
        parent = tk._default_root
    return StyledDialog(parent, title, message, dialog_type, buttons).show()


def showinfo(title, message, parent=None):
    """Show an info dialog."""
    return _show_dialog("info", title, message, parent)


def showsuccess(title, message, parent=None):
    """Show a success dialog."""
    return _show_dialog("success", title, message, parent)


def showerror(title, message, parent=None):
    """Show an error dialog."""
    return _show_dialog("error", title, message, parent)


def showwarning(title, message, parent=None):
    """Show a warning dialog."""
    return _show_dialog("warning", title, message, parent)


def askyesno(title, message, parent=None):
    """Show a yes/no question dialog."""
    return _show_dialog("question", title, message, parent, [("Yes", True), ("No", False)])


def askokcancel(title, message, parent=None):
    """Show an OK/Cancel question dialog."""
    return _show_dialog("question", title, message, parent, [("OK", True), ("Cancel", False)])


def ask_version_action(title, message, parent=None):
    """Show a dialog with Force Update / Continue / Cancel options.
    
    Returns:
        str: 'force_update', 'continue', or 'cancel'
    """
    return _show_dialog("warning", title, message, parent, 
                       [("Force Update", "force_update"), ("Continue", "continue"), ("Cancel", "cancel")])


def show_validation_report(parent, github_mods, gdrive_mods, other_domains, failed_list):
    result = {'action': 'cancel'}
    
    dialog = _create_dialog(parent, "Download Sources Analysis")
    
    main_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    tk.Label(main_frame, text="Download Sources Analysis", 
             font=("Arial", 14, "bold"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).pack(pady=(0, 15))
    
    # Summary frame
    summary_frame = tk.Frame(main_frame, bg=TriOSTheme.SURFACE)
    summary_frame.pack(fill=tk.X, pady=(0, 15))
    
    # GitHub mods
    if len(github_mods) > 0:
        github_frame = tk.Frame(summary_frame, bg=TriOSTheme.SURFACE)
        github_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(github_frame, text=f"{LogSymbols.SUCCESS} {len(github_mods)} mod(s) from GitHub", 
                font=("Arial", 11, "bold"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.GITHUB_FG).pack(anchor=tk.W)
        
        # List GitHub mods
        github_list_frame = tk.Frame(github_frame, bg=TriOSTheme.GITHUB_BG)
        github_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        github_text = tk.Text(github_list_frame, height=min(4, len(github_mods)), width=55,
                             font=("Courier", 9), wrap=tk.WORD, bg=TriOSTheme.GITHUB_BG, fg=TriOSTheme.TEXT_PRIMARY, 
                             relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        for mod in github_mods:
            github_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
        github_text.config(state=tk.DISABLED)
        github_text.pack(padx=5, pady=5)
    
    # Google Drive mods with info
    if len(gdrive_mods) > 0:
        gdrive_frame = tk.Frame(summary_frame, bg=TriOSTheme.SURFACE)
        gdrive_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(gdrive_frame, text=f"{LogSymbols.SUCCESS} {len(gdrive_mods)} mod(s) from Google Drive", 
                font=("Arial", 11, "bold"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.GDRIVE_FG).pack(anchor=tk.W)
        
        # Info about large files
        info_text = tk.Label(gdrive_frame, 
            text="Large files bypass Google's virus scan and may need a second confirmation to download.",
            font=("Arial", 9, "italic"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, wraplength=450, justify=tk.LEFT)
        info_text.pack(anchor=tk.W, padx=(20, 0), pady=(2, 0))
        
        # List Google Drive mods
        gdrive_list_frame = tk.Frame(gdrive_frame, bg=TriOSTheme.GDRIVE_BG)
        gdrive_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        gdrive_text = tk.Text(gdrive_list_frame, height=min(4, len(gdrive_mods)), width=55,
                             font=("Courier", 9), wrap=tk.WORD, bg=TriOSTheme.GDRIVE_BG, fg=TriOSTheme.TEXT_PRIMARY, 
                             relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        for mod in gdrive_mods:
            gdrive_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
        gdrive_text.config(state=tk.DISABLED)
        gdrive_text.pack(padx=5, pady=5)
    
    # Other domains
    if other_domains:
        other_frame = tk.Frame(summary_frame, bg=TriOSTheme.SURFACE)
        other_frame.pack(fill=tk.X, pady=(0, 8))
        
        total_other = sum(len(mods) for mods in other_domains.values())
        tk.Label(other_frame, text=f"{LogSymbols.WARNING} {total_other} mod(s) from other sources", 
                font=("Arial", 11, "bold"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.OTHER_FG).pack(anchor=tk.W)
        
        # List each domain with its mods
        other_list_frame = tk.Frame(other_frame, bg=TriOSTheme.OTHER_BG)
        other_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        other_text = tk.Text(other_list_frame, height=min(5, total_other), width=55,
                            font=("Courier", 9), wrap=tk.WORD, bg=TriOSTheme.OTHER_BG, fg=TriOSTheme.TEXT_PRIMARY, 
                            relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        
        for domain, mods in sorted(other_domains.items()):
            for mod in mods:
                other_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')} ({domain})\n")
        
        other_text.config(state=tk.DISABLED)
        other_text.pack(padx=5, pady=5)
    
    # Failed mods
    if failed_list:
        failed_frame = tk.Frame(summary_frame, bg=TriOSTheme.SURFACE)
        failed_frame.pack(fill=tk.X, pady=(0, 0))
        
        tk.Label(failed_frame, text=f"{LogSymbols.ERROR} {len(failed_list)} mod(s) inaccessible", 
                font=("Arial", 11, "bold"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.FAILED_FG).pack(anchor=tk.W, pady=(0, 2))
        
        tk.Label(failed_frame, 
            text="These mods cannot be downloaded. Check URLs or contact mod authors.",
            font=("Arial", 9, "italic"), bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, wraplength=450, justify=tk.LEFT).pack(anchor=tk.W, padx=(20, 0), pady=(2, 0))
        
        # Scrollable list of failed mods
        failed_list_frame = tk.Frame(failed_frame, bg=TriOSTheme.FAILED_BG)
        failed_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        failed_text = tk.Text(failed_list_frame, height=min(5, len(failed_list)), width=55, 
                             font=("Courier", 9), wrap=tk.WORD, bg=TriOSTheme.FAILED_BG, fg=TriOSTheme.TEXT_PRIMARY, 
                             relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        
        for fail in failed_list:
            mod_name = fail['mod'].get('name', 'Unknown')
            error = fail['error']
            failed_text.insert(tk.END, f"  • {mod_name}: {error}\n")
        
        failed_text.config(state=tk.DISABLED)
        failed_text.pack(padx=5, pady=5)
    
    # Buttons frame
    button_frame = tk.Frame(main_frame, bg=TriOSTheme.SURFACE)
    button_frame.pack(fill=tk.X, pady=(15, 0))
    
    def on_continue():
        result['action'] = 'continue'
        dialog.destroy()
    
    def on_cancel():
        result['action'] = 'cancel'
        dialog.destroy()
    
    # Center the buttons
    button_container = tk.Frame(button_frame, bg=TriOSTheme.SURFACE)
    button_container.pack(anchor=tk.CENTER)
    
    if len(github_mods) > 0 or len(gdrive_mods) > 0 or other_domains:
        _create_button(button_container, "Continue", on_continue,
                      width=12, button_type="success").pack(side=tk.LEFT, padx=5)
    
    _create_button(button_container, "Cancel", on_cancel,
                  width=12, button_type="secondary").pack(side=tk.LEFT, padx=5)
    
    # Keyboard bindings
    dialog.bind("<Escape>", lambda e: on_cancel())
    dialog.bind("<Return>", lambda e: on_continue() if len(github_mods) > 0 or len(gdrive_mods) > 0 or other_domains else None)
    
    _center_dialog(dialog, parent)
    dialog.wait_window()
    return result['action']


# ============================================================================
# Mod Management Dialogs
# ============================================================================


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
    dlg = _create_dialog(parent, "Add Mod", 550, 180)

    url_var = tk.StringVar()
    category_var = tk.StringVar(value="Uncategorized")
    status_var = tk.StringVar(value="")

    _, url_entry = _create_form_field(dlg, 0, "Download URL:", textvariable=url_var)
    url_entry.focus()
    
    _, category_combo = _create_form_field(dlg, 1, "Category:", widget_type='combobox', 
                                           textvariable=category_var, values=app.categories, state='readonly')

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
        status_var.set(f"{UISymbols.DOWNLOADING} Downloading and extracting metadata...")
        dlg.update()

        # Helper functions for Tkinter-safe callbacks
        def re_enable_buttons():
            """Re-enable buttons in case of error or cancellation."""
            add_button.config(state=tk.NORMAL)
            cancel_button.config(state=tk.NORMAL)
            status_var.set("")
        
        def show_error(message):
            """Show error dialog and re-enable buttons."""
            showerror("Error", message)
            re_enable_buttons()
        
        def on_success(mod):
            """Handle successful mod addition."""
            app.add_mod_to_config(mod)
            showsuccess("Success", f"Mod '{mod['name']}' (v{mod['mod_version']}) has been added")
            dlg.destroy()
        
        def download_retry_async(retry_url):
            """Retry download with fixed Google Drive URL."""
            status_var.set(f"{UISymbols.DOWNLOADING} Retrying download with fixed URL...")
            dlg.update()
            
            def retry_download():
                try:
                    result = app.mod_installer.download_archive(
                        {'download_url': retry_url, 'name': 'temp'},
                        skip_gdrive_check=True
                    )
                    temp_file, is_7z = result.temp_path, result.is_7z
                    if not temp_file or temp_file == 'GDRIVE_HTML':
                        dlg.after(0, lambda: show_error("Failed to download archive even with fixed URL"))
                        return
                    
                    # Continue with metadata extraction
                    dlg.after(0, lambda: process_metadata(temp_file, is_7z, retry_url))
                    
                except Exception as e:
                    dlg.after(0, lambda: show_error(f"Failed to process mod: {e}"))
            
            thread = threading.Thread(target=retry_download, daemon=True)
            thread.start()
        
        def process_metadata(temp_file, is_7z, final_url):
            """Process metadata extraction (must be called from main thread via after)."""
            import tempfile
            from pathlib import Path
            
            def extract_metadata():
                try:
                    # Extract metadata
                    metadata = app.mod_installer.extract_mod_metadata(temp_file, is_7z)
                    
                    if not metadata or not metadata.get('id'):
                        dlg.after(0, lambda: show_error("Could not extract mod metadata (mod_info.json not found or missing 'id' field)"))
                        return
                    
                    # Build mod object with extracted metadata
                    mod = {
                        "mod_id": metadata.get('id'),
                        "name": metadata.get('name', metadata.get('id')),
                        "download_url": final_url,
                        "mod_version": metadata.get('version', ''),
                        "game_version": metadata.get('gameVersion', ''),
                        "category": category_var.get().strip() or "Uncategorized"
                    }
                    
                    # Check if mod already exists (by mod_id)
                    existing_mods = app.modlist_data.get('mods', [])
                    for existing_mod in existing_mods:
                        if existing_mod.get('mod_id') == mod['mod_id']:
                            dlg.after(0, lambda: show_error(f"Mod '{mod['name']}' (ID: {mod['mod_id']}) already exists in modlist"))
                            return
                    
                    # Success callback
                    dlg.after(0, lambda: on_success(mod))
                    
                finally:
                    # Cleanup temp file
                    try:
                        if temp_file and Path(temp_file).exists():
                            Path(temp_file).unlink()
                    except Exception:
                        pass
            
            thread = threading.Thread(target=extract_metadata, daemon=True)
            thread.start()
        
        def download_and_extract_async():
            """Download and extract metadata in background thread."""
            try:
                import tempfile
                from pathlib import Path
                
                result = app.mod_installer.download_archive({'download_url': url, 'name': 'temp'})
                temp_file, is_7z = result.temp_path, result.is_7z
                
                # Handle Google Drive HTML response (virus scan warning)
                if temp_file == 'GDRIVE_HTML':
                    def show_gdrive_dialog():
                        status_var.set("")
                        result = custom_dialogs.askyesno(
                            "Google Drive Confirmation Required",
                            "This file is too large for Google's virus scan.\n\n"
                            "Google Drive requires manual confirmation to download large files.\n"
                            "The download URL will be automatically fixed to bypass this warning.\n\n"
                            "Do you want to continue?"
                        )
                        
                        if result:
                            # Fix the URL to bypass virus scan and retry
                            fixed_url = fix_google_drive_url(url)
                            download_retry_async(fixed_url)
                        else:
                            re_enable_buttons()
                    
                    dlg.after(0, show_gdrive_dialog)
                    return
                
                if not temp_file:
                    dlg.after(0, lambda: show_error("Failed to download archive from URL"))
                    return
                
                # Continue with metadata extraction
                dlg.after(0, lambda: process_metadata(temp_file, is_7z, url))
                    
            except Exception as e:
                dlg.after(0, lambda: show_error(f"Failed to process mod: {e}"))
        
        # Launch async download in background thread
        thread = threading.Thread(target=download_and_extract_async, daemon=True)
        thread.start()

    btn_frame = tk.Frame(dlg, bg=TriOSTheme.SURFACE)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=12)
    
    btn_container = tk.Frame(btn_frame, bg=TriOSTheme.SURFACE)
    btn_container.pack(expand=True)
    
    add_button = _create_button(btn_container, "Add Mod", submit, width=12, button_type="success")
    add_button.pack(side=tk.LEFT, padx=6)
    
    cancel_button = _create_button(btn_container, "Cancel", dlg.destroy, width=12, button_type="secondary")
    cancel_button.pack(side=tk.LEFT, padx=6)


def open_edit_mod_dialog(parent, app, current_mod):
    dlg = _create_dialog(parent, f"Mod Info: {current_mod.get('name', 'Unknown')}", 550, 320)

    mod_id_value = current_mod.get('mod_id', 'N/A')
    mod_name_value = current_mod.get('name', 'Unknown')
    mod_version_value = current_mod.get('mod_version', 'N/A')
    game_version_value = current_mod.get('game_version', current_mod.get('version', 'N/A'))
    category_value = current_mod.get('category', 'Uncategorized')
    url_value = current_mod.get('download_url', '')

    name_var = tk.StringVar(value=mod_name_value)
    url_var = tk.StringVar(value=url_value)
    category_var = tk.StringVar(value=category_value)

    row = 0
    
    tk.Label(dlg, text="Mod ID:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=(12, 6))
    tk.Label(dlg, text=mod_id_value, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=(12, 6))
    row += 1
    
    _, name_entry = _create_form_field(dlg, row, "Display Name:", textvariable=name_var)
    row += 1
    
    tk.Label(dlg, text="Mod Version:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    tk.Label(dlg, text=mod_version_value, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=6)
    row += 1
    
    tk.Label(dlg, text="Game Version:", bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    tk.Label(dlg, text=game_version_value, bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=6)
    row += 1
    
    _, category_combo = _create_form_field(dlg, row, "Category:", widget_type='combobox',
                                           textvariable=category_var, values=app.categories, state='readonly')
    row += 1
    
    _, url_entry = _create_form_field(dlg, row, "Download URL:", textvariable=url_var)
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
    
    btn_container = tk.Frame(btn_frame, bg=TriOSTheme.SURFACE)
    btn_container.pack(expand=True)
    
    _create_button(btn_container, "Save Changes", submit, width=14, button_type="success").pack(side=tk.LEFT, padx=6)
    _create_button(btn_container, "Close", dlg.destroy, width=12, button_type="secondary").pack(side=tk.LEFT, padx=6)


def open_manage_categories_dialog(parent, app):
    dlg = _create_dialog(parent, "Manage Categories", 500, 450, resizable=True)
    dlg.minsize(400, 350)
    
    tk.Label(dlg, text="Categories (in display order):", font=("Arial", 12, "bold"),
            bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).pack(pady=(10, 5))
    
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
    
    up_btn = _create_button(move_frame, LogSymbols.UPDATED, move_up, width=3, font_size=14, button_type="secondary")
    up_btn.pack(pady=(0, 5))
    
    down_btn = _create_button(move_frame, UISymbols.ARROW_DOWN_ALT, move_down, width=3, font_size=14, button_type="secondary")
    down_btn.pack(pady=(5, 0))
        
    refresh_category_listbox()
    
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
            app.log(f"Renamed category: {old_name} {LogSymbols.ARROW_RIGHT} {new_name}")
    
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
        parent=parent,
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
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
        parent=parent,
        title="Export modlist to CSV",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    
    if not csv_file:
        return
    
    try:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            # Write metadata section
            metadata_writer = csv.writer(f)
            metadata_writer.writerow(['modlist_name', 'author', 'starsector_version', 'modlist_description', 'modlist_version'])
            metadata_writer.writerow([
                app.modlist_data.get('modlist_name', ''),
                app.modlist_data.get('author', ''),
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
        
        app.log(f"{LogSymbols.SUCCESS} Exported {len(app.modlist_data.get('mods', []))} mods to {csv_file}", success=True)
    except Exception as e:
        app.log(f"{LogSymbols.ERROR} Export error: {e}", error=True)


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
        
        # Early return: no metadata section, parse as regular CSV
        if not (has_metadata and not has_mod_headers):
            app.log(f"  No metadata section detected, parsing as regular CSV")
        else:
            # Parse metadata from first line
            app.log(f"  Parsing metadata section...")
            reader = csv.DictReader([lines[0], lines[1]])  # Header + values
            metadata_row = next(reader)
            
            app.log(f"  Detected metadata row keys: {list(metadata_row.keys())}")
            app.log(f"  Detected metadata row values: {list(metadata_row.values())}")
            
            # Update modlist metadata using mapping
            metadata_mapping = {
                'modlist_name': 'modlist_name',
                'author': 'author',
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
                        result = app.mod_installer.download_archive({'download_url': url, 'name': 'temp'})
                        temp_file, is_7z = result.temp_path, result.is_7z
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
                                    app.log(f"  {LogSymbols.SUCCESS} Auto-detected: {name} (ID: {mod_id})", info=True)
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
        app.log(f"  {LogSymbols.ERROR} Error importing CSV: {type(e).__name__}: {e}", error=True)
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
    dialog = _create_dialog(parent, "Google Drive Confirmation Required")
    
    main_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
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
        text=f"{LogSymbols.WARNING}  Google can't verify these files due to their size. Confirm only if from a trusted source.",
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
    
    _center_dialog(dialog, parent)
    dialog.wait_window()


def open_restore_backup_dialog(parent, app):
    """Show enhanced dialog to restore a backup with detailed information.
    
    Args:
        parent: Parent window
        app: Main application instance
    """
    from datetime import datetime
    from utils.backup_manager import BackupManager
    import json
    
    starsector_dir = app.starsector_path.get()
    if not starsector_dir:
        showerror("Error", "Starsector path not set. Please configure it in settings.", parent)
        return
    
    try:
        backup_manager = BackupManager(starsector_dir)
        backups = backup_manager.list_backups()
        
        if not backups:
            showinfo("No Backups", "No backups found. Backups are created automatically before installation.", parent)
            return
        
        # Create dialog with larger size for details panel
        dialog = _create_dialog(parent, "Restore Backup", width=750, height=500)
        
        # Title
        title_label = tk.Label(dialog, text="Select a backup to restore", font=("Arial", 13, "bold"), 
                bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY)
        title_label.pack(pady=(10, 5))
        
        # Main content frame (horizontal split)
        content_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Left panel: Backup list
        left_frame = tk.Frame(content_frame, bg=TriOSTheme.SURFACE)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        
        tk.Label(left_frame, text="Available Backups:", font=("Arial", 10, "bold"),
                bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY).pack(anchor=tk.W, pady=(0, 5))
        
        list_frame = tk.Frame(left_frame, bg=TriOSTheme.SURFACE)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, width=28,
                            bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                            selectbackground=TriOSTheme.PRIMARY, selectforeground=TriOSTheme.SURFACE_DARK,
                            font=("Courier", 10), activestyle='none')
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Right panel: Backup details
        right_frame = tk.Frame(content_frame, bg=TriOSTheme.SURFACE_DARK, relief=tk.FLAT, bd=1)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Details header
        details_header = tk.Label(right_frame, text="Backup Details", font=("Arial", 11, "bold"),
                                 bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.PRIMARY, anchor=tk.W)
        details_header.pack(fill=tk.X, padx=12, pady=(10, 8))
        
        # Details text widget with scrollbar
        details_frame = tk.Frame(right_frame, bg=TriOSTheme.SURFACE_DARK)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        
        details_scroll = tk.Scrollbar(details_frame)
        details_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        details_text = tk.Text(details_frame, yscrollcommand=details_scroll.set, height=15,
                              bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                              font=("Arial", 10), wrap=tk.WORD, relief=tk.FLAT, bd=0,
                              cursor="arrow", state=tk.DISABLED)
        details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        details_scroll.config(command=details_text.yview)
        
        # Helper function to extract mod count from backup
        def get_backup_details(backup_path):
            """Extract detailed information from a backup."""
            details = {}
            
            # Read enabled_mods.json
            enabled_mods_file = backup_path / "enabled_mods.json"
            if enabled_mods_file.exists():
                try:
                    with open(enabled_mods_file, 'r', encoding='utf-8') as f:
                        enabled_data = json.load(f)
                        details['mod_count'] = len(enabled_data.get('enabledMods', []))
                        details['enabled_mods'] = enabled_data.get('enabledMods', [])
                except:
                    details['mod_count'] = 'Unknown'
                    details['enabled_mods'] = []
            else:
                details['mod_count'] = 'Unknown'
                details['enabled_mods'] = []
            
            return details
        
        # Populate backup list
        for backup_path, metadata in backups:
            timestamp = metadata.get('timestamp', 'Unknown')
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                formatted = dt.strftime("%Y-%m-%d %H:%M")
            except:
                formatted = timestamp
            listbox.insert(tk.END, formatted)
        
        # Update details panel when selection changes
        def on_select(event):
            selection = listbox.curselection()
            if not selection:
                return
            
            idx = selection[0]
            backup_path, metadata = backups[idx]
            timestamp = metadata.get('timestamp', 'Unknown')
            
            # Get additional details
            backup_details = get_backup_details(backup_path)
            
            # Format timestamp nicely
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                formatted_date = dt.strftime("%A, %B %d, %Y")
                formatted_time = dt.strftime("%I:%M:%S %p")
            except:
                formatted_date = timestamp
                formatted_time = ""
            
            # Build details text
            details_str = f"📅 Date: {formatted_date}\n"
            if formatted_time:
                details_str += f"🕐 Time: {formatted_time}\n"
            details_str += f"\n📊 Number of Mods: {backup_details['mod_count']}\n"
            
            # Show first few mods if available
            if backup_details['enabled_mods'] and isinstance(backup_details['mod_count'], int):
                details_str += f"\n📦 Enabled Mods:\n"
                max_show = min(15, len(backup_details['enabled_mods']))
                for i, mod_id in enumerate(backup_details['enabled_mods'][:max_show]):
                    details_str += f"  • {mod_id}\n"
                
                if len(backup_details['enabled_mods']) > max_show:
                    remaining = len(backup_details['enabled_mods']) - max_show
                    details_str += f"  ... and {remaining} more mod(s)\n"
            
            # Update details panel
            details_text.config(state=tk.NORMAL)
            details_text.delete("1.0", tk.END)
            details_text.insert("1.0", details_str)
            details_text.config(state=tk.DISABLED)
        
        listbox.bind('<<ListboxSelect>>', on_select)
        
        # Select first backup by default
        if backups:
            listbox.selection_set(0)
            listbox.event_generate('<<ListboxSelect>>')
        
        def on_restore():
            selection = listbox.curselection()
            if not selection:
                showwarning("No Selection", "Please select a backup to restore.", parent)
                return
            
            idx = selection[0]
            backup_path, metadata = backups[idx]
            timestamp = metadata.get('timestamp', 'Unknown')
            
            # Format timestamp for confirmation
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                formatted = dt.strftime("%Y-%m-%d at %H:%M:%S")
            except:
                formatted = timestamp
            
            # Confirm restore
            if not askyesno("Confirm Restore", 
                          f"Restore backup from {formatted}?\n\n" +
                          "This will replace your current enabled_mods.json file.\n" +
                          "A backup of the current state will be created automatically.", parent):
                return
            
            # Use the safe restore function from app
            success, error = app.restore_backup_safely(backup_path, formatted)
            
            if success:
                showsuccess("Success", "Backup restored successfully!\n\nYour mod configuration has been restored.", parent)
                dialog.destroy()
            else:
                showerror("Restore Failed", f"Failed to restore backup:\n{error}", parent)
        
        def on_delete():
            selection = listbox.curselection()
            if not selection:
                showwarning("No Selection", "Please select a backup to delete.", parent)
                return
            
            idx = selection[0]
            backup_path, metadata = backups[idx]
            timestamp = metadata.get('timestamp', 'Unknown')
            
            # Format timestamp for confirmation
            try:
                dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                formatted = dt.strftime("%Y-%m-%d at %H:%M:%S")
            except:
                formatted = timestamp
            
            if not askyesno("Confirm Delete", 
                          f"Delete backup from {formatted}?\n\n" +
                          "This action cannot be undone.", parent):
                return
            
            success, error = backup_manager.delete_backup(backup_path)
            if success:
                app.log(f"{LogSymbols.SUCCESS} Deleted backup: {formatted}")
                listbox.delete(idx)
                backups.pop(idx)
                
                # Clear details panel
                details_text.config(state=tk.NORMAL)
                details_text.delete("1.0", tk.END)
                details_text.config(state=tk.DISABLED)
                
                # Select next or previous backup
                if backups:
                    new_idx = min(idx, len(backups) - 1)
                    listbox.selection_set(new_idx)
                    listbox.event_generate('<<ListboxSelect>>')
                else:
                    showinfo("No Backups", "All backups deleted.", parent)
                    dialog.destroy()
            else:
                showerror("Delete Failed", f"Failed to delete backup:\n{error}", parent)
        
        # Buttons frame
        btn_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
        btn_frame.pack(pady=(5, 15))
        
        restore_btn = _create_button(btn_frame, "Restore Backup", on_restore, width=16, button_type="success")
        restore_btn.pack(side=tk.LEFT, padx=5)
        
        delete_btn = _create_button(btn_frame, "Delete Backup", on_delete, width=16, button_type="danger")
        delete_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = _create_button(btn_frame, "Cancel", dialog.destroy, width=12, button_type="secondary")
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        _center_dialog(dialog, parent)
        
    except Exception as e:
        app.log(f"{LogSymbols.ERROR} Error accessing backups: {e}", error=True)
        showerror("Error", f"Failed to access backups:\n{e}", parent)


def open_edit_modlist_metadata_dialog(parent, app):
    """Open dialog to edit modlist metadata (name, version, description, etc.).
    
    Args:
        parent: Parent window
        app: Main application instance
    """
    if not app.modlist_data:
        return
    
    # Create dialog
    dialog = _create_dialog(parent, "Edit Modlist Metadata", width=500, height=400)
    
    # Title
    tk.Label(dialog, text="Modlist Metadata", font=("Arial", 14, "bold"),
            bg=TriOSTheme.SURFACE, fg=TriOSTheme.PRIMARY).pack(pady=(15, 20))
    
    # Form frame
    form_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
    form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
    
    # Fields
    fields = [
        ("Modlist Name:", "modlist_name", app.modlist_data.get("modlist_name", "")),
        ("Version:", "version", app.modlist_data.get("version", "")),
        ("Starsector Version:", "starsector_version", app.modlist_data.get("starsector_version", "")),
        ("Author:", "author", app.modlist_data.get("author", "")),
    ]
    
    entries = {}
    for i, (label_text, key, value) in enumerate(fields):
        tk.Label(form_frame, text=label_text, font=("Arial", 10),
                bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY,
                anchor=tk.W).grid(row=i, column=0, sticky="w", pady=5)
        
        entry = tk.Entry(form_frame, font=("Arial", 10),
                       bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                       insertbackground=TriOSTheme.PRIMARY)
        entry.insert(0, value)
        entry.grid(row=i, column=1, sticky="ew", pady=5, padx=(10, 0))
        entries[key] = entry
    
    form_frame.columnconfigure(1, weight=1)
    
    # Description field (multi-line)
    tk.Label(form_frame, text="Description:", font=("Arial", 10),
            bg=TriOSTheme.SURFACE, fg=TriOSTheme.TEXT_PRIMARY,
            anchor=tk.W).grid(row=len(fields), column=0, sticky="nw", pady=5)
    
    desc_text = tk.Text(form_frame, font=("Arial", 10), height=6,
                      bg=TriOSTheme.SURFACE_DARK, fg=TriOSTheme.TEXT_PRIMARY,
                      insertbackground=TriOSTheme.PRIMARY, wrap=tk.WORD)
    desc_text.insert("1.0", app.modlist_data.get("description", ""))
    desc_text.grid(row=len(fields), column=1, sticky="ew", pady=5, padx=(10, 0))
    entries['description'] = desc_text
    
    # Buttons
    button_frame = tk.Frame(dialog, bg=TriOSTheme.SURFACE)
    button_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
    
    def save_metadata():
        """Save the edited metadata."""
        app.modlist_data["modlist_name"] = entries["modlist_name"].get().strip()
        app.modlist_data["version"] = entries["version"].get().strip()
        app.modlist_data["starsector_version"] = entries["starsector_version"].get().strip()
        app.modlist_data["author"] = entries["author"].get().strip()
        app.modlist_data["description"] = desc_text.get("1.0", tk.END).strip()
        
        app.save_modlist_config()
        app.display_modlist_info()
        app.log("Modlist metadata updated")
        dialog.destroy()
        showsuccess("Success", "Modlist metadata has been updated.", parent)
    
    save_btn = _create_button(button_frame, "Save", save_metadata, width=12, button_type="success")
    save_btn.pack(side=tk.LEFT, padx=(0, 5))
    
    cancel_btn = _create_button(button_frame, "Cancel", dialog.destroy, width=12, button_type="secondary")
    cancel_btn.pack(side=tk.LEFT)
    
    _center_dialog(dialog, parent)
