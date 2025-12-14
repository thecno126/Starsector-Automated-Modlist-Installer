"""
Starsector Automated Modlist Installer - Entry point
Main executable script for the modlist installer application.
"""

import tkinter as tk

# Import the main window class
from gui import ModlistInstaller


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = ModlistInstaller(root)
    root.mainloop()


if __name__ == "__main__":
    main()
