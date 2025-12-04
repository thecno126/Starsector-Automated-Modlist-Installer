# Tests

Comprehensive test suite for ASTRA Modlist Installer (25 tests total).

## Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# With verbose output
pytest -v

# Run specific test
pytest tests/test_all.py::test_theme_detection -v
```

## Test Coverage

**Unit Tests (17 tests):**
- ConfigManager: load/save/reset for modlist, categories, preferences (4 tests)
- ModInstaller: download, ZIP/7z extraction, zip-slip protection, already-installed detection (6 tests)
- ThemeManager: system detection, color schemes, consistency, forced theme (7 tests)

**Integration & Scenario Tests (8 tests):**
- CSV import to installation workflow
- Manual mod addition and reorganization
- Installation with already-installed mods (skip detection, 100% progress)
- Network failure recovery and error handling
- Corrupted archive detection
- Category management and persistence
- Large modlist handling (150+ mods)
- Parallel download efficiency verification

## Structure

```
tests/
├── README.md      # This file
└── test_all.py    # All 25 tests in one file
```
