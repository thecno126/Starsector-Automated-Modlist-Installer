# Starsector Automated Modlist Installer

Outil GUI pour gérer et installer des modlists Starsector, avec détection intelligente des liens (GitHub, Mediafire, Google Drive), extraction de métadonnées sans décompression complète, et interface soignée.

## Aperçu

**Gestion de liens intelligente:**
- Catégorisation automatique: GitHub, **Mediafire** (affiché en priorité), Google Drive, Autres
- **Google Drive**: correction d'URL automatique (`drive.usercontent.google.com`) et contournement de l'avertissement "virus scan" pour les fichiers volumineux
- **Détection 7z robuste**: via l'en-tête `Content-Disposition` (nom de fichier), indépendamment du `Content-Type`

**Extraction intelligente:**
- Lecture de `mod_info.json` **sans extraction complète** des archives (ZIP/7z)
- Gain de temps et d'espace disque

**Gestion de modlists:**
- Export de modlist/preset via l'UI (les backups automatiques ont été retirés)
- Activation "modlist-only": le bouton "Enable All Mods" active **uniquement** les mods installés présents dans la modlist courante
- Patch LunaLib: écrit dans `saves/common/LunaSettings/`

**Interface utilisateur:**
- Bouton **Refresh** déplacé en bas, à gauche du bouton **Wipe**
- Contours colorés: **bleu** (Refresh), **rouge** (Wipe)
- **Tooltips persistants**: restent visibles après utilisation des boutons
- **Compteur de mods**: overlay en haut à droite, sans perte d'espace vertical
- Thème: `AppTheme` (nomenclature neutre)

## Prérequis

- **Python 3.10+**
- **Tkinter** (inclus par défaut sur macOS et la plupart des distributions Linux)
- **Dépendances Python**: `requests`, `py7zr` (optionnel pour archives 7z)

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate  # ou '. .venv/bin/activate'
pip install -r requirements.txt
```

## Lancement

```bash
source .venv/bin/activate  # Activer l'environnement virtuel
python src/modlist_installer.py
```

Ou en une seule commande:
```bash
.venv/bin/python src/modlist_installer.py
```

## Fonctionnalités

### Validation et catégorisation d'URL
- Détection automatique: **GitHub**, **Mediafire**, **Google Drive**, Autres
- Mediafire affiché **avant** Google Drive dans l'interface

### Google Drive
- Dialogue de confirmation pour les fichiers volumineux
- Correction d'URL vers `drive.usercontent.google.com` pour téléchargement direct

### Archives
- Support **ZIP** et **7z**
- Extraction de `mod_info.json` **sans extraction complète** (économie de temps/espace)
- Détection 7z via `Content-Disposition: filename=...` (robuste même si `Content-Type` incorrect)

### Modlists et Presets
- **Export**: sauvegarde de votre modlist actuelle
- **Import**: chargement de presets depuis `config/presets/`
- **Activation modlist-only**: "Enable All Mods" active uniquement les mods listés et installés

### LunaLib
- Patch des configurations vers `saves/common/LunaSettings/`
- Application globale au profil de jeu

### Interface
- **Tooltips persistants**: informations au survol stables
- **Compteur de mods**: affichage overlay dynamique en haut à droite
- **Boutons stylisés**: Refresh (contour bleu) et Wipe (contour rouge) côte à côte en bas

## Configuration

- **Fichiers de configuration**: [config](config)
- **Presets**: [config/presets](config/presets)
- **Chemin LunaLib**: `saves/common/LunaSettings/`

## Dépannage

### Google Drive
- **Problème**: Fichier trop volumineux, avertissement "virus scan"
- **Solution**: Un dialogue s'affiche; l'URL est automatiquement corrigée pour téléchargement direct

### Fichiers 7z
- **Problème**: `Content-Type` ambigu ou incorrect
- **Solution**: La détection se base sur `Content-Disposition: filename=...` (nom de fichier)

### Chemin Starsector
- **Problème**: Installation Starsector non détectée
- **Solution**: Sélectionnez manuellement le chemin via l'interface

## FAQ

**Q: Pourquoi je peux activer 20 mods alors que seulement 19 sont listés?**  
R: Désormais corrigé — l'activation cible **uniquement** les mods présents dans la modlist courante.

**Q: Où sont les backups automatiques?**  
R: Les backups automatiques ont été retirés. Utilisez la fonction **Export** pour sauvegarder votre modlist.

**Q: Comment exporter ma modlist?**  
R: Utilisez le bouton 💾 **SAVE** pour exporter vers `config/presets/<nom>/`.

## Tests

```bash
source .venv/bin/activate
pytest tests/test_suite.py -v
```

Ou exécution directe:
```bash
.venv/bin/python tests/test_suite.py
```

**Couverture**: import/export presets, correction URL Google Drive, détection 7z, extraction `mod_info.json`, activation modlist-only.

## Licence et Contrib

Projet open-source — contributions bienvenues.
