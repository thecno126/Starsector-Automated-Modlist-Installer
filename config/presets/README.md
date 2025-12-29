# Presets Directory

This directory contains preset configurations for modlists. Each preset is stored in its own subdirectory.

## Structure

```
presets/
├── <preset-name-1>/
│   ├── modlist_config.json  (required)
│   └── lunalib_config.json  (optional)
├── <preset-name-2>/
│   ├── modlist_config.json  (required)
│   └── lunalib_config.json  (optional)
└── ...
```

## How to Use Presets

### Import a Preset (📄 Button)

Click the **📄 FILE** button in the modlist section to import a preset:

1. Select one or both JSON files:
   - `modlist_config.json` (contains your mod list)
  - `lunalib_config.json` (optional LunaLib settings)
2. Enter a name for the preset
3. The preset will be saved in `config/presets/<name>/`

The imported preset will then be available in the presets list.

### Export Current Modlist as Preset (💾 Button)

Click the **💾 SAVE** button to export your current modlist as a preset:

1. Click the save/disk icon button
2. Enter a name for the preset
3. Your current modlist will be saved in `config/presets/<name>/modlist_config.json`

This allows you to save your current modlist configuration for later use or sharing.

## Files

### modlist_config.json (Required)

Contains the complete modlist configuration including metadata and mod list.

**Required fields:**
- `modlist_name` (string): Name of the modlist
- `mods` (array): List of mod objects

**Optional fields:**
- `version` (string): Modlist version
- `starsector_version` (string): Compatible Starsector version
- `description` (string): Description of the modlist
- `author` (string): Author name

**Example:**
```json
{
  "modlist_name": "My Preset",
  "version": "1.0",
  "starsector_version": "0.97a-RC11",
  "description": "Custom modlist",
  "author": "Username",
  "mods": [
    {
      "mod_id": "lazylib",
      "name": "LazyLib",
      "download_url": "https://example.com/lazylib.zip",
      "mod_version": "2.8c",
      "game_version": "0.97a",
      "category": "Required"
    }
  ]
}
```

### lunalib_config.json (Optional)

Contains LunaLib-specific configuration that will be patched into the Starsector installation.

**Example:**
```json
{
  "enabled": true,
  "settings": {
    "enableDebugLogging": false,
    "maxCacheSize": 100
  }
}
```

### LunaLib Patch Location

When a preset includes `lunalib_config.json`, the application automatically patches the Starsector LunaLib configuration.

**Target path:**
- `<starsector_install>/saves/common/LunaSettings/`

**When patching occurs:**
- During preset import if `lunalib_config.json` is present
- When explicitly applying LunaLib settings via the UI

**Behavior:**
- Existing LunaLib settings are **merged** with preset settings (preset values take precedence)
- Ensures LunaLib picks up the settings globally for the game profile
- A success message confirms the patch location: `LunaLib config patched to saves/common/LunaSettings/`

**Note:** Preset export is the recommended way to save your configuration. Automatic backup functionality has been removed in favor of explicit export control.

## Usage

### Creating a Preset

1. Create a new directory under `presets/` with your preset name (e.g., `My_Modlist`)
2. Add a `modlist_config.json` file with your modlist configuration
3. Optionally add a `lunalib_config.json` file

### Loading a Preset

Use the preset management functions in the application to:
- List available presets
- Load a preset
- Apply a preset to your current configuration
- Patch LunaLib settings

### Programmatic Access

```python
from core.config_manager import ConfigManager

cm = ConfigManager()

# List all presets
presets = cm.list_presets()

# Create a new preset
success, error = cm.create_preset("My_Preset", modlist_data, lunalib_data)

# Load a preset
modlist, lunalib, error = cm.load_preset("My_Preset")

# Validate preset data
is_valid, error = cm.validate_preset(modlist_data)

# Delete a preset
success, error = cm.delete_preset("My_Preset")
```

## Notes

- Preset names must be valid directory names (no special characters: `< > : " / \ | ? *`)
- The `modlist_config.json` file is required; presets without it will be ignored
- LunaLib config is optional and will only be used if present
- All JSON files must be valid UTF-8 encoded JSON
 - Preset export is supported; backup functionality has been removed in favor of explicit export
