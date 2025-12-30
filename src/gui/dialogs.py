import tkinter as tk
from tkinter import ttk, filedialog
import threading
import re
from pathlib import Path
from .ui_builder import _create_button
from utils.theme import AppTheme
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
    dialog.configure(bg=AppTheme.SURFACE)
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
    label = tk.Label(parent, text=label_text, bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold'))
    label.grid(row=row, column=0, sticky="e", padx=8, pady=6)
    
    if widget_type == 'combobox':
        widget = ttk.Combobox(parent, width=width-3, **widget_kwargs)
    else:
        widget_kwargs.setdefault('bg', AppTheme.SURFACE_DARK)
        widget_kwargs.setdefault('fg', AppTheme.TEXT_PRIMARY)
        widget_kwargs.setdefault('insertbackground', AppTheme.PRIMARY)
        widget_kwargs.setdefault('relief', tk.FLAT)
        widget_kwargs.setdefault('highlightthickness', 1)
        widget_kwargs.setdefault('highlightbackground', AppTheme.BORDER)
        widget_kwargs.setdefault('highlightcolor', AppTheme.PRIMARY)
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
        self.dialog.configure(bg=AppTheme.SURFACE)
        
        # Main content frame
        content_frame = tk.Frame(self.dialog, bg=AppTheme.SURFACE)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Icon and message
        message_frame = tk.Frame(content_frame, bg=AppTheme.SURFACE)
        message_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Icon
        icons = {"info": LogSymbols.INFO, "success": LogSymbols.SUCCESS, "warning": LogSymbols.WARNING, "error": LogSymbols.ERROR, "question": LogSymbols.QUESTION}
        tk.Label(message_frame, text=icons.get(dialog_type, LogSymbols.INFO), 
            font=("Arial", 36, "bold"), bg=AppTheme.SURFACE, fg=AppTheme.PRIMARY).pack(side=tk.LEFT, padx=(0, 15))
        
        # Message
        tk.Label(message_frame, text=message, font=("Arial", 11),
            wraplength=350, justify=tk.LEFT, bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = tk.Frame(content_frame, bg=AppTheme.SURFACE)
        button_frame.pack(fill=tk.X)
        
        # Default buttons
        if buttons is None:
            buttons = [("Yes", True), ("No", False)] if dialog_type == "question" else [("OK", True)]
        
        # Center button container
        button_container = tk.Frame(button_frame, bg=AppTheme.SURFACE)
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


def show_validation_report(parent, github_mods, gdrive_mods, mediafire_mods, other_domains, failed_list):
    result = {'action': 'cancel'}
    
    dialog = _create_dialog(parent, "Download Sources Analysis")
    
    main_frame = tk.Frame(dialog, bg=AppTheme.SURFACE)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    tk.Label(main_frame, text="Download Sources Analysis", 
             font=("Arial", 14, "bold"), bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY).pack(pady=(0, 15))
    
    # Summary frame
    summary_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    summary_frame.pack(fill=tk.X, pady=(0, 15))
    
    # GitHub mods
    if len(github_mods) > 0:
        github_frame = tk.Frame(summary_frame, bg=AppTheme.SURFACE)
        github_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(github_frame, text=f"{LogSymbols.SUCCESS} {len(github_mods)} mod(s) from GitHub", 
                font=("Arial", 11, "bold"), bg=AppTheme.SURFACE, fg=AppTheme.GITHUB_FG).pack(anchor=tk.W)
        
        # List GitHub mods
        github_list_frame = tk.Frame(github_frame, bg=AppTheme.GITHUB_BG)
        github_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        github_text = tk.Text(github_list_frame, height=min(4, len(github_mods)), width=55,
                     font=("Courier", 9), wrap=tk.WORD, bg=AppTheme.GITHUB_BG, fg=AppTheme.TEXT_PRIMARY, 
                             relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        for mod in github_mods:
            github_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
        github_text.config(state=tk.DISABLED)
        github_text.pack(padx=5, pady=5)
    
    # Mediafire mods
    if len(mediafire_mods) > 0:
        mediafire_frame = tk.Frame(summary_frame, bg=AppTheme.SURFACE)
        mediafire_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(mediafire_frame, text=f"{LogSymbols.SUCCESS} {len(mediafire_mods)} mod(s) from Mediafire", 
            font=("Arial", 11, "bold"), bg=AppTheme.SURFACE, fg=AppTheme.MEDIAFIRE_FG).pack(anchor=tk.W)
        
        # List Mediafire mods
        mediafire_list_frame = tk.Frame(mediafire_frame, bg=AppTheme.MEDIAFIRE_BG)
        mediafire_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        mediafire_text = tk.Text(mediafire_list_frame, height=min(4, len(mediafire_mods)), width=55,
                     font=("Courier", 9), wrap=tk.WORD, bg=AppTheme.MEDIAFIRE_BG, fg=AppTheme.TEXT_PRIMARY, 
                             relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        for mod in mediafire_mods:
            mediafire_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
        mediafire_text.config(state=tk.DISABLED)
        mediafire_text.pack(padx=5, pady=5)
    
    # Google Drive mods with info
    if len(gdrive_mods) > 0:
        gdrive_frame = tk.Frame(summary_frame, bg=AppTheme.SURFACE)
        gdrive_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(gdrive_frame, text=f"{LogSymbols.SUCCESS} {len(gdrive_mods)} mod(s) from Google Drive", 
            font=("Arial", 11, "bold"), bg=AppTheme.SURFACE, fg=AppTheme.GDRIVE_FG).pack(anchor=tk.W)
        
        # Info about large files
        info_text = tk.Label(gdrive_frame, 
            text="Some Google Drive links are not direct downloads and may require an additional action. The app will attempt to auto-fix them.",
            font=("Arial", 9, "italic"), bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY, wraplength=450, justify=tk.LEFT)
        info_text.pack(anchor=tk.W, padx=(20, 0), pady=(2, 0))
        
        # List Google Drive mods
        gdrive_list_frame = tk.Frame(gdrive_frame, bg=AppTheme.GDRIVE_BG)
        gdrive_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        gdrive_text = tk.Text(gdrive_list_frame, height=min(4, len(gdrive_mods)), width=55,
                     font=("Courier", 9), wrap=tk.WORD, bg=AppTheme.GDRIVE_BG, fg=AppTheme.TEXT_PRIMARY, 
                             relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        for mod in gdrive_mods:
            name = mod.get('name', 'Unknown')
            url = mod.get('download_url', '')
            # Heuristic: mark as 'may need fix' only if not already a direct download
            # - Not usercontent
            # - Not confirm=t
            # - Not export=download with id
            is_gdrive = 'drive.google.com' in url
            is_usercontent = 'drive.usercontent.google.com' in url
            has_confirm = 'confirm=t' in url
            has_export_id = 'export=download' in url and 'id=' in url
            needs_fix = is_gdrive and not (is_usercontent or has_confirm or has_export_id)
            suffix = " [may need fix]" if needs_fix else ""
            gdrive_text.insert(tk.END, f"  • {name}{suffix}\n")
        gdrive_text.config(state=tk.DISABLED)
        gdrive_text.pack(padx=5, pady=5)
    
    # Other domains
    if other_domains:
        other_frame = tk.Frame(summary_frame, bg=AppTheme.SURFACE)
        other_frame.pack(fill=tk.X, pady=(0, 8))
        
        total_other = sum(len(mods) for mods in other_domains.values())
        tk.Label(other_frame, text=f"{LogSymbols.WARNING} {total_other} mod(s) from other sources", 
            font=("Arial", 11, "bold"), bg=AppTheme.SURFACE, fg=AppTheme.OTHER_FG).pack(anchor=tk.W)
        
        # List each domain with its mods
        other_list_frame = tk.Frame(other_frame, bg=AppTheme.OTHER_BG)
        other_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        other_text = tk.Text(other_list_frame, height=min(5, total_other), width=55,
                    font=("Courier", 9), wrap=tk.WORD, bg=AppTheme.OTHER_BG, fg=AppTheme.TEXT_PRIMARY, 
                            relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        
        for domain, mods in sorted(other_domains.items()):
            for mod in mods:
                other_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')} ({domain})\n")
        
        other_text.config(state=tk.DISABLED)
        other_text.pack(padx=5, pady=5)
    
    # Failed mods
    if failed_list:
        failed_frame = tk.Frame(summary_frame, bg=AppTheme.SURFACE)
        failed_frame.pack(fill=tk.X, pady=(0, 0))
        
        tk.Label(failed_frame, text=f"{LogSymbols.ERROR} {len(failed_list)} mod(s) inaccessible", 
            font=("Arial", 11, "bold"), bg=AppTheme.SURFACE, fg=AppTheme.FAILED_FG).pack(anchor=tk.W, pady=(0, 2))
        
        tk.Label(failed_frame, 
            text="These mods cannot be downloaded. Check URLs or contact mod authors.",
            font=("Arial", 9, "italic"), bg=AppTheme.SURFACE, fg=AppTheme.TEXT_SECONDARY, wraplength=450, justify=tk.LEFT).pack(anchor=tk.W, padx=(20, 0), pady=(2, 0))
        
        # Scrollable list of failed mods
        failed_list_frame = tk.Frame(failed_frame, bg=AppTheme.FAILED_BG)
        failed_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        failed_text = tk.Text(failed_list_frame, height=min(5, len(failed_list)), width=55, 
                     font=("Courier", 9), wrap=tk.WORD, bg=AppTheme.FAILED_BG, fg=AppTheme.TEXT_PRIMARY, 
                             relief=tk.FLAT, highlightthickness=0, borderwidth=0)
        
        for fail in failed_list:
            mod_name = fail['mod'].get('name', 'Unknown')
            error = fail['error']
            failed_text.insert(tk.END, f"  • {mod_name}: {error}\n")
        
        failed_text.config(state=tk.DISABLED)
        failed_text.pack(padx=5, pady=5)
    
    # Buttons frame
    button_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    button_frame.pack(fill=tk.X, pady=(15, 0))
    
    def on_continue():
        result['action'] = 'continue'
        dialog.destroy()
    
    def on_cancel():
        result['action'] = 'cancel'
        dialog.destroy()
    
    # Center the buttons
    button_container = tk.Frame(button_frame, bg=AppTheme.SURFACE)
    button_container.pack(anchor=tk.CENTER)
    
    if len(github_mods) > 0 or len(gdrive_mods) > 0 or len(mediafire_mods) > 0 or other_domains:
        _create_button(button_container, "Continue", on_continue,
                      width=12, button_type="success").pack(side=tk.LEFT, padx=5)
    
    _create_button(button_container, "Cancel", on_cancel,
                  width=12, button_type="secondary").pack(side=tk.LEFT, padx=5)
    
    # Keyboard bindings
    dialog.bind("<Escape>", lambda e: on_cancel())
    dialog.bind("<Return>", lambda e: on_continue() if len(github_mods) > 0 or len(gdrive_mods) > 0 or len(mediafire_mods) > 0 or other_domains else None)
    
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

    status_label = tk.Label(dlg, textvariable=status_var, bg=AppTheme.SURFACE, fg=AppTheme.TEXT_SECONDARY, wraplength=500)
    status_label.grid(row=2, column=0, columnspan=2, padx=8, pady=6)

    def submit():
        url = url_var.get().strip()
        if not url:
            showerror("Error", "Download URL is required")
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
                        # Important: keep the original URL so the user can review it,
                        # even if we had to use a fixed URL to retrieve metadata.
                        "download_url": url,
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
                
                # Handle Google Drive HTML response (non-direct link)
                if temp_file == 'GDRIVE_HTML':
                    def show_gdrive_dialog():
                        status_var.set("")
                        result = askyesno(
                            "Google Drive Confirmation Required",
                            "This Google Drive link is not a direct download.\n\n"
                            "Manual confirmation may be required to start the download.\n"
                            "The URL will be automatically converted to a direct download link.\n\n"
                            "Do you want to continue?"
                        )
                        
                        if result:
                            # Fix the URL to direct download and retry
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

    btn_frame = tk.Frame(dlg, bg=AppTheme.SURFACE)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=12)
    
    btn_container = tk.Frame(btn_frame, bg=AppTheme.SURFACE)
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
    
    tk.Label(dlg, text="Mod ID:", bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=(12, 6))
    tk.Label(dlg, text=mod_id_value, bg=AppTheme.SURFACE, fg=AppTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=(12, 6))
    row += 1
    
    _, name_entry = _create_form_field(dlg, row, "Display Name:", textvariable=name_var)
    row += 1
    
    tk.Label(dlg, text="Mod Version:", bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    tk.Label(dlg, text=mod_version_value, bg=AppTheme.SURFACE, fg=AppTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=6)
    row += 1
    
    tk.Label(dlg, text="Game Version:", bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY, font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky="e", padx=8, pady=6)
    tk.Label(dlg, text=game_version_value, bg=AppTheme.SURFACE, fg=AppTheme.TEXT_SECONDARY, anchor='w').grid(row=row, column=1, sticky="w", padx=8, pady=6)
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
            showerror("Error", "Display name cannot be empty")
            return
        
        if not url:
            showerror("Error", "Download URL is required")
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
        showsuccess("Success", f"Mod info for '{name}' has been updated")
        dlg.destroy()

    btn_frame = tk.Frame(dlg, bg=AppTheme.SURFACE)
    btn_frame.grid(row=row, column=0, columnspan=2, pady=12)
    
    btn_container = tk.Frame(btn_frame, bg=AppTheme.SURFACE)
    btn_container.pack(expand=True)
    
    _create_button(btn_container, "Save Changes", submit, width=14, button_type="success").pack(side=tk.LEFT, padx=6)
    _create_button(btn_container, "Close", dlg.destroy, width=12, button_type="secondary").pack(side=tk.LEFT, padx=6)


def open_manage_categories_dialog(parent, app):
    dlg = _create_dialog(parent, "Manage Categories", 500, 450, resizable=True)
    dlg.minsize(400, 350)
    
    tk.Label(dlg, text="Categories (in display order):", font=("Arial", 12, "bold"),
            bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY).pack(pady=(10, 5))
    
    main_frame = tk.Frame(dlg, bg=AppTheme.SURFACE)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
    
    # Listbox for categories
    list_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(list_frame, bg=AppTheme.SURFACE)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    cat_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=15,
                            bg=AppTheme.SURFACE_DARK, fg=AppTheme.TEXT_PRIMARY,
                            selectbackground=AppTheme.PRIMARY, selectforeground=AppTheme.SURFACE_DARK,
                            relief=tk.FLAT, highlightthickness=0, borderwidth=0)
    cat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=cat_listbox.yview)
    
    # Move buttons (↑↓)
    move_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
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
    
    btn_frame = tk.Frame(dlg, bg=AppTheme.SURFACE)
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
                showwarning("Duplicate", f"Category '{new_cat}' already exists", parent=dlg)
    
    def rename_category():
        selection = cat_listbox.curselection()
        if not selection:
            showwarning("No Selection", "Please select a category to rename", parent=dlg)
            return
        
        idx = selection[0]
        old_name = app.categories[idx]
        new_name = tk.simpledialog.askstring("Rename Category", f"Rename '{old_name}' to:", 
                                              initialvalue=old_name, parent=dlg)
        if new_name and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            if new_name in app.categories:
                showwarning("Duplicate", f"Category '{new_name}' already exists", parent=dlg)
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
            showwarning("No Selection", "Please select a category to delete", parent=dlg)
            return
        
        idx = selection[0]
        cat_name = app.categories[idx]
        
        # Check if category is in use
        in_use = any(mod.get('category') == cat_name for mod in app.modlist_data.get('mods', []))
        
        if in_use:
            response = askyesno("Category in Use", 
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
    
    center_frame = tk.Frame(btn_frame, bg=AppTheme.SURFACE)
    center_frame.pack(expand=True)
    
    btn_add = _create_button(center_frame, "Add", add_category, width=10, button_type="success")
    btn_add.pack(side=tk.LEFT, padx=5)
    
    btn_rename = _create_button(center_frame, "Rename", rename_category, width=10, button_type="info")
    btn_rename.pack(side=tk.LEFT, padx=5)
    
    btn_delete = _create_button(center_frame, "Delete", delete_category, width=10, button_type="danger")
    btn_delete.pack(side=tk.LEFT, padx=5)
    
    btn_close = _create_button(center_frame, "Close", dlg.destroy, width=10, button_type="secondary")
    btn_close.pack(side=tk.LEFT, padx=5)


def open_import_preset_dialog(parent, app):
    """Open dialog to load/import an existing preset."""
    import tkinter as tk
    from utils.theme import AppTheme
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get available presets
    presets = app.config_manager.list_presets()
    
    if not presets:
        showinfo(
            "No Presets",
            "No presets found in config/presets/\n\n"
            "Create a preset first by exporting your current modlist.",
            parent=parent
        )
        return
    
    # Create selection dialog
    dialog = tk.Toplevel(parent)
    dialog.title("Load Preset")
    dialog.geometry("500x400")
    dialog.resizable(False, False)
    dialog.configure(bg=AppTheme.SURFACE)
    dialog.transient(parent)
    dialog.grab_set()
    
    # Center dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
    y = (dialog.winfo_screenheight() // 2) - (400 // 2)
    dialog.geometry(f"500x400+{x}+{y}")
    
    # Main frame
    main_frame = tk.Frame(dialog, bg=AppTheme.SURFACE, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = tk.Label(
        main_frame,
        text="Load Preset",
        font=("Arial", 12, "bold"),
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_PRIMARY
    )
    title_label.pack(pady=(0, 10))
    
    # Info
    info_label = tk.Label(
        main_frame,
        text="Select a preset to load as your current modlist configuration.",
        font=("Arial", 9),
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_SECONDARY
    )
    info_label.pack(pady=(0, 15))
    
    # Listbox frame
    list_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
    
    scrollbar = tk.Scrollbar(list_frame, bg=AppTheme.SURFACE)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    preset_listbox = tk.Listbox(
        list_frame,
        yscrollcommand=scrollbar.set,
        font=("Courier", 10),
        bg=AppTheme.SURFACE_DARK,
        fg=AppTheme.TEXT_PRIMARY,
        selectbackground=AppTheme.PRIMARY,
        selectforeground=AppTheme.SURFACE_DARK,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=AppTheme.BORDER,
        highlightcolor=AppTheme.PRIMARY
    )
    preset_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=preset_listbox.yview)
    
    # Populate listbox and store preset data
    preset_data = []  # Store (name, path, has_lunalib) for each index
    for name, path, has_lunalib in presets:
        lunalib_indicator = "📘 " if has_lunalib else "   "
        preset_listbox.insert(tk.END, f"{lunalib_indicator}{name}")
        preset_data.append((name, path, has_lunalib))
    
    # Status label
    status_label = tk.Label(
        main_frame,
        text="",
        font=("Arial", 9),
        bg=AppTheme.SURFACE,
        fg=AppTheme.WARNING
    )
    status_label.pack(pady=(5, 15))
    
    def load_selected_preset():
        selection = preset_listbox.curselection()
        if not selection:
            status_label.config(text="⚠ Please select a preset", fg=AppTheme.WARNING)
            return
        
        # Get preset name from stored data (not from display text)
        idx = selection[0]
        preset_name, preset_path, has_lunalib = preset_data[idx]
        
        # Load preset
        modlist_data, lunalib_data, error = app.config_manager.load_preset(preset_name)
        
        if error:
            showerror("Load Failed", f"Could not load preset:\\n\\n{error}", parent=dialog)
            logger.error(f"Load preset failed: {error}")
            return
        
        # Ask for confirmation (will overwrite current modlist)
        confirm = askyesno(
            "Confirm Load",
            f"Load preset '{preset_name}'?\\n\\n"
            f"This will replace your current modlist configuration.",
            parent=dialog
        )
        
        if not confirm:
            return
        
        # Apply preset (replace current modlist_config.json)
        try:
            # Write new modlist
            app.config_manager.save_modlist_config(modlist_data)
            
            # Reload modlist data and UI
            app.modlist_data = modlist_data
            app.display_modlist_info()
            
            app.log(f"✓ Loaded preset: {preset_name}", success=True)
            logger.info(f"Loaded preset: {preset_name}")
            
            lunalib_msg = " (includes LunaSettings)" if lunalib_data else ""
            showsuccess(
                "Preset Loaded",
                f"Preset '{preset_name}' loaded successfully{lunalib_msg}!\\n\\n"
                f"Your modlist has been updated.",
                parent=parent
            )
            
            dialog.destroy()
            
        except Exception as e:
            error_msg = f"Failed to apply preset: {e}"
            showerror("Load Error", error_msg, parent=dialog)
            app.log(f"✗ {error_msg}", error=True)
            logger.error(error_msg)
    
    def cancel():
        logger.info("Load preset cancelled by user")
        dialog.destroy()
    
    # Buttons
    button_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    button_frame.pack(fill=tk.X)
    
    # Import _create_button for consistent styling
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from gui.ui_builder import _create_button
    
    cancel_btn = _create_button(
        button_frame,
        "Cancel",
        cancel,
        width=10,
        font_size=10,
        button_type="secondary"
    )
    cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
    
    load_btn = _create_button(
        button_frame,
        "Load Preset",
        load_selected_preset,
        width=12,
        font_size=10,
        button_type="primary"
    )
    load_btn.pack(side=tk.RIGHT)
    
    # Bind Enter key and double-click
    dialog.bind('<Return>', lambda e: load_selected_preset())
    dialog.bind('<Escape>', lambda e: cancel())
    preset_listbox.bind('<Double-Button-1>', lambda e: load_selected_preset())


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


def open_export_preset_dialog(root, app):
    """Open dialog to export current modlist as a preset.
    
    Args:
        root: Parent Tk root window
        app: ModlistInstaller instance with config_manager and log method
    """
    import tkinter as tk
    from utils.theme import AppTheme
    from pathlib import Path
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Create custom dialog
    dialog = tk.Toplevel(root)
    dialog.title("Export Preset")
    dialog.geometry("500x300")
    dialog.resizable(False, False)
    dialog.configure(bg=AppTheme.SURFACE)
    dialog.transient(root)
    dialog.grab_set()
    
    # Center dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
    y = (dialog.winfo_screenheight() // 2) - (300 // 2)
    dialog.geometry(f"500x300+{x}+{y}")
    
    # Get presets directory
    presets_dir = app.config_manager.presets_dir
    presets_dir.mkdir(parents=True, exist_ok=True)
    
    # Main frame
    main_frame = tk.Frame(dialog, bg=AppTheme.SURFACE, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Title
    title_label = tk.Label(
        main_frame,
        text="Export Current Modlist as Preset",
        font=("Arial", 12, "bold"),
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_PRIMARY
    )
    title_label.pack(pady=(0, 5))
    
    # Info label
    info_label = tk.Label(
        main_frame,
        text=f"Save location: {presets_dir}/",
        font=("Arial", 9),
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_SECONDARY
    )
    info_label.pack(pady=(0, 15))
    
    # Preset name entry
    name_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    name_frame.pack(fill=tk.X, pady=(0, 15))
    
    tk.Label(
        name_frame,
        text="Preset Name:",
        font=("Arial", 10),
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_PRIMARY
    ).pack(side=tk.LEFT, padx=(0, 10))
    
    preset_name_var = tk.StringVar()
    name_entry = tk.Entry(
        name_frame,
        textvariable=preset_name_var,
        font=("Arial", 10),
        bg=AppTheme.SURFACE_DARK,
        fg=AppTheme.TEXT_PRIMARY,
        insertbackground=AppTheme.PRIMARY,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=AppTheme.BORDER,
        highlightcolor=AppTheme.PRIMARY
    )
    name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    name_entry.focus_set()
    
    # Checkbox for including LunaLib
    include_lunalib_var = tk.BooleanVar(value=False)
    checkbox_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    checkbox_frame.pack(fill=tk.X, pady=(0, 10))
    
    lunalib_check = tk.Checkbutton(
        checkbox_frame,
        text="Include current LunaSettings from game",
        variable=include_lunalib_var,
        font=("Arial", 10),
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_PRIMARY,
        selectcolor=AppTheme.SURFACE_DARK,
        activebackground=AppTheme.SURFACE,
        activeforeground=AppTheme.TEXT_PRIMARY
    )
    lunalib_check.pack(anchor=tk.W)
    
    # Description label
    desc_label = tk.Label(
        main_frame,
        text="This will save your current modlist configuration.\n"
             "If checked, it will also copy the LunaSettings folder\n"
             "from your Starsector installation.",
        font=("Arial", 9),
        bg=AppTheme.SURFACE,
        fg=AppTheme.TEXT_SECONDARY,
        justify=tk.LEFT
    )
    desc_label.pack(pady=(0, 15))
    
    # Status label
    status_label = tk.Label(
        main_frame,
        text="",
        font=("Arial", 9),
        bg=AppTheme.SURFACE,
        fg=AppTheme.WARNING
    )
    status_label.pack(pady=(5, 15))
    
    def export_preset():
        preset_name = preset_name_var.get().strip()
        if not preset_name:
            status_label.config(text="⚠ Please enter a preset name", fg=AppTheme.WARNING)
            return

        include_lunalib = include_lunalib_var.get()
        starsector_path = None

        from pathlib import Path
        preset_path = presets_dir / preset_name
        if preset_path.exists():
            # Ask for confirmation before overwriting
            if not askyesno(
                "Overwrite Preset?",
                f"Preset '{preset_name}' already exists. Overwrite?",
                parent=dialog
            ):
                status_label.config(text=f"✗ Export cancelled (preset exists)", fg=AppTheme.WARNING)
                return

        if include_lunalib:
            # Get Starsector path from app
            starsector_path = app.starsector_path.get()
            if not starsector_path or not Path(starsector_path).exists():
                status_label.config(
                    text="⚠ Valid Starsector path required for LunaLib export",
                    fg=AppTheme.WARNING
                )
                return

        # Export via ConfigManager
        success, error_msg = app.config_manager.export_current_modlist_as_preset(
            preset_name,
            include_lunalib=include_lunalib,
            starsector_path=starsector_path,
            overwrite=True if preset_path.exists() else False
        )

        if success:
            message = (
                f"Preset '{preset_name}' created successfully!\n\n"
                f"Location: {preset_path}/\n\n"
                "The preset folder contains:\n"
                "• modlist_config.json (your modlist)"
            )
            if include_lunalib:
                message += "\n• LunaSettings/ (game settings)"

            showsuccess("Export Successful", message, parent=root)
            app.log(f"✓ Exported preset: {preset_name}", info=True)
            logger.info(f"Exported preset: {preset_name}")
            dialog.destroy()
        else:
            status_label.config(text=f"✗ {error_msg}", fg=AppTheme.ERROR)
            logger.error(f"Export preset failed: {error_msg}")
    
    def cancel():
        logger.info("Export preset cancelled by user")
        dialog.destroy()
    
    # Buttons
    button_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    button_frame.pack(fill=tk.X)
    
    # Import _create_button for consistent styling
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from gui.ui_builder import _create_button
    
    cancel_btn = _create_button(
        button_frame,
        "Cancel",
        cancel,
        width=10,
        font_size=10,
        button_type="secondary"
    )
    cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))
    
    export_btn = _create_button(
        button_frame,
        "Export",
        export_preset,
        width=10,
        font_size=10,
        button_type="primary"
    )
    export_btn.pack(side=tk.RIGHT)
    
    # Bind Enter key
    dialog.bind('<Return>', lambda e: export_preset())
    dialog.bind('<Escape>', lambda e: cancel())


def open_patch_lunalib_dialog(root, app):
    """Open dialog to select a preset and patch LunaSettings.
    
    Args:
        root: Parent Tk root window
        app: ModlistInstaller instance with config_manager, starsector_path, and log method
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Check if Starsector path is set
        starsector_path = app.starsector_path.get()
        if not starsector_path or not Path(starsector_path).exists():
            showerror(
                "Starsector Path Required", 
                "Please set a valid Starsector installation path before patching LunaSettings.",
                parent=root
            )
            logger.warning("Patch LunaLib failed: no Starsector path set")
            return
        
        # List available presets with LunaSettings
        presets = app.config_manager.list_presets()
        lunalib_presets = [(name, path) for name, path, has_lunalib in presets if has_lunalib]
        
        if not lunalib_presets:
            showwarning(
                "No LunaLib Presets",
                "No presets with LunaSettings found.\n\n"
                "Create a preset with LunaSettings first by exporting with the checkbox enabled.",
                parent=root
            )
            logger.info("No LunaLib presets available")
            return
        
        # Create selection dialog
        dialog = _create_dialog(root, "Patch LunaSettings", 550, 400)
        
        main_frame = tk.Frame(dialog, bg=AppTheme.SURFACE)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        tk.Label(
            main_frame,
            text="Select a preset to patch LunaSettings",
            font=("Arial", 12, "bold"),
            bg=AppTheme.SURFACE,
            fg=AppTheme.TEXT_PRIMARY
        ).pack(pady=(0, 10))
        
        # Description
        desc_text = (
            "This will copy the preset's LunaSettings files to your\\n"
            "Starsector installation (saves/common/LunaSettings/).\\n\\n"
            "\u2022 All preset files will overwrite existing settings"
        )
        tk.Label(
            main_frame,
            text=desc_text,
            font=("Arial", 9),
            bg=AppTheme.SURFACE,
            fg=AppTheme.TEXT_SECONDARY,
            justify=tk.LEFT
        ).pack(pady=(0, 15))
        
        # Preset listbox
        list_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        scrollbar = tk.Scrollbar(list_frame, bg=AppTheme.SURFACE)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        preset_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=10,
            bg=AppTheme.SURFACE_DARK,
            fg=AppTheme.TEXT_PRIMARY,
            selectbackground=AppTheme.PRIMARY,
            selectforeground=AppTheme.SURFACE_DARK,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=AppTheme.BORDER,
            font=("Arial", 10)
        )
        preset_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=preset_listbox.yview)
        
        # Populate listbox
        for name, path in lunalib_presets:
            preset_listbox.insert(tk.END, name)
        
        # Select first preset by default
        if lunalib_presets:
            preset_listbox.selection_set(0)
        
        result = {'action': None, 'preset': None}
        
        def on_patch():
            selection = preset_listbox.curselection()
            if not selection:
                showwarning("No Selection", "Please select a preset to patch.", parent=dialog)
                return
            
            preset_name = lunalib_presets[selection[0]][0]
            result['action'] = 'patch'
            result['preset'] = preset_name
            dialog.destroy()
        
        def on_cancel():
            result['action'] = 'cancel'
            dialog.destroy()
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
        button_frame.pack(fill=tk.X)
        
        button_container = tk.Frame(button_frame, bg=AppTheme.SURFACE)
        button_container.pack(anchor=tk.CENTER)
        
        _create_button(button_container, "Patch LunaLib", on_patch, width=14, button_type="success").pack(side=tk.LEFT, padx=5)
        _create_button(button_container, "Cancel", on_cancel, width=12, button_type="secondary").pack(side=tk.LEFT, padx=5)
        
        # Keyboard bindings
        dialog.bind("<Return>", lambda e: on_patch())
        dialog.bind("<Escape>", lambda e: on_cancel())
        preset_listbox.bind("<Double-Button-1>", lambda e: on_patch())
        
        _center_dialog(dialog, root)
        dialog.wait_window()
        
        # Execute patch if user confirmed
        if result['action'] == 'patch' and result['preset']:
            preset_name = result['preset']
            app.log(f"Patching LunaLib config from preset: {preset_name}", info=True)
            
            success, error_msg, backup_path = app.config_manager.patch_lunalib_config(
                preset_name,
                starsector_path
            )
            
            if success:
                message = (
                    f"LunaLib config patched successfully from preset '{preset_name}'!\n\n"
                    f"Target: {starsector_path}/saves/common/LunaSettings/"
                )
                
                showsuccess("Patch Successful", message, parent=root)
                app.log(f"✓ LunaSettings patched from preset: {preset_name}", success=True)
                logger.info(f"LunaSettings patched: {preset_name}")
            else:
                showerror("Patch Failed", f"Failed to patch LunaSettings:\n\n{error_msg}", parent=root)
                app.log(f"✗ LunaSettings patch failed: {error_msg}", error=True)
                logger.error(f"LunaSettings patch failed: {error_msg}")
    
    except Exception as e:
        error_msg = f"Unexpected error during LunaSettings patch: {e}"
        showerror("Error", error_msg, parent=root)
        app.log(f"✗ {error_msg}", error=True)
        logger.exception("Patch LunaSettings dialog error")


def show_google_drive_confirmation_dialog(parent, failed_mods, on_confirm_callback, on_cancel_callback):
    dialog = _create_dialog(parent, "Google Drive Confirmation Required")
    
    main_frame = tk.Frame(dialog, bg=AppTheme.SURFACE)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    gdrive_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
    gdrive_frame.pack(fill=tk.X, pady=(0, 10))
    
    tk.Label(gdrive_frame, text=f"{len(failed_mods)} Google Drive mod(s) need confirmation to download:", 
             font=("Arial", 10, "bold"), bg=AppTheme.SURFACE, fg=AppTheme.ERROR).pack(anchor=tk.W, pady=(0, 8))
    
    # List Google Drive mods
    gdrive_list_frame = tk.Frame(gdrive_frame, bg=AppTheme.GDRIVE_BG)
    gdrive_list_frame.pack(fill=tk.X, pady=(0, 10))
    
    gdrive_text = tk.Text(gdrive_list_frame, height=min(5, len(failed_mods)), width=60,
                         font=("Courier", 9), wrap=tk.WORD, bg=AppTheme.GDRIVE_BG, fg=AppTheme.TEXT_PRIMARY, 
                         relief=tk.FLAT, highlightthickness=0, borderwidth=0)
    for mod in failed_mods:
        gdrive_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
    gdrive_text.config(state=tk.DISABLED)
    gdrive_text.pack(padx=5, pady=5)
    
    # Warning message
    warning_frame = tk.Frame(gdrive_frame, bg=AppTheme.SURFACE)
    warning_frame.pack(fill=tk.X, pady=(0, 0))
    
    warning_text = tk.Label(warning_frame, 
        text=f"{LogSymbols.WARNING}  These Google Drive links might not be direct downloads and may require manual confirmation. Proceed only if the source is trusted.",
        font=("Arial", 9), bg=AppTheme.SURFACE, fg=AppTheme.TEXT_SECONDARY, wraplength=500, justify=tk.LEFT)
    warning_text.pack(anchor=tk.W)
    
    # Buttons frame
    button_frame = tk.Frame(main_frame, bg=AppTheme.SURFACE)
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
    button_container = tk.Frame(button_frame, bg=AppTheme.SURFACE)
    button_container.pack(anchor=tk.CENTER)
    
    _create_button(button_container, "Confirm Installation", on_confirm,
                  width=18, button_type="success").pack(side=tk.LEFT, padx=5)
    
    _create_button(button_container, "Cancel", on_cancel,
                  width=12, button_type="secondary").pack(side=tk.LEFT, padx=5)
    
    # Keyboard bindings
    dialog.bind("<Escape>", lambda e: on_cancel())
    
    _center_dialog(dialog, parent)
    dialog.wait_window()


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
             bg=AppTheme.SURFACE, fg=AppTheme.PRIMARY).pack(pady=(15, 20))
    
    # Form frame
    form_frame = tk.Frame(dialog, bg=AppTheme.SURFACE)
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
            bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY,
                anchor=tk.W).grid(row=i, column=0, sticky="w", pady=5)
        
        entry = tk.Entry(form_frame, font=("Arial", 10),
                   bg=AppTheme.SURFACE_DARK, fg=AppTheme.TEXT_PRIMARY,
                   insertbackground=AppTheme.PRIMARY)
        entry.insert(0, value)
        entry.grid(row=i, column=1, sticky="ew", pady=5, padx=(10, 0))
        entries[key] = entry
    
    form_frame.columnconfigure(1, weight=1)
    
    # Description field (multi-line)
    tk.Label(form_frame, text="Description:", font=("Arial", 10),
             bg=AppTheme.SURFACE, fg=AppTheme.TEXT_PRIMARY,
             anchor=tk.W).grid(row=len(fields), column=0, sticky="nw", pady=5)
    
    desc_text = tk.Text(form_frame, font=("Arial", 10), height=6,
                      bg=AppTheme.SURFACE_DARK, fg=AppTheme.TEXT_PRIMARY,
                      insertbackground=AppTheme.PRIMARY, wrap=tk.WORD)
    desc_text.insert("1.0", app.modlist_data.get("description", ""))
    desc_text.grid(row=len(fields), column=1, sticky="ew", pady=5, padx=(10, 0))
    entries['description'] = desc_text
    
    # Buttons
    button_frame = tk.Frame(dialog, bg=AppTheme.SURFACE)
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
