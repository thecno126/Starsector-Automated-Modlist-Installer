# Starsector Automated Modlist Installer (SAMI)

![Tests](https://github.com/thecno126/Starsector-Automated-Modlist-Installer/workflows/Tests/badge.svg)
![Build](https://github.com/thecno126/Starsector-Automated-Modlist-Installer/workflows/Build%20and%20Release/badge.svg)

An amateur tool to manage and install Starsector modlists with parallel downloads, intelligent caching, and an intuitive graphical interface.

## ✨ Key Features

### Smart Installation
- 🎯 **Intelligent Updates** - Automatically installs only missing or outdated mods
- 🔍 **Auto-detection** - Finds Starsector installation automatically on startup
- ⚡ **Parallel Downloads** - 3 concurrent workers for faster installation
- ✅ **Status Indicators** - Visual markers (✓ installed, ○ not installed, ↑ update available)
- 💾 **Automatic Backups** - Creates backup of enabled_mods.json before installation (keeps last 5)
- 🔄 **Restore Backups** - One-click restore to previous mod configurations

### Pre-Installation Checks
- 💿 **Disk Space** - Verifies sufficient free space before downloading (5GB minimum)
- 🌐 **Internet Connection** - Quick connectivity test
- 📝 **Write Permissions** - Ensures mod folder is writable
- 🔗 **Dependency Detection** - Warns about missing mod dependencies
- 🔒 **Version Compatibility** - Checks target Starsector version

### User Interface
- 🎨 **TriOS Theme** - Modern dark UI with cyan accents matching TriOS mod manager
- 🖱️ **Drag & Drop** - Reorder mods by dragging them between categories
- ⬆️⬇️ **Arrow Keys** - Quick reordering within and across categories
- 📊 **Category Management** - Create, rename, delete, and reorder custom categories
- 🔍 **Search Filter** - Quickly find mods by name
- 📋 **CSV Import/Export** - Share modlists with metadata (author field supported)
- 📝 **Modlist Metadata** - Edit name, author, version, Starsector version, and description

### Advanced Features
- 🌐 **Google Drive Support** - Automatic HTML detection and confirmation dialog for large files
- 🔒 **Security** - Zip-slip protection and archive integrity validation
- 🔁 **Retry Logic** - Automatic retry with exponential backoff on network failures
- 🎯 **Enable All Mods** - One-click activation of all installed mods
- ⏸️ **Pause/Resume** - Control installation flow
- 🪵 **Colored Logs** - Easy-to-read installation progress with color-coded messages
- 🧪 **Headless Testing** - MockTk fixtures for GUI-free test execution

## 🚀 Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Usage

```bash
python src/modlist_installer.py
```

**First Launch:**
1. The app will auto-detect your Starsector installation (or prompt you to select it)
2. Configure your modlist: add mods, organize categories, reorder as needed
3. Click **"Install Modlist"** - only missing/outdated mods will be downloaded
4. All installed mods are automatically activated in Starsector

**Managing Mods:**
- **Add Mod** - Add mods individually with URL validation
- **Edit Mod** - Modify mod name, URL, or category
- **Import CSV** - Bulk import from CSV files (replace or merge mode)
- **Export CSV** - Export with metadata (name, author, version, description)
- **Categories** - Create, rename, delete, and reorder custom categories
- **Reorder** - Use ↑↓ buttons or drag & drop to rearrange mods
- **Enable All Mods** - Activate all installed mods in one click
- **Restore Backup** - Rollback to a previous mod configuration
- **Refresh Metadata** - Update mod versions from installed mods
- **Edit Metadata** - Update modlist name, author, version, and description

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
Starsector-Automated-Modlist-Installer/
├── .github/
│   └── workflows/            # Automated CI/CD
│       ├── build-release.yml # Multi-platform builds
│       └── tests.yml         # Automated tests
├── src/                      # Source code
│   ├── modlist_installer.py  # Entry point
│   ├── core/                 # Business logic
│   │   ├── __init__.py       # Core exports
│   │   ├── constants.py      # Constants and paths
│   │   ├── config_manager.py # Config management (atomic saves)
│   │   ├── archive_extractor.py # ZIP/7z extraction
│   │   └── installer.py      # Download and installation logic
│   ├── gui/                  # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py    # Main application window
│   │   ├── dialogs.py        # All dialog functions
│   │   ├── ui_builder.py     # UI component builders
│   │   └── installation_controller.py # Installation flow control
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── theme.py          # TriOS theme colors
│       ├── backup_manager.py # Backup creation/restore
│       ├── mod_utils.py      # Mod detection and metadata
│       ├── network_utils.py  # URL validation and downloads
│       ├── validators.py     # Path and URL validators
│       ├── error_messages.py # User-friendly error messages
│       ├── installation_checks.py # Pre-installation checks
│       ├── listbox_helpers.py # Listbox utilities
│       └── category_navigator.py # Category navigation
├── tests/                    # Unit tests
│   ├── test_suite.py         # 80 comprehensive tests
│   └── README.md             # Test documentation
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

## 💡 Usage Examples

**Managing Mods:**
- Use the GUI to add mods individually with automatic URL validation
- Import mods in bulk from CSV files (replace or merge mode)
- Edit mod properties (name, URL, category)
- Organize mods by categories (create, rename, delete, reorder)
- Reorder mods within categories using arrows or drag & drop
- Export your modlist to CSV with full metadata

**CSV Import Format** (via GUI):
```csv
mod_id,name,download_url,mod_version,game_version,category
lazylib,LazyLib,https://example.com/lazylib.zip,3.0.0,0.98a-RC5,Libs
nexerelin,Nexerelin,https://example.com/nexerelin.zip,0.12.1b,0.98a-RC8,Megamods
```
- `mod_version`, `game_version`, and `category` are optional
- Also supports `url` or `version` as alternate column names

**Modlist metadata** (optional CSV header):
```csv
modlist_name,author,starsector_version,modlist_description,modlist_version
My Modlist,YourName,0.98a-RC8,My custom modlist,1.0
mod_id,name,download_url,mod_version,game_version,category
lazylib,LazyLib,https://example.com/lazylib.zip,3.0.0,0.98a-RC5,Libs
```

The first two lines can contain modlist metadata (detected if first line lacks a `download_url` field).

## ⚙️ Configuration

Mods are stored in `modlist_config.json`:

```json
{
  "modlist_name": "ASTRA",
  "version": "1.0",
  "starsector_version": "0.98a-RC8",
  "author": "thecno126",
  "description": "Starsector Modlist",
  "mods": [
    {
      "mod_id": "lazylib",
      "name": "LazyLib",
      "download_url": "https://github.com/LazyWizard/lazylib/releases/download/3.0/LazyLib.3.0.zip",
      "mod_version": "3.0.0",
      "game_version": "0.98a-RC5",
      "category": "Libs"
    }
  ]
}
```
## 📦 Dependencies

Install required libraries:
```bash
pip install -r requirements.txt
```

**Required libraries:**
- `requests>=2.31.0` - HTTP downloads, URL validation, and retry logic
- `py7zr>=0.20.0` - 7zip archive support (optional, falls back to ZIP-only if unavailable)

**Development dependencies:**
- `pytest>=7.4.0` - Unit testing framework (80 tests)
- `pytest-mock>=3.11.1` - Mocking for tests

## 🔄 Workflow

1. **Configure your modlist** - Use the GUI to build your modlist
   - Add mods individually via "Add Mod" button with automatic URL validation
   - Or bulk import from CSV file ("Import CSV") with replace or merge mode
   - Edit modlist metadata (name, author, version, description)
   - Organize mods by categories and reorder with arrow buttons or drag-and-drop
2. **Install mods** - Click "Install Modlist" to download and install everything
   - Automatic Starsector path detection on first launch
   - Pre-installation checks (disk space, permissions, dependencies)
   - Parallel downloads (3 workers) with progress tracking
   - ZIP and 7z support with integrity validation
   - Duplicate and already-installed mod detection
   - Automatic backup of enabled_mods.json
3. **Manage your installation** - Post-installation tools
   - **Enable All Mods** - Activate all installed mods in one click
   - **Refresh Metadata** - Update mod versions from installed mod_info.json files
   - **Restore Backup** - Rollback to previous configuration
   - Use **TriOS** mod manager for advanced version compatibility and conflict resolution
## 📝 Notes

- **Smart duplicate prevention** - Mods checked by `mod_id`, name, and URL
- **Automatic format detection** - ZIP/7z detected from URL or Content-Type header
- **Intelligent installation** - Mods with single top-level folders installed as-is
- **Google Drive handling** - Detects HTML responses, shows confirmation dialog for large files
- **Auto-save** - Configuration saved on exit and after changes (Ctrl+S for manual save)
- **Error recovery** - Retry logic with exponential backoff (0s → 2s → 4s) handles transient failures
- **Skip duplicates** - Already-installed mods detected by mod_info.json and skipped automatically
- **Category-based organization** - Mods grouped by custom categories, maintained on save
- **No mods_by_category** - Removed redundant structure, categories computed dynamically
- **macOS file dialog fix** - Parent parameter added to all filedialog calls for compatibility

## 🧪 Testing

Run the test suite:
```bash
pytest tests/test_suite.py -v
```

**Test coverage:**
- Configuration management (save/load/reset)
- Archive extraction (ZIP/7z with py7zr)
- Version comparison and mod detection
- Google Drive URL fixing
- Download scenarios (parallel, timeout, errors, retry logic)
- URL validation and caching (1-hour cache)
- Complete workflows (CSV import, manual mod addition)
- GUI functions (add, edit, remove, reorder, drag & drop)
- Backup management (create, restore, cleanup)
- Metadata refresh and mod enabling
- Error recovery and UI state management

**80 tests total** - 78 passed, 2 skipped (py7zr-dependent) ✅

## 📄 License

This project is open source. See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## 📧 Contact

For questions or support, please open an issue on GitHub: https://github.com/thecno126/Starsector-Automated-Modlist-Installer/issues

---

### 🔧 Recent Improvements

- **Author field synchronization** - Author field now fully synchronized across metadata dialog, JSON config, CSV export/import, and header display
- **Headless testing** - MockTk/MockToplevel fixtures prevent GUI windows during test execution
- **NameError fixes** - Fixed dialog callback references for proper error handling
- **Configuration validation** - Built-in validation in ConfigManager and dialogs for data integrity
- **Redundancy removal** - Eliminated `mods_by_category` structure, simplified codebase by 150+ lines
- **macOS compatibility** - Fixed file dialogs on macOS by adding parent parameter and changing wildcard to "*.*"
- **Test suite expansion** - Grew from 36 to 80 comprehensive tests covering all major workflows
