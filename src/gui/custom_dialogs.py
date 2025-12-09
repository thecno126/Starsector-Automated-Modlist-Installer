"""  
Custom styled dialog boxes for ASTRA Modlist Installer.
Provides modern, themed alternatives to standard tkinter messageboxes.
"""
import tkinter as tk


class StyledDialog:
    """Base class for custom styled dialogs."""
    
    def __init__(self, parent, title, message, dialog_type="info", buttons=None):
        """
        Create a styled dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            message: Message to display
            dialog_type: Type of dialog - "info", "success", "error", "warning", "question"
            buttons: List of (label, value) tuples for buttons
        """
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)
        
        # Main content frame
        content_frame = tk.Frame(self.dialog)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(content_frame, text=title, font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 15))
        
        # Icon and message
        message_frame = tk.Frame(content_frame)
        message_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Icon with color coding
        icons = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✗", "question": "?"}
        icon_colors = {
            "info": "#3498db",      # Blue
            "success": "#2ecc71",   # Green
            "warning": "#e67e22",   # Orange
            "error": "#e74c3c",     # Red
            "question": "#3498db"   # Blue
        }
        icon_label = tk.Label(message_frame, text=icons.get(dialog_type, "ℹ"), 
                font=("Arial", 36, "bold"), fg=icon_colors.get(dialog_type, "#3498db"))
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Message
        tk.Label(message_frame, text=message, font=("Arial", 10),
                wraplength=350, justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = tk.Frame(content_frame)
        button_frame.pack(fill=tk.X)
        
        # Default buttons
        if buttons is None:
            buttons = [("Yes", True), ("No", False)] if dialog_type == "question" else [("OK", True)]
        
        # Button color scheme based on dialog type
        primary_color = {
            "success": "#2ecc71",
            "error": "#e74c3c",
            "warning": "#e67e22",
            "info": "#3498db",
            "question": "#3498db"
        }.get(dialog_type, "#3498db")
        
        # Create buttons (reversed for right-to-left packing)
        for i, (label, value) in enumerate(reversed(buttons)):
            # First button gets primary color, others get gray
            bg_color = primary_color if i == len(buttons) - 1 else "#95a5a6"
            tk.Button(button_frame, text=label, command=lambda v=value: self._on_button_click(v),
                     font=("Arial", 10, "bold"), cursor="hand2", padx=20, 
                     pady=8, bg=bg_color, fg="white" if bg_color != "#95a5a6" else "black",
                     relief=tk.RAISED, bd=1).pack(side=tk.RIGHT, padx=(0, 5) if i > 0 else 0)
        
        # Keyboard bindings
        self.dialog.bind("<Return>", lambda e: self._on_button_click(buttons[0][1]))
        self.dialog.bind("<Escape>", lambda e: self._on_button_click(False if dialog_type == "question" else True))
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
    def _on_button_click(self, value):
        """Handle button click."""
        self.result = value
        self.dialog.destroy()
        
    def show(self):
        """Show dialog and wait for result."""
        self.dialog.wait_window()
        return self.result


# Helper functions
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
    """
    Show URL validation report dialog with domain breakdown.
    
    Args:
        parent: Parent window
        github_mods: List of GitHub mods
        gdrive_mods: List of Google Drive mods
        other_domains: Dict of {domain: [mod, ...]}
        failed_list: List of {'mod': mod, 'status': code, 'error': str}
        
    Returns:
        str: 'continue' to proceed, 'cancel' to abort
    """
    result = {'action': 'cancel'}
    
    dialog = tk.Toplevel(parent)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)
    
    # Main frame
    main_frame = tk.Frame(dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Title
    tk.Label(main_frame, text="Download Sources Analysis", 
             font=("Arial", 14, "bold")).pack(pady=(0, 15))
    
    # Summary frame
    summary_frame = tk.Frame(main_frame)
    summary_frame.pack(fill=tk.X, pady=(0, 15))
    
    # GitHub mods
    if len(github_mods) > 0:
        github_frame = tk.Frame(summary_frame)
        github_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(github_frame, text=f"✓ {len(github_mods)} mod(s) from GitHub", 
                font=("Arial", 11, "bold"), fg="#2d862d").pack(anchor=tk.W)
        
        # List GitHub mods
        github_list_frame = tk.Frame(github_frame, relief=tk.SUNKEN, bd=1, bg="#e6ffe6")
        github_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        github_text = tk.Text(github_list_frame, height=min(4, len(github_mods)), width=55,
                             font=("Courier", 9), wrap=tk.WORD, bg="#e6ffe6", relief=tk.FLAT)
        for mod in github_mods:
            github_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
        github_text.config(state=tk.DISABLED)
        github_text.pack(padx=5, pady=5)
    
    # Google Drive mods with info
    if len(gdrive_mods) > 0:
        gdrive_frame = tk.Frame(summary_frame)
        gdrive_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(gdrive_frame, text=f"✓ {len(gdrive_mods)} mod(s) from Google Drive", 
                font=("Arial", 11, "bold"), fg="#3b82f6").pack(anchor=tk.W)
        
        # Info about large files
        info_text = tk.Label(gdrive_frame, 
            text="Large files bypass Google's virus scan and may need a second confirmation to download.",
            font=("Arial", 9, "italic"), fg="#666", wraplength=450, justify=tk.LEFT)
        info_text.pack(anchor=tk.W, padx=(20, 0), pady=(2, 0))
        
        # List Google Drive mods
        gdrive_list_frame = tk.Frame(gdrive_frame, relief=tk.SUNKEN, bd=1, bg="#e6f2ff")
        gdrive_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        gdrive_text = tk.Text(gdrive_list_frame, height=min(4, len(gdrive_mods)), width=55,
                             font=("Courier", 9), wrap=tk.WORD, bg="#e6f2ff", relief=tk.FLAT)
        for mod in gdrive_mods:
            gdrive_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')}\n")
        gdrive_text.config(state=tk.DISABLED)
        gdrive_text.pack(padx=5, pady=5)
    
    # Other domains
    if other_domains:
        other_frame = tk.Frame(summary_frame)
        other_frame.pack(fill=tk.X, pady=(0, 8))
        
        total_other = sum(len(mods) for mods in other_domains.values())
        tk.Label(other_frame, text=f"⚠ {total_other} mod(s) from other sources", 
                font=("Arial", 11, "bold"), fg="#d97706").pack(anchor=tk.W)
        
        # List each domain with its mods
        other_list_frame = tk.Frame(other_frame, relief=tk.SUNKEN, bd=1, bg="#fff9e6")
        other_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        other_text = tk.Text(other_list_frame, height=min(5, total_other), width=55,
                            font=("Courier", 9), wrap=tk.WORD, bg="#fff9e6", relief=tk.FLAT)
        
        for domain, mods in sorted(other_domains.items()):
            for mod in mods:
                other_text.insert(tk.END, f"  • {mod.get('name', 'Unknown')} ({domain})\n")
        
        other_text.config(state=tk.DISABLED)
        other_text.pack(padx=5, pady=5)
    
    # Failed mods
    if failed_list:
        failed_frame = tk.Frame(summary_frame)
        failed_frame.pack(fill=tk.X, pady=(0, 0))
        
        tk.Label(failed_frame, text=f"✗ {len(failed_list)} mod(s) inaccessible", 
                font=("Arial", 11, "bold"), fg="#dc2626").pack(anchor=tk.W, pady=(0, 2))
        
        tk.Label(failed_frame, 
            text="These mods cannot be downloaded. Check URLs or contact mod authors.",
            font=("Arial", 9, "italic"), fg="#666", wraplength=450, justify=tk.LEFT).pack(anchor=tk.W, padx=(20, 0), pady=(2, 0))
        
        # Scrollable list of failed mods
        failed_list_frame = tk.Frame(failed_frame, relief=tk.SUNKEN, bd=1, bg="#ffe6e6")
        failed_list_frame.pack(fill=tk.X, padx=(20, 0), pady=(4, 0))
        
        failed_text = tk.Text(failed_list_frame, height=min(5, len(failed_list)), width=55, 
                             font=("Courier", 9), wrap=tk.WORD, bg="#ffe6e6", relief=tk.FLAT)
        
        for fail in failed_list:
            mod_name = fail['mod'].get('name', 'Unknown')
            error = fail['error']
            failed_text.insert(tk.END, f"  • {mod_name}: {error}\n")
        
        failed_text.config(state=tk.DISABLED)
        failed_text.pack(padx=5, pady=5)
    
    # Buttons frame
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(15, 0))
    
    def on_continue():
        result['action'] = 'continue'
        dialog.destroy()
    
    def on_cancel():
        result['action'] = 'cancel'
        dialog.destroy()
    
    # Center the buttons
    button_container = tk.Frame(button_frame)
    button_container.pack(anchor=tk.CENTER)
    
    if len(github_mods) > 0 or len(gdrive_mods) > 0 or other_domains:
        tk.Button(button_container, text="Continue", command=on_continue,
                 font=("Arial", 10, "bold"), cursor="hand2", padx=20, pady=8,
                 bg="#2ecc71", fg="white", relief=tk.RAISED, bd=1).pack(side=tk.LEFT, padx=(0, 5))
    
    tk.Button(button_container, text="Cancel", command=on_cancel,
             font=("Arial", 10), cursor="hand2", padx=20, pady=8,
             bg="#95a5a6", fg="black", relief=tk.RAISED, bd=1).pack(side=tk.LEFT)
    
    # Keyboard bindings
    dialog.bind("<Escape>", lambda e: on_cancel())
    dialog.bind("<Return>", lambda e: on_continue() if github_count > 0 or len(gdrive_mods) > 0 or other_domains else None)
    
    # Center on parent
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    
    dialog.wait_window()
    return result['action']
