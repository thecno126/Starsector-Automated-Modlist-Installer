# Plan de Refactorisation - Starsector Automated Modlist Installer

## 📊 Analyse de l'Architecture Actuelle

### Structure des Modules

```
src/
├── modlist_installer.py (19 lignes - Entry point ✓)
├── core/
│   ├── __init__.py (exports clairs ✓)
│   ├── constants.py (~145 lignes - config + InstallationReport)
│   ├── config_manager.py (~130 lignes - gestion JSON)
│   ├── installer.py (~878 lignes - ⚠️ TROP LONG)
│   └── archive_extractor.py (~260 lignes - extraction)
├── gui/
│   ├── __init__.py (exports ✓)
│   ├── main_window.py (~1802 lignes - ⚠️ TRÈS LONG)
│   ├── installation_controller.py (~473 lignes - orchestration)
│   ├── dialogs.py (~1136 lignes - ⚠️ LONG, répétitions)
│   └── ui_builder.py (~547 lignes - composants UI)
└── utils/
    ├── __init__.py
    ├── mod_utils.py (~400 lignes - parsing, comparaisons)
    ├── path_validator.py (~130 lignes - validation chemins)
    ├── backup_manager.py (~150 lignes - backups)
    ├── error_messages.py (~130 lignes - messages d'erreur)
    └── theme.py (~180 lignes - thème TriOS)
```

**Total: ~5500 lignes Python**

---

## 🔴 Problèmes Identifiés

### 1. **Fichiers Trop Longs** (>500 lignes)

| Fichier | Lignes | Problèmes |
|---------|--------|-----------|
| `gui/main_window.py` | 1802 | Classe `ModlistInstaller` fait tout : UI, logique, état, événements |
| `gui/dialogs.py` | 1136 | Répétitions dans création dialogs, patterns similaires |
| `core/installer.py` | 878 | Mélange validation URL, download, metadata, dépendances |
| `gui/ui_builder.py` | 547 | Beaucoup de boilerplate pour widgets similaires |

### 2. **Responsabilités Mal Définies**

#### `gui/main_window.py` fait TROP :
- ✅ Création UI
- ✅ Gestion événements
- ❌ **Manipulation directe de `modlist_data`** (devrait être dans `core.ConfigManager`)
- ❌ **Logique de drag & drop + réordonnancement** (devrait être séparée)
- ❌ **Formatage d'affichage de la modlist** (helpers séparés)
- ❌ **Gestion d'état d'installation** (partiellement dans `InstallationController` mais pas assez)

#### `core/installer.py` mélange :
- Validation réseau (`validate_mod_urls`)
- Téléchargement (`download_archive`)
- Extraction de metadata (`extract_mod_metadata`)
- Gestion dépendances (`resolve_mod_dependencies`)
- Comparaison versions (déjà dans `utils/mod_utils.py` - **duplication**)

### 3. **Duplications**

- **Parsing `mod_info.json`**: dans `core/installer.py` ET `utils/mod_utils.py`
- **Normalisation noms mods**: patterns similaires à plusieurs endroits
- **Création de dialogs**: beaucoup de code répété dans `gui/dialogs.py`
- **Gestion erreurs réseau**: logique retry éparpillée

### 4. **Commentaires/Docstrings Excessifs**

- ~40% des lignes sont des docstrings/commentaires
- Beaucoup répètent juste le code ("Load modlist configuration from JSON file")
- Args/Returns évidents sur-documentés
- Exemples doctest non maintenus

---

## 🎯 Plan de Refactorisation par Étapes

### **Phase 1 : Nettoyage Commentaires** (Rapide, bas risque)

**Objectif**: Réduire ~500-800 lignes en supprimant commentaires inutiles

#### Règles à appliquer:
1. **Supprimer** docstrings de module qui répètent juste le nom
2. **Supprimer** docstrings de fonction évidentes (ex: `get_mods_dir`, `normalize_mod_name`)
3. **Garder** uniquement:
   - Logique complexe (retry avec backoff, parsing regex, sécurité zip-slip)
   - Cas limites OS (macOS .app, PyInstaller paths)
   - Raisons de design non évidentes

#### Fichiers prioritaires:
- `core/installer.py` : supprimer ~100 lignes de docstrings
- `gui/main_window.py` : supprimer ~150 lignes
- `gui/dialogs.py` : supprimer ~80 lignes
- `utils/mod_utils.py` : supprimer ~60 lignes

**Résultat attendu**: -390 lignes, code plus lisible

---

### **Phase 2 : Extraction Helpers dans `utils/`** (Risque moyen)

#### 2.1 Créer `utils/network_utils.py`

**Extraire de `core/installer.py`**:
```python
# utils/network_utils.py
def retry_with_backoff(func, max_retries=3, delay=2, backoff=2):
    """Retry function with exponential backoff."""
    ...

def validate_url(url, timeout=6):
    """Validate single URL with HEAD/GET fallback."""
    ...

def download_file(url, dest_path, progress_callback=None):
    """Download file with progress tracking."""
    ...
```

**Impact**: `core/installer.py` passe de 878 → ~700 lignes

#### 2.2 Créer `utils/ui_helpers.py`

**Extraire de `gui/ui_builder.py`**:
```python
# utils/ui_helpers.py
def create_labeled_frame(parent, title, **kwargs):
    """Helper for consistent LabelFrame creation."""
    ...

def create_text_with_scrollbar(parent, **kwargs):
    """Helper for Text widget + scrollbar."""
    ...

def pack_button_row(parent, buttons_config):
    """Pack multiple buttons in a row with consistent spacing."""
    ...
```

**Impact**: `gui/ui_builder.py` passe de 547 → ~400 lignes

#### 2.3 Factoriser `gui/dialogs.py`

**Créer helper pour dialogs génériques**:
```python
def create_base_dialog(parent, title, width=500):
    """Create base Toplevel with consistent styling."""
    ...

def add_scrollable_list(frame, items, height=10):
    """Add scrollable list widget."""
    ...
```

**Impact**: `gui/dialogs.py` passe de 1136 → ~800 lignes

---

### **Phase 3 : Réorganiser `core/installer.py`** (Risque moyen-élevé)

#### 3.1 Séparer en sous-modules

**Créer `core/mod_validator.py`**:
```python
# core/mod_validator.py
class ModValidator:
    def validate_urls(self, mods, progress_callback=None):
        """Validate all mod URLs in parallel."""
        ...
    
    def check_dependencies(self, mods, installed_mods):
        """Check missing dependencies."""
        ...
    
    def check_versions(self, mod_name, expected_version, mods_dir):
        """Check if mod is up-to-date."""
        ...
```

**Créer `core/mod_downloader.py`**:
```python
# core/mod_downloader.py
class ModDownloader:
    def __init__(self, log_callback):
        self.log = log_callback
    
    def download_archive(self, mod, skip_gdrive_check=False):
        """Download single mod archive."""
        ...
    
    def download_batch(self, mods, max_workers=3):
        """Download multiple mods in parallel."""
        ...
```

**Simplifier `core/installer.py`**:
```python
# core/installer.py (devient orchestrateur)
class ModInstaller:
    def __init__(self, log_callback):
        self.log = log_callback
        self.validator = ModValidator(log_callback)
        self.downloader = ModDownloader(log_callback)
        self.extractor = ArchiveExtractor(log_callback)
    
    def install_mods(self, mods, mods_dir, ...):
        """High-level installation orchestration."""
        validation = self.validator.validate_urls(mods)
        downloads = self.downloader.download_batch(mods_to_install)
        # ...
```

**Impact**: 
- `core/installer.py`: 878 → ~250 lignes
- Nouveaux fichiers: +400 lignes (mais mieux organisées)

---

### **Phase 4 : Alléger `gui/main_window.py`** (Risque élevé)

#### 4.1 Créer `gui/modlist_display.py`

**Extraire logique d'affichage**:
```python
# gui/modlist_display.py
class ModlistDisplay:
    def __init__(self, listbox, header_text):
        self.listbox = listbox
        self.header = header_text
    
    def render_modlist(self, modlist_data, categories, search_filter=""):
        """Render modlist with categories and formatting."""
        ...
    
    def highlight_selected_line(self, line_num):
        """Apply selection highlighting."""
        ...
    
    def get_mod_at_line(self, line_num):
        """Extract mod data from line."""
        ...
```

#### 4.2 Créer `gui/modlist_editor.py`

**Extraire logique d'édition**:
```python
# gui/modlist_editor.py
class ModlistEditor:
    def __init__(self, config_manager):
        self.config = config_manager
    
    def add_mod(self, mod_data):
        """Add mod to modlist data."""
        ...
    
    def remove_mod(self, mod_name):
        """Remove mod from modlist data."""
        ...
    
    def move_mod(self, mod_name, target_category, position):
        """Move mod to different category/position."""
        ...
    
    def update_mod(self, mod_name, new_data):
        """Update mod properties."""
        ...
```

#### 4.3 Créer `gui/drag_drop_handler.py`

**Extraire drag & drop**:
```python
# gui/drag_drop_handler.py
class DragDropHandler:
    def __init__(self, listbox, on_reorder_callback):
        self.listbox = listbox
        self.on_reorder = on_reorder_callback
        self.drag_state = None
        self._setup_bindings()
    
    def _setup_bindings(self):
        self.listbox.bind('<Button-1>', self._on_drag_start)
        self.listbox.bind('<B1-Motion>', self._on_drag_motion)
        self.listbox.bind('<ButtonRelease-1>', self._on_drag_end)
    
    # ... drag logic
```

#### 4.4 Simplifier `ModlistInstaller`

**Résultat après extraction**:
```python
# gui/main_window.py (simplifié)
class ModlistInstaller:
    def __init__(self, root):
        self.root = root
        self.config_manager = ConfigManager()
        
        # Délégation responsabilités
        self.modlist_editor = ModlistEditor(self.config_manager)
        self.installation_controller = InstallationController(self)
        
        self.create_ui()
        
        # Setup après UI
        self.modlist_display = ModlistDisplay(self.mod_listbox, self.header_text)
        self.drag_handler = DragDropHandler(self.mod_listbox, self.on_mod_reordered)
    
    def create_ui(self):
        """Create UI structure (delegation to ui_builder)."""
        ...
    
    # Callbacks simples qui délèguent
    def open_add_mod_dialog(self):
        result = dialogs.open_add_mod_dialog(...)
        if result:
            self.modlist_editor.add_mod(result)
            self.refresh_display()
```

**Impact**: `gui/main_window.py` passe de 1802 → ~600 lignes

---

### **Phase 5 : Harmonisation & Polish** (Bas risque)

#### 5.1 Conventions de Nommage

**Uniformiser**:
- Variables d'état: `is_*` pour bool, `current_*` pour valeurs
- Callbacks: `on_*` pour événements UI
- Helpers privés: préfixe `_` systématique
- Constants: `UPPER_SNAKE_CASE` strict

#### 5.2 Type Hints (Optionnel)

Ajouter annotations aux fonctions publiques importantes:
```python
from pathlib import Path
from typing import List, Dict, Optional, Tuple

def validate_mod_urls(
    mods: List[Dict[str, str]], 
    progress_callback: Optional[callable] = None
) -> Dict[str, List]:
    ...
```

#### 5.3 Logs Harmonisés

Centraliser format de logs:
```python
# utils/logger.py
class Logger:
    def __init__(self, text_widget):
        self.text = text_widget
    
    def info(self, msg): ...
    def error(self, msg): ...
    def success(self, msg): ...
    def debug(self, msg): ...
```

---

## 📈 Résultats Attendus

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| Lignes totales | ~5500 | ~4200 | -24% |
| Fichiers >500 lignes | 4 | 0 | -100% |
| Commentaires/Docstrings | ~2200 | ~800 | -64% |
| Fichiers Python | 15 | 22 | +47% (mieux organisé) |
| Fonction max lignes | ~200 | <80 | -60% |

---

## 🚦 Ordre d'Exécution Recommandé

### Semaine 1 : Préparation (Phase 1)
- ✅ Nettoyer commentaires/docstrings
- ✅ Tests de non-régression (app doit fonctionner identiquement)

### Semaine 2 : Extraction Helpers (Phase 2)
- ✅ Créer `utils/network_utils.py`
- ✅ Créer `utils/ui_helpers.py`
- ✅ Factoriser `gui/dialogs.py`
- ✅ Tests à chaque étape

### Semaine 3 : Refactor Core (Phase 3)
- ✅ Créer `core/mod_validator.py`
- ✅ Créer `core/mod_downloader.py`
- ✅ Simplifier `core/installer.py`
- ✅ Tests intensifs installation

### Semaine 4 : Refactor GUI (Phase 4)
- ✅ Créer `gui/modlist_display.py`
- ✅ Créer `gui/modlist_editor.py`
- ✅ Créer `gui/drag_drop_handler.py`
- ✅ Simplifier `gui/main_window.py`
- ✅ Tests UI complets

### Semaine 5 : Polish (Phase 5)
- ✅ Harmoniser nommage
- ✅ Ajouter type hints
- ✅ Centraliser logger
- ✅ Tests finaux + doc

---

## 🔧 Stratégie de Tests

### Tests à Maintenir
1. **Installation complète** : installer 3-5 mods depuis modlist
2. **Validation URL** : vérifier GitHub, Google Drive, autres domaines
3. **Gestion erreurs** : simuler échecs réseau, espace disque
4. **Drag & Drop** : réordonner mods dans UI
5. **Import/Export CSV** : vérifier préservation données

### Tests Automatisés (Optionnel)
```bash
# tests/test_refactoring.py
def test_mod_validator():
    validator = ModValidator(lambda x: None)
    result = validator.validate_urls([...])
    assert 'github' in result
    assert 'failed' in result

def test_modlist_editor():
    editor = ModlistEditor(ConfigManager())
    editor.add_mod({'name': 'TestMod', ...})
    assert 'TestMod' in editor.get_all_mods()
```

---

## 📝 Commentaires/Docstrings : Guide Final

### ✅ À GARDER

```python
def retry_with_backoff(func, max_retries=3, delay=2, backoff=2):
    """Retry function with exponential backoff on exceptions."""
    # Utile car logique non triviale
```

```python
if sys.platform == "darwin" and '.app' in sys.executable:
    # macOS .app bundle - go up to folder containing .app
    BASE_DIR = Path(sys.executable).resolve().parent.parent.parent.parent
```

```python
def extract_mod_version_from_text(content):
    """Extract mod version from mod_info.json text.
    
    Handles both object format {major:0, minor:12} and string format "1.5.0".
    Must come before gameVersion to avoid false matches.
    """
```

### ❌ À SUPPRIMER

```python
def normalize_mod_name(name):
    """
    Normalize a mod name for comparison by removing spaces, hyphens, and underscores.
    Case-insensitive.
    
    Args:
        name: Mod name to normalize
        
    Returns:
        str: Normalized name (lowercase, no spaces/hyphens/underscores)
        
    Examples:
        >>> normalize_mod_name("Graphics Lib")
        'graphicslib'
        >>> normalize_mod_name("My-Awesome_Mod")
        'myawesomemod'
    """
    # Trop verbeux pour une fonction simple
```

**Remplacer par**:
```python
def normalize_mod_name(name):
    """Remove spaces/hyphens/underscores and lowercase."""
    return re.sub(r'[\s\-_]', '', str(name).lower()) if name else ''
```

---

## 🎓 Principes de Refactorisation Appliqués

1. **Single Responsibility**: Chaque classe/fonction fait UNE chose
2. **Separation of Concerns**: GUI ≠ Logique ≠ Utils
3. **DRY (Don't Repeat Yourself)**: Factoriser patterns répétés
4. **KISS (Keep It Simple)**: Éviter sur-ingénierie
5. **Boy Scout Rule**: Laisser le code plus propre qu'on l'a trouvé

---

## 📚 Ressources

- [PEP 8 Style Guide](https://pep8.org/)
- [Refactoring Guru](https://refactoring.guru/refactoring)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

---

**Auteur**: GitHub Copilot  
**Date**: 18 décembre 2025  
**Version**: 1.0
