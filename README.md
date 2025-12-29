# Starsector Automated Modlist Installer

**Important Note**: The application, its user interface, and all documentation (README, code comments, error messages, etc.) must be **in English only**.

GUI tool for managing and installing Starsector modlists, featuring intelligent link detection (GitHub, Mediafire, Google Drive), metadata extraction without full decompression, and a polished interface.

## Overview

**Smart Link Management:**
- Automatic categorization: GitHub, **Mediafire** (displayed with priority), Google Drive, Others
- **Google Drive**: automatic URL correction (`drive.usercontent.google.com`) and bypass of "virus scan" warning for large files
- **Robust 7z detection**: via `Content-Disposition` header (filename), independent of `Content-Type`

**Smart Extraction:**
- Reading `mod_info.json` **without full extraction** from archives (ZIP/7z)
- Saves time and disk space

**Modlist Management:**
- Modlist/preset export via UI (automatic backups have been removed)
- "Modlist-only" activation: the "Enable All Mods" button activates **only** the installed mods present in the current modlist
- LunaLib patch: writes to `saves/common/LunaSettings/`
 Fast, reliable modlist downloader and manager for Starsector.
**User Interface:**
- **Refresh** button moved to the bottom, left of the **Wipe** button
- Colored borders: **blue** (Refresh), **red** (Wipe)
 Starsector Automated Modlist Installer helps players quickly install curated modlists, validate download links, extract essential metadata straight from archives, and enable the right mods automatically. It focuses on safety, clarity, and minimal friction so you can spend more time playing.
## Prerequisites

python3 -m venv .venv
source .venv/bin/activate  # or '. .venv/bin/activate'
## Launch

```bash
source .venv/bin/activate  # Activate virtual environment
python src/modlist_installer.py
```

Or in a single command:
```bash
.venv/bin/python src/modlist_installer.py
```

## Features

### URL Validation and Categorization
- Automatic detection: **GitHub**, **Mediafire**, **Google Drive**, Others
- Mediafire displayed **before** Google Drive in the interface

### Google Drive
- Confirmation dialog for large files
- 7z detection via `Content-Disposition: filename=...` (robust even if `Content-Type` is incorrect)

- **Modlist-only activation**: "Enable All Mods" activates only the listed and installed mods

### LunaLib
- Patch configurations to `saves/common/LunaSettings/`
- Global application to the game profile

- **Styled buttons**: Refresh (blue border) and Wipe (red border) side by side at the bottom

- **Configuration files**: [config](config)
- **Presets**: [config/presets](config/presets)

### Google Drive
- **Solution**: A dialog appears; the URL is automatically corrected for direct download


### Starsector Path
- **Solution**: Manually select the path via the interface
## FAQ
**Q: Why can I activate 20 mods when only 19 are listed?**  

A: Automatic backups have been removed. Use the **Export** function to save your modlist.

**Q: How do I export my modlist?**  
## Tests

```bash
source .venv/bin/activate
pytest tests/test_suite.py -v
```

Or direct execution:
```bash
.venv/bin/python tests/test_suite.py
```

**Coverage**: import/export presets, Google Drive URL correction, 7z detection, `mod_info.json` extraction, modlist-only activation.

## License and Contributions

Open-source project — contributions welcome.
