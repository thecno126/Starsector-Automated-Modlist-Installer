# ASTRA Modlist Installer

![Tests](https://github.com/thecno126/ASTRA-Modlist-Installer/workflows/Tests/badge.svg)
![Build](https://github.com/thecno126/ASTRA-Modlist-Installer/workflows/Build%20and%20Release/badge.svg)

A tool to manage and install Starsector modlists with parallel downloads and an intuitive graphical interface.

## ✨ Features

- 📦 Automatic mod installation from URLs
- ⚡ Parallel downloads (3 workers by default)
- 🔒 Zip-slip protection and archive validation
- 📊 Category management and mod reorganization
- 💾 Atomic configuration saves
- 🎨 Modern Tkinter interface with progress bar
- 📋 CSV Import/Export to share your modlists
- ✅ 10 unit tests with pytest

## 🚀 Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Usage

**Install mods:**
```bash
python src/modlist_installer.py
```

### 📦 Building Executables

**On macOS/Linux:**
```bash
cd build_scripts
chmod +x build.sh  # First time only
./build.sh
```

**On Windows:**
```cmd
cd build_scripts
build.bat
```

Executables will be created in the `dist/` folder

For more details, see [build_scripts/BUILD.md](build_scripts/BUILD.md)

### 🤖 Automated Builds with GitHub Actions

**For each release (tag `v*`)**:
1. Create a tag: `git tag v1.0.0 && git push origin v1.0.0`
2. GitHub Actions automatically compiles for:
   - 🍎 macOS (.app)
   - 🪟 Windows (.exe)
   - 🐧 Linux (binary)
3. Executables are attached to the GitHub release

**Automated tests**: Each push to `main` or `develop` runs tests.

## 📁 Project Structure

```
ASTRA-Modlist-Installer/
├── .github/
│   └── workflows/            # Automated CI/CD
│       ├── build-release.yml # Multi-platform builds
│       └── tests.yml         # Automated tests
├── src/                      # Source code
│   ├── modlist_installer.py  # Entry point
│   ├── core/                 # Business logic
│   │   ├── constants.py      # Constants and paths
│   │   ├── config_manager.py # Config management (atomic)
│   │   └── installer.py      # Download and extraction
│   ├── gui/                  # User interface
│   │   ├── main_window.py    # Main window
│   │   ├── dialogs.py        # Dialogs
│   │   └── ui_builder.py     # UI builder
│   └── utils/                # Utilities
│       └── theme.py          # System theme detection
├── tests/                    # Unit tests
│   ├── test_config_manager.py
│   └── test_installer.py
├── build_scripts/            # Build scripts
│   ├── modlist_installer.spec
│   ├── build.sh / build.bat
│   └── BUILD.md
├── config/                   # Configuration files
│   ├── modlist_config.json
│   ├── categories.json
│   └── installer_prefs.json
└── requirements.txt          # Python dependencies
```

## 📚 Documentation

- **README.md** (this file) - Quick start guide
- **build_scripts/BUILD.md** - Build and distribution guide
- **tests/README.md** - Test documentation

## ✨ Detailed Features

**Modlist Installer** - Install and manage Starsector mods

**Core Features:**
- Auto-detect Starsector installation path (Windows/macOS/Linux)
- GUI for managing mods (add, remove, reorder, categorize)
- Import/export modlists from CSV
- Install mods from URLs (ZIP and 7z archives)
- Skip already-installed mods automatically
- Progress tracking and detailed logging
- System theme detection (light/dark mode)
- Mod categories management

**Usage:**
```bash
python src/modlist_installer.py
```

**Managing Mods:**
- Use the GUI to add mods individually with URL validation
- Import mods from CSV files
- Organize mods by categories
- Reorder mods within categories
- Export your modlist to CSV

**CSV Import Format** (via GUI):
```csv
name,category,download_url,version
LazyLib,Required,https://example.com/lazylib.zip,2.8
Nexerelin,Gameplay,https://example.com/nexerelin.7z,0.11.2b
```
- `version` and `category` are optional
- Also supports `url` as column name instead of `download_url`

**Modlist metadata** (optional CSV header):
```csv
modlist_name,modlist_version,starsector_version,modlist_description
My Modlist,1.0,0.97a-RC11,My modlist description
name,category,download_url,version
LazyLib,Required,https://example.com/lazylib.zip,2.8
```

The first line can contain modlist metadata (detected if it lacks a `download_url` field).

## ⚙️ Configuration

Mods are stored in `modlist_config.json`:

```json
{
  "modlist_name": "My Custom Modlist",
  "version": "1.0",
  "starsector_version": "0.97a-RC11",
  "description": "A selection of mods",
  "mods": [
    {
      "name": "LazyLib",
      "download_url": "https://example.com/lazylib.zip",
      "version": "2.8"
    }
  ]
}
```

**Required fields per mod:**
- `name`: Mod name
- `download_url`: Direct download link (ZIP or 7z)

**Optional fields:**
- `version`: Mod version (display only)

## 📦 Dependencies

Install required libraries:
```bash
pip install -r requirements.txt
```

**Required libraries:**
- `requests>=2.31.0` - HTTP downloads and URL validation
- `py7zr>=0.20.0` - 7zip archive support (optional, works without for ZIP only)

## 🔄 Workflow

1. **Add mods:** Use the GUI to build your modlist
   - Add mods individually via the "Add Mod" button
   - Or import from a CSV file ("Import CSV")
   - Organize by categories and reorder as you like
2. **Install mods:** Click "Install Modlist" to download and install everything
   - Automatic Starsector path detection
   - ZIP and 7z support
   - Duplicate and already-installed mod detection

## 📝 Notes

- Duplicate mods (by name or URL) are automatically prevented
- Archive type (ZIP/7z) is automatically detected from URL extension or Content-Type header
- Mods with a single top-level folder are installed as-is
- Multi-file archives are extracted directly
- Already installed mods are automatically skipped
