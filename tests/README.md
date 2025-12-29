# Tests

Documentation de la suite de tests pour Starsector Automated Modlist Installer.

## Lancer les tests
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Exécuter le runner principal
pytest tests/test_suite.py -v

# Ou exécuter directement via Python
.venv/bin/python tests/test_suite.py
```

## Couverture des tests

### Import/Export de presets
- Validation de la structure JSON (`modlist_config.json`, `lunalib_config.json`)
- Chargement et sauvegarde depuis/vers `config/presets/<name>/`
- Détection d'erreurs (presets invalides, chemins manquants)

### Correction d'URL Google Drive
- Formats supportés: `/file/d/<ID>/view`, `?id=<ID>`
- Correction automatique vers `drive.usercontent.google.com`
- Détection des réponses HTML (page d'avertissement virus scan)
- Dialogue de confirmation pour fichiers volumineux

### Détection d'archives 7z
- Détection via `Content-Disposition: filename=...` (priorité sur `Content-Type`)
- Support des noms de fichiers avec extension `.7z`
- Fallback robuste si `Content-Type` est ambigu

### Extraction `mod_info.json`
- Extraction **sans décompression complète** (ZIP et 7z)
- Support `py7zr` pour archives 7z
- Lecture directe depuis l'archive avec `zipfile` et `py7zr`
- Économie de temps et d'espace disque

### Activation "modlist-only"
- Mise à jour de `enabled_mods.json` pour activer **uniquement** les mods:
  - Présents dans la modlist courante
  - **ET** installés dans le dossier `mods/`
- Vérification des `mod_id` pour correspondance exacte
- Résout le problème "20 mods activés pour 19 listés"

### Validations et messages d'erreur
- Dialogs (confirmations, erreurs, succès)
- Validations de chemins (Starsector install, mod folders)
- Permissions d'écriture (config, mods, saves)

### Fichiers de test JSON

Des fichiers de test sont fournis **à la racine du projet**:
- `test_import_modlist.json` — modlist de test pour import
- `test_invalid_preset.json` — preset invalide (validation d'erreur)
- `test_lunalib_patch.json` — configuration LunaLib de test
- `test_import_lunalib.json` — preset avec LunaLib config

Ces fichiers permettent de valider les flux complets d'import/export et de patch LunaLib.

## Structure
```
tests/
├── README.md       # Ce fichier
└── test_suite.py   # Runner de tests principal
```
