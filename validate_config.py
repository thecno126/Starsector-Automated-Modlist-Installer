#!/usr/bin/env python3
"""
Script de validation du fichier modlist_config.json
Vérifie la structure et la cohérence des données
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def validate_modlist_config(config_path):
    """Valide la cohérence du fichier modlist_config.json"""
    
    print(f"📋 Validation de {config_path}")
    print("-" * 60)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Erreur de syntaxe JSON: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Fichier introuvable: {config_path}")
        return False
    
    # Vérifier les champs obligatoires
    required_fields = ['modlist_name', 'version', 'starsector_version', 'mods']
    missing = [f for f in required_fields if f not in data]
    if missing:
        print(f"❌ Champs manquants: {', '.join(missing)}")
        return False
    
    mods = data.get('mods', [])
    
    print(f"✓ {len(mods)} mods dans la liste")
    print()
    
    # Grouper par catégorie pour stats
    category_counts = defaultdict(int)
    for mod in mods:
        cat = mod.get('category', 'Uncategorized')
        category_counts[cat] += 1
    
    print(f"Répartition par catégorie:")
    for cat, count in sorted(category_counts.items()):
        print(f"  - {cat}: {count} mod(s)")
    print()
    
    # Détection des problèmes
    errors = []
    warnings = []
    
    # 1. Vérifier que chaque mod a un mod_id
    missing_ids = []
    for mod in mods:
        if not mod.get('mod_id'):
            missing_ids.append(f"{mod.get('name', 'INCONNU')}")
    
    if missing_ids:
        warnings.append("⚠️  Mods sans mod_id:")
        for mod in missing_ids:
            warnings.append(f"   - {mod}")
    
    # 2. Duplicatas de mod_id
    seen_ids = set()
    duplicates = []
    for mod in mods:
        mod_id = mod.get('mod_id')
        if mod_id:
            if mod_id in seen_ids:
                duplicates.append(f"{mod.get('name')} (ID: {mod_id})")
            seen_ids.add(mod_id)
    
    if duplicates:
        errors.append("❌ Mod_id en double:")
        for dup in duplicates:
            errors.append(f"   - {dup}")
    
    # 3. Vérifier les URLs
    missing_urls = []
    for mod in mods:
        if not mod.get('download_url'):
            missing_urls.append(f"{mod.get('name', 'INCONNU')}")
    
    if missing_urls:
        errors.append("❌ Mods sans download_url:")
        for mod in missing_urls:
            errors.append(f"   - {mod}")
    
    # 4. Vérifications des dépendances manquantes
    if mods and 'dependencies' in mods[0]:  # Si le champ existe
        missing_deps = []
        mod_ids = {m.get('mod_id') for m in mods if m.get('mod_id')}
        
        for mod in mods:
            deps = mod.get('dependencies', [])
            for dep_id in deps:
                if dep_id not in mod_ids:
                    missing_deps.append(
                        f"{mod.get('name')} nécessite '{dep_id}' qui n'est pas dans la modlist"
                    )
        
        if missing_deps:
            warnings.append("⚠️  Dépendances manquantes:")
            for msg in missing_deps:
                warnings.append(f"   - {msg}")
    
    # Affichage des résultats
    print()
    if warnings:
        for line in warnings:
            print(line)
        print()
    
    if errors:
        for line in errors:
            print(line)
        print()
        print("❌ Validation échouée - Des erreurs ont été détectées")
        return False
    else:
        print("✅ Aucune erreur détectée - Configuration valide!")
        return True

if __name__ == '__main__':
    config_path = Path(__file__).parent / 'config' / 'modlist_config.json'
    
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    
    success = validate_modlist_config(config_path)
    sys.exit(0 if success else 1)
