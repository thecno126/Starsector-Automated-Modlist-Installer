# Starsector Automated Modlist Installer

Outil GUI pour gérer et installer des modlists Starsector, avec détection des liens (GitHub, Mediafire, Google Drive), extraction intelligente de métadonnées, et une interface soignée.

## Aperçu
- Catégorisation des liens: GitHub, Mediafire (affiché avant Google Drive), Google Drive, Autres
- Google Drive: correction automatique d’URL et contournement de l’avertissement “virus scan” pour les fichiers volumineux
- Détection 7z robuste: via l’en-tête `Content-Disposition` (nom de fichier), pas seulement le `Content-Type`
- Extraction de `mod_info.json` sans extraction complète (ZIP/7z)
- Export de modlist (les backups ont été retirés)
- Activation “modlist-only”: le bouton “Enable All Mods” active uniquement les mods installés présents dans la modlist
- UI: bouton Refresh déplacé en bas à gauche du bouton Wipe; contours bleus/rouges pour Refresh/Wipe; tooltips persistants; compteur de mods overlay en haut à droite
- Thème: `AppTheme` (nomenclature neutre)

## Prérequis
- Python 3.10+
- macOS testé (Tkinter requis)
- `requests`, `py7zr` (optionnel pour les archives 7z)

## Installation
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Lancement
```bash
.venv/bin/python src/modlist_installer.py
```

## Fonctionnalités
- Validation d’URL et catégorisation (GitHub/Mediafire/GDrive/Autres)
- Google Drive: confirmation pour gros fichiers et URL directe corrigée (`drive.usercontent.google.com`)
- Extraction des métadonnées depuis `mod_info.json` dans archive (ZIP/7z), sans extraction complète
- Export de preset/modlist via l’UI
- Activation: uniquement les mods de la modlist et présents dans `mods/`
- Patch LunaLib: utilise `saves/common/LunaSettings/`
- UI améliorée: tooltips stables, compteur de mods overlay, contours de boutons (Refresh en bleu, Wipe en rouge)

## Configuration
- Fichiers de configuration sous [config](config)
- Presets sous [config/presets](config/presets)
- Le chemin LunaLib est `saves/common/LunaSettings/`

## Dépannage
- Google Drive: si le fichier est trop volumineux, un dialogue s’affiche et l’URL est corrigée pour le téléchargement direct
- Fichiers 7z: si `Content-Type` est ambigu, la détection se base sur `Content-Disposition: filename=...`
- Chemin Starsector: si non détecté, sélectionnez-le via l’UI

## FAQ
- “Pourquoi je peux activer 20 mods pour 19 listés?” → désormais l’activation cible uniquement les mods présents dans la modlist (problème corrigé)

## Tests
```bash
. .venv/bin/activate
.venv/bin/python tests/test_suite.py
```
Le test suit couvre import/export de presets, validation de liens (Mediafire/GDrive), extraction `mod_info.json`, et flux d’activation.

## Licence et Contrib
Projet open-source — contributions bienvenues.
