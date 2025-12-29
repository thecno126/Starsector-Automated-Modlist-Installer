# Tests

**Important**: All application content, UI elements, tests, and documentation must be in **English only**.

Test suite documentation for Starsector Automated Modlist Installer.

## Running Tests
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Run the main test runner
pytest tests/test_suite.py -v

# Or run directly via Python
.venv/bin/python tests/test_suite.py
```

## Test Coverage

### Import/Export Presets
- JSON structure validation (`modlist_config.json`, `lunalib_config.json`)
- Loading and saving from/to `config/presets/<name>/`
- Error detection (invalid presets, missing paths)

### Google Drive URL Correction
- Supported formats: `/file/d/<ID>/view`, `?id=<ID>`
- Automatic correction to `drive.usercontent.google.com`
- HTML response detection (virus scan warning page)
- Confirmation dialog for large files

### 7z Archive Detection
- Detection via `Content-Disposition: filename=...` (priority over `Content-Type`)
- Support for filenames with `.7z` extension
- Robust fallback if `Content-Type` is ambiguous

### `mod_info.json` Extraction
- Extraction **without full decompression** (ZIP and 7z)
- `py7zr` support for 7z archives
- Direct reading from archive with `zipfile` and `py7zr`
- Saves time and disk space

### "Modlist-only" Activation
- Update `enabled_mods.json` to activate **only** mods that are:
  - Present in the current modlist
  - **AND** installed in the `mods/` folder
- Verification of `mod_id` for exact match
- Solves the "20 mods activated for 19 listed" issue

### Validations and Error Messages
- Dialogs (confirmations, errors, success)
- Path validations (Starsector install, mod folders)
- Write permissions (config, mods, saves)

### Test JSON Files

Test files are provided under the `tests/` folder:
- `tests/test_import_modlist.json` — test modlist for import
- `tests/test_invalid_preset.json` — invalid preset (error validation)
- `tests/test_lunalib_patch.json` — test LunaLib configuration
- `tests/test_import_lunalib.json` — preset with LunaLib config

These files allow validation of complete import/export and LunaLib patch workflows.

## Structure
```
tests/
├── README.md                # This file
├── test_suite.py            # Main test runner
├── test_import_modlist.json
├── test_invalid_preset.json
├── test_lunalib_patch.json
├── test_import_lunalib.json
└── test_lunasettings.py
```
