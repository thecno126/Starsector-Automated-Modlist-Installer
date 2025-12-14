# Starsector Automated Modlist Installer (SAMI)

![Tests](https://github.com/thecno126/Starsector-Automated-Modlist-Installer/workflows/Tests/badge.svg)
![Build](https://github.com/thecno126/Starsector-Automated-Modlist-Installer/workflows/Build%20and%20Release/badge.svg)

A professional tool to manage and install Starsector modlists with parallel downloads, intelligent caching, and an intuitive graphical interface.

## ✨ Key Features

### Smart Installation
- 🎯 **Intelligent Updates** - Automatically installs only missing or outdated mods
- 🔍 **Auto-detection** - Finds Starsector installation automatically on startup
- ⚡ **Parallel Downloads** - 3 concurrent workers for faster installation
- ✅ **Status Indicators** - Visual markers (✓ installed, ○ not installed, ↑ update available)
- 💾 **Automatic Backups** - Creates backup of enabled_mods.json before installation (keeps last 5)
- 🔄 **Restore Backups** - One-click restore to previous mod configurations

### Pre-Installation Checks
- 💿 **Disk Space** - Verifies sufficient free space before downloading
- 🌐 **Internet Connection** - Quick connectivity test
- 📝 **Write Permissions** - Ensures mod folder is writable
- 🔗 **Dependency Detection** - Warns about missing mod dependencies
- 🔒 **Version Compatibility** - Checks target Starsector version

### User Interface
- 🎨 **TriOS Theme** - Modern dark UI matching TriOS mod manager with colored logs
- 🖱️ **Drag & Drop** - Reorder mods by dragging them between categories
- ⬆️⬇️ **Arrow Keys** - Quick reordering within and across categories
- 📊 **Category Management** - Organize mods with custom categories
- 🔍 **Search Filter** - Quickly find mods by name
- 📋 **CSV Import/Export** - Share modlists easily

### Advanced Features
- 🌐 **Google Drive Support** - Automatic HTML detection and confirmation dialog for large files
- 🔒 **Security** - Zip-slip protection and archive integrity validation
- 🔁 **Retry Logic** - Automatic retry with exponential backoff on network failures
- 🎯 **Enable All Mods** - One-click activation of all installed mods
- ⏸️ **Pause/Resume** - Control installation flow
- 🪵 **Colored Logs** - Easy-to-read installation progress with color-coded messages

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
- **Import CSV** - Bulk import from CSV files
- **Categories** - Create and manage custom categories
- **Reorder** - Use ↑↓ buttons or drag & drop to rearrange mods
- **Enable All Mods** - Activate all installed mods in one click
- **Restore Backup** - Rollback to a previous mod configuration
- **Refresh** - Update mod metadata from installed mods

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

**Modlist Installer** - Professional mod management for Starsector

**Core Features:**
- 🔍 **Auto-detect** Starsector installation path (Windows/macOS/Linux)
- 🖥️ **GUI management** - Add, remove, reorder, and categorize mods
- 📥 **Import/Export** - Share modlists via CSV format
- 🌐 **Smart downloads** - Handles ZIP, 7z, and Google Drive links
- 📊 **Progress tracking** - Real-time installation progress with detailed logs
- 🎨 **TriOS Theme** - Consistent dark theme with cyan accents matching TriOS mod manager
- 🏷️ **Category management** - Create, rename, delete, and reorder categories
- 💾 **Auto-save** - Configuration saved automatically on exit
- 🔄 **Retry logic** - Automatic retry with exponential backoff on network failures

**Advanced Features:**
- **TriOS Theme Integration** - Custom Canvas-based buttons for proper theming on macOS (bypasses Aqua limitations)
- **Non-blocking UI** - Async URL validation with `root.after()` prevents freezing during validation
- **URL Validation Cache** - 1-hour cache reduces redundant network checks
- **Archive Validation** - Integrity checks for ZIP and 7z files
- **Version Comparison** - Smart parsing of version strings (supports "1.2.3", "2.0a", etc.)
- **Google Drive Fix** - Detects and fixes HTML responses from Google Drive
- **Zip-slip Protection** - Prevents malicious archives from escaping extraction directory
- **Atomic Saves** - Temporary file writes prevent corruption on crash
- **Skip Installed** - Automatically detects and skips already-installed mods

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
## 📦 Dependencies

Install required libraries:
```bash
pip install -r requirements.txt
```

**Required libraries:**
- `requests>=2.31.0` - HTTP downloads, URL validation, and retry logic
- `py7zr>=0.20.0` - 7zip archive support (optional, falls back to ZIP-only if unavailable)

**Development dependencies:**
- `pytest>=7.4.0` - Unit testing framework (36 tests)
- `pytest-mock>=3.11.1` - Mocking for tests

## 📦 Dependencies

Install required libraries:
```bash
pip install -r requirements.txt
```

## 🔄 Workflow

1. **Add mods:** Use the GUI to build your modlist
   - Add mods individually via the "Add Mod" button
   - Or import from a CSV file ("Import CSV")
   - Organize by categories and reorder with arrow buttons or drag-and-drop
2. **Install mods:** Click "Install Modlist" to download and install everything
   - Automatic Starsector path detection
   - ZIP and 7z support with integrity validation
   - Duplicate and already-installed mod detection
3. **Manage compatibility:** Use **TriOS** to manage mod versions and compatibility
   - Starsector Automated Modlist Installer downloads and activates mods automatically
   - Mods with incorrect game versions are installed but may need adjustment
   - Use TriOS mod manager to handle version conflicts and enable/disable mods
## 📝 Notes

- **Smart duplicate prevention** - Mods are checked by name and URL
- **Automatic format detection** - ZIP/7z detected from URL or Content-Type
- **Intelligent installation** - Mods with single top-level folders installed as-is
- **Google Drive handling** - Detects HTML responses and fixes URLs automatically
- **Auto-save** - Configuration saved on exit to prevent data loss
- **Silent saves** - No log spam from automatic saves (only Ctrl+S logs)
- **Error recovery** - Retry logic with exponential backoff handles transient failures
- **Skip duplicates** - Already-installed mods detected and skipped automatically
- **TriOS integration** - Use TriOS mod manager for version compatibility and conflict resolution

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

**Test coverage:**
- Configuration management (save/load/reset)
- Archive extraction (ZIP/7z)
- Version comparison
- Google Drive URL fixing
- Download scenarios (parallel, timeout, errors)
- URL validation and caching
- Mod installation workflows

All 36 tests pass ✅

## 📄 License

This project is open source. See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## 📧 Contact

For questions or support, please open an issue on GitHub.
- **Modular architecture** - Separation of concerns (core, GUI, utils)
- **Type hints** - Better IDE support and code clarity
- **Comprehensive tests** - 36 unit tests covering core functionality
- **Error handling** - Specific exception handling with detailed logging
- **Code elegance** - Recent refactoring eliminated 150+ redundant lines

### Performance Optimizations
- **Parallel downloads** - Up to 3 concurrent mod downloads
- **URL validation cache** - 1-hour cache for reachable URLs
- **Lazy imports** - Optional dependencies loaded only when needed
- **Atomic operations** - Efficient file I/O with temporary file strategy

### Security & Reliability
- **Zip-slip protection** - Path traversal prevention in archives
- **Archive validation** - Integrity checks before extraction
- **Atomic saves** - Prevent configuration corruption
- **Retry with backoff** - Network failure resilience (exponential backoff: 0s → 2s → 4s)
- **Version comparison** - Smart parsing handles various version formatse
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
