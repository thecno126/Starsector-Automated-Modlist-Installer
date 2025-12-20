```instructions
---
applyTo: '**'
---

# Starsector Automated Modlist Installer - Instructions de développement

## Vue d'ensemble du projet

Application Python/Tkinter pour automatiser l'installation de mods Starsector depuis une modlist JSON. Supporte le téléchargement parallèle, extraction ZIP/7z, gestion des dépendances, backups automatiques et refresh de métadonnées.

## Règles critiques

**⚠️ SYMBOLES UNICODE - NE JAMAIS HARDCODER**

Tous les symboles Unicode (✓, ✗, ⚠️, ⬆, ⬇, etc.) sont **centralisés** dans `src/utils/symbols.py`. **TOUJOURS** utiliser `LogSymbols` et `UISymbols` au lieu de hardcoder les caractères.

```python
from utils.symbols import LogSymbols, UISymbols

# ✓ BON
self.log(f"{LogSymbols.SUCCESS} Installation complete")
button = _create_button(frame, UISymbols.ARROW_UP, callback)

# ✗ MAUVAIS - Ne jamais faire
self.log("✓ Installation complete")  # ❌ INTERDIT
button = _create_button(frame, "⬆", callback)  # ❌ INTERDIT
```

Voir section "Symboles centralisés" ci-dessous pour la liste complète.

## Architecture du code

### Structure des modules

```
src/
├── model_types.py          # NamedTuples partagés (DownloadResult, ModVersionCheck, BackupResult)
├── core/                   # Logique métier principale
│   ├── installer.py        # Téléchargement et installation de mods
│   ├── archive_extractor.py # Extraction ZIP/7z avec sécurité path traversal
│   ├── config_manager.py   # Gestion config JSON avec log_callback
│   └── constants.py        # Constantes et InstallationReport
├── gui/                    # Interface utilisateur
│   ├── main_window.py      # Fenêtre principale et orchestration
│   ├── dialogs.py          # Dialogs modaux (add mod, import CSV, etc.)
│   ├── installation_controller.py # Workflow installation (download, extract, finalize)
│   └── ui_builder.py       # Création composants UI (buttons, frames, etc.)
└── utils/                  # Utilitaires
    ├── symbols.py          # LogSymbols (SUCCESS, ERROR, WARNING, etc.)
    ├── backup_manager.py   # Backups avec retention policy (4 backups par défaut)
    ├── mod_utils.py        # Métadonnées, version comparison, dependencies
    ├── installation_checks.py # Pré-checks (disk space, permissions, internet)
    ├── network_utils.py    # Validation URLs, Google Drive fixes
    ├── error_messages.py   # Messages utilisateur friendly
    ├── category_navigator.py # Navigation catégories dans listbox
    ├── listbox_helpers.py  # Extraction noms de mods depuis listbox
    ├── validators.py       # StarsectorPathValidator, URLValidator
    └── theme.py            # TriOSTheme (couleurs, styles)
```

### Types partagés (model_types.py)

**TOUJOURS utiliser ces NamedTuples au lieu de tuples anonymes :**

```python
from model_types import DownloadResult, ModVersionCheck, BackupResult

# DownloadResult(temp_path: Path, is_7z: bool)
result = DownloadResult(temp_path=Path("/tmp/mod.zip"), is_7z=False)
if result.temp_path and result.temp_path.exists():
    extract(result.temp_path, result.is_7z)

# ModVersionCheck(is_current: bool, installed_version: str)
check = is_mod_up_to_date(mod, mods_dir)
if not check.is_current:
    print(f"Outdated: {check.installed_version}")

# BackupResult(path: Path, success: bool, error: str)
result = backup_manager.create_backup()
if result.success:
    print(f"Backup created: {result.path}")
```

### Symboles centralisés (utils/symbols.py)

**TOUJOURS utiliser LogSymbols au lieu de symboles hardcodés :**

```python
from utils.symbols import LogSymbols, UISymbols

# ✓ BON
self.log(f"{LogSymbols.SUCCESS} Installation complete")
self.log(f"{LogSymbols.ERROR} Failed to download", error=True)
self.log(f"{LogSymbols.WARNING} Disk space low", warning=True)
icon = LogSymbols.INSTALLED if installed else LogSymbols.NOT_INSTALLED
btn = _create_button(frame, UISymbols.ARROW_UP, callback)
status_var.set(f"{UISymbols.DOWNLOADING} Downloading...")

# ✗ MAUVAIS - Ne jamais hardcoder
self.log("✓ Installation complete")  # ❌
self.log("✗ Failed", error=True)     # ❌
icon = "✓" if installed else "○"     # ❌
btn = _create_button(frame, "⬆", callback)  # ❌
```

**Symboles disponibles :**

**LogSymbols** (pour les logs et messages) :
- `LogSymbols.SUCCESS` = "✓"
- `LogSymbols.ERROR` = "✗"
- `LogSymbols.WARNING` = "⚠️"
- `LogSymbols.INFO` = "ℹ"
- `LogSymbols.QUESTION` = "?"
- `LogSymbols.INSTALLED` = "✓"
- `LogSymbols.NOT_INSTALLED` = "○"
- `LogSymbols.UPDATED` = "↑"
- `LogSymbols.BULLET` = "•"
- `LogSymbols.TRASH` = "🗑"
- `LogSymbols.ARROW_RIGHT` = "→"

**UISymbols** (pour les boutons et UI) :
- `UISymbols.ARROW_UP` = "⬆"
- `UISymbols.ARROW_DOWN` = "⬇"
- `UISymbols.ARROW_DOWN_ALT` = "↓"
- `UISymbols.DOWNLOADING` = "⬇"
- `UISymbols.PAUSE` = "⏸"
- `UISymbols.PLAY` = "▶"
- `UISymbols.EDIT_METADATA` = "⋯"
- `UISymbols.REFRESH` = "↻"
- `UISymbols.IMPORT` = "⤓"
- `UISymbols.EXPORT` = "⤒"
- `UISymbols.SEARCH` = "🔍"
- `UISymbols.CLEAR` = "✕"
- `UISymbols.REMOVE` = "✖"
- `UISymbols.ADD` = "➕"
- `UISymbols.SETTINGS` = "⚙"
- `UISymbols.EDIT` = "✏️"
- `UISymbols.DELETE` = "␡"
- `UISymbols.SAVE` = "💾"

## Règles d'imports

### 1. JAMAIS d'imports `from src.`

```python
# ✓ BON
from utils.symbols import LogSymbols
from core.installer import ModInstaller
from model_types import DownloadResult

# ✗ MAUVAIS - L'application ne peut pas s'exécuter depuis src/
from src.utils.symbols import LogSymbols  # ❌
from src.core.installer import ModInstaller  # ❌
```

### 2. Imports relatifs dans gui/

```python
# Dans gui/dialogs.py
from .ui_builder import _create_button  # ✓ relatif
from utils.theme import TriOSTheme      # ✓ absolu depuis src/
```

### 3. Ordre des imports

```python
# 1. Stdlib
import os
import json
from pathlib import Path

# 2. Third-party
import requests

# 3. Types partagés
from model_types import DownloadResult

# 4. Core modules
from core.installer import ModInstaller

# 5. Utils
from utils.symbols import LogSymbols
from utils.mod_utils import scan_installed_mods
```

## Thread-safety et UI

### Marshalling UI depuis threads

**TOUJOURS** utiliser `root.after()` pour mutations UI depuis threads :

```python
# ✓ BON
def download_in_thread():
    result = download_mod(url)
    self.root.after(0, lambda: self.update_ui(result))

# ✗ MAUVAIS - Crash Tkinter
def download_in_thread():
    result = download_mod(url)
    self.label.config(text=result)  # ❌ Direct UI mutation from thread
```

### Logging thread-safe

```python
# Dans main_window.py
def log(self, message, success=False, error=False, warning=False, info=False, debug=False):
    """Thread-safe logging via root.after()"""
    def _log():
        # UI mutations here
        self.log_text.insert('end', formatted_message)
    
    self.root.after(0, _log)
```

## Gestion des backups

### Retention policy unifiée

**TOUJOURS** utiliser `backup_manager` avec retention automatique :

```python
# ✓ BON - Retention automatique (4 backups)
backup_manager = BackupManager(starsector_path, log_callback=self.log)
result = backup_manager.create_backup()  # Cleanup automatique

# ✗ MAUVAIS - Pas de retention
MAX_BACKUPS = 5  # ❌ Valeur arbitraire dispersée
manually_delete_old_backups()  # ❌ Logique dupliquée
```

### BackupManager API

```python
# Création avec cleanup automatique
result = backup_manager.create_backup()
# → BackupResult(path=Path(...), success=True, error=None)

# Restore
success, error = backup_manager.restore_backup(backup_path)

# Cleanup manuel
backup_manager.cleanup_old_backups()

# Suppression
success, error = backup_manager.delete_backup(backup_path)
```

## Tests

### Exécution

```bash
pytest tests/test_suite.py -v
```

### Mocks avec NamedTuples

```python
# ✓ BON - Mock retourne NamedTuple
mock_backup_mgr.create_backup.return_value = BackupResult(
    Path("backup_20251220"), True, None
)

# ✗ MAUVAIS - Mock retourne tuple
mock_backup_mgr.create_backup.return_value = (Path("backup"), True, None)  # ❌
```

### Test pattern

```python
def test_feature(mock_app, tmp_path):
    # Setup
    mock_app.modlist_data = {"mods": [{"name": "TestMod", "url": "..."}]}
    
    # Execute
    result = mock_app.some_function()
    
    # Assert
    assert result.success
    mock_app.log.assert_called_with(f"{LogSymbols.SUCCESS} ...", success=True)
```

## Docstrings

### Style minimaliste

```python
# ✓ BON - Concis mais informatif
def install_mod(self, mod, mods_dir):
    """Install mod from archive to mods directory.
    
    Args:
        mod: Mod config dict with name, url, version
        mods_dir: Target installation directory
        
    Returns:
        bool: Success status
    """

# ✗ MAUVAIS - Trop verbeux
def install_mod(self, mod, mods_dir):
    """This function installs a mod from an archive.
    
    It performs the following steps:
    1. Downloads the mod archive
    2. Extracts it to a temporary location
    3. Moves files to the mods directory
    
    Args:
        mod: A dictionary containing mod configuration
        mods_dir: The directory where mods should be installed
        
    Returns:
        bool: True if successful, False otherwise
        
    Raises:
        ValueError: If mod dict is invalid
        IOError: If filesystem errors occur
    """  # ❌ Trop de détails
```

### Éviter les commentaires obvies

```python
# ✓ BON - Code self-explanatory
def create_backup(self):
    backup_path = self.backups_dir / f"backup_{timestamp}"
    shutil.copy2(self.enabled_mods_path, backup_path)
    self.cleanup_old_backups()
    return BackupResult(backup_path, True, None)

# ✗ MAUVAIS - Commentaires redondants
def create_backup(self):
    # Create backup path  # ❌
    backup_path = self.backups_dir / f"backup_{timestamp}"
    # Copy enabled_mods.json to backup  # ❌
    shutil.copy2(self.enabled_mods_path, backup_path)
    # Clean old backups  # ❌
    self.cleanup_old_backups()
    # Return result  # ❌
    return BackupResult(backup_path, True, None)
```

## Error handling

### Messages utilisateur friendly

```python
# Utiliser error_messages.py pour UX
from utils.error_messages import get_user_friendly_error

try:
    download_mod(url)
except requests.exceptions.Timeout:
    user_msg = get_user_friendly_error('network_timeout')
    self.log(f"{LogSymbols.ERROR} {user_msg}", error=True)
```

### Logging structuré

```python
# ✓ BON - Symboles + contexte
self.log(f"{LogSymbols.ERROR} Download failed: {mod['name']}", error=True)
self.log(f"{LogSymbols.WARNING} Disk space low: {free_gb}GB", warning=True)

# ✗ MAUVAIS - Pas de symbole, pas de contexte
self.log("Failed", error=True)  # ❌
```

## Performance

### Téléchargements parallèles

```python
# Installation controller utilise ThreadPoolExecutor
with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as executor:
    futures = [executor.submit(download_fn, mod) for mod in mods]
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
```

### Extraction optimisée

```python
# Détection automatique ZIP vs 7z
is_7z = url.endswith('.7z') or '7z' in url.lower()
result = DownloadResult(temp_path, is_7z)
```

## Sécurité

### Path traversal prevention

```python
# Dans archive_extractor.py
for member in archive.namelist():
    extract_path = (target_dir / member).resolve()
    if not extract_path.is_relative_to(target_dir):
        self.log(f"{LogSymbols.ERROR} Path traversal blocked", error=True)
        return False
```

### Google Drive virus scan

```python
# Auto-détection HTML vs fichier binaire
if b'<html' in content[:1024].lower():
    self.log(f"{LogSymbols.WARNING} Google Drive HTML warning", error=True)
```

## Checklist avant commit

- [ ] Tous les tests passent (88/88)
- [ ] Aucun import `from src.`
- [ ] **Aucun symbole Unicode hardcodé** (utiliser `LogSymbols`/`UISymbols`)
- [ ] Tous les tuples de retour sont des NamedTuples
- [ ] Thread-safety : UI mutations via `root.after()`
- [ ] Backup retention utilise `backup_manager`
- [ ] Pas de commentaires obvies
- [ ] Docstrings concises
- [ ] Application se lance : `python src/modlist_installer.py`

## Commandes utiles

```bash
# Tests
pytest tests/test_suite.py -v

# Test spécifique
pytest tests/test_suite.py::TestClassName::test_method -v

# Lancer l'app
python src/modlist_installer.py

# Vérifier imports
python -c "import sys; sys.path.insert(0, 'src'); from gui import ModlistInstaller"
```
```
