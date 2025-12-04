# Tests

Comprehensive test suite for ASTRA Modlist Installer (18 tests total).

## Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# With verbose output
pytest -v

# Run specific test
pytest tests/test_all.py::test_extract_zip_success -v
```

## Test Coverage

**Unit Tests (10 tests):**
- ConfigManager: load/save/reset for modlist, categories, preferences (4 tests)
- ModInstaller: download, ZIP/7z extraction, zip-slip protection, already-installed detection (6 tests)

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
└── test_all.py    # All tests in one file
```
