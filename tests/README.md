# Tests

Comprehensive test suite for Starsector Automated Modlist Installer (30 tests total).

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

**Configuration Management (4 tests):**
- ConfigManager: load/save/reset for modlist, categories, preferences
- Default config generation when files missing
- Roundtrip save/load validation

**Core Installation (6 tests):**
- ZIP and 7z extraction
- Zip-slip security protection
- Already-installed mod detection
- Network error handling
- File overlap detection

**Google Drive Integration (4 tests):**
- URL fixing for /file/d/ID/view format
- URL fixing for ?id=ID format  
- Non-Google Drive URL preservation
- Invalid URL handling

**Download Scenarios (6 tests):**
- Parallel downloads (3 concurrent workers)
- Timeout and retry logic
- 404 error handling
- 7z format detection
- Google Drive HTML response detection
- Non-Google Drive HTML handling

**URL Validation (5 tests):**
- Mixed URL sources (GitHub, Google Drive, other)
- Retry logic with exponential backoff
- 403 fallback to GET request
- Empty URL validation
- Domain categorization

**Concurrent Operations (2 tests):**
- ThreadPoolExecutor max_workers limit
- Executor cancellation

**Integration Workflows (3 tests):**
- CSV import → validation → installation
- Manual mod addition → reorganization → export
- Installation with pre-installed mods

## Structure

```
tests/
├── README.md      # This file
└── test_all.py    # All 30 tests consolidated
```

All tests are consolidated into a single file for easier maintenance.
