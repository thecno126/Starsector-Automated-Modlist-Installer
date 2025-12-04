# Tests

Unit test suite for ASTRA Modlist Installer.

## Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# With verbose output
pytest -v

# Specific tests
pytest tests/test_config_manager.py
pytest tests/test_installer.py
```

## Coverage

- `test_config_manager.py`: Tests for ConfigManager (load/save/reset for modlist, categories, preferences)
- `test_installer.py`: Tests for ModInstaller (download, ZIP/7z extraction, zip-slip protection, already-installed detection)

## Structure

```
tests/
├── README.md                  # This file
├── test_config_manager.py     # ConfigManager tests
└── test_installer.py          # ModInstaller tests
```
