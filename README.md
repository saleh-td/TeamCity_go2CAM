# TeamCity Monitor

Un outil de surveillance des builds TeamCity avec intégration dynamique et configuration JSON.

## 🎯 **Nouveau système d'intégration**

Le système combine maintenant :
- **Données dynamiques** : Récupération automatique de tous les projets non-archivés via l'API TeamCity
- **Configuration JSON** : Filtrage et organisation selon les patterns définis dans `config/dashboard_config.json`

## 📁 **Structure du projet**

```
teamcity_monitor/
├── api/
│   ├── services/
│   │   ├── teamcity_fetcher.py      # API TeamCity (nettoyé)
│   │   ├── config_service.py        # Service de configuration JSON
│   │   └── build_tree_service.py    # Arborescence des builds
│   └── routes/
│       ├── config_routes.py         # Nouvelles routes organisées
│       └── builds.py                # Routes existantes
├── config/
│   └── dashboard_config.json        # Configuration des patterns
└── frontend/
    └── assets/
        └── js/
            ├── Dashboard.js         # Interface utilisateur
            └── Config.js            # Configuration
```

## 🔧 **Configuration JSON**

Le fichier `config/dashboard_config.json` définit :

### **Projets et patterns**
```json
{
  "projects": {
    "GO2 Version 612": {
      "builds": "builds-612",
      "title": "title-612",
      "icon": "database",
      "prefixes": ["Go2Version612"]
    },
    "GO2 Version New": {
      "builds": "builds-new",
      "title": "title-new", 
      "icon": "sparkles",
      "prefixes": [
        "Go2VersionNew",
        "InstalleursNew",
        "GO2camNew"
      ]
    }
  }
}
```

### **Sous-catégories**
```json
{
  "subcategories": {
    "ProductInstall": {
      "patterns": ["ProductInstall", "Installeurs"],
      "subprojects": ["Meca", "Dental"]
    }
  }
}
```

### **Statuts et détection automatique**
```json
{
  "statuses": {
    "SUCCESS": ["SUCCESS", "success"],
    "FAILURE": ["FAILURE", "failure", "FAILED"],
    "RUNNING": ["RUNNING", "running"]
  },
  "autoDetection": {
    "enabled": true,
    "fallbackToConfig": true,
    "cacheTimeout": 300,
    "maxProjects": 10
  }
}
```

## 🚀 **Nouvelles API endpoints**

### **Builds organisés**
- `GET /api/organized/builds` - Builds filtrés selon la configuration JSON
- `GET /api/organized/builds/status` - Builds avec statut actuel
- `GET /api/organized/dashboard` - Dashboard complet avec sélection utilisateur

### **Projets et agents**
- `GET /api/organized/projects` - Projets organisés par catégorie
- `GET /api/organized/agents` - Agents avec statistiques

### **Configuration**
- `GET /api/organized/config` - Configuration complète (JSON + utilisateur)
- `POST /api/organized/cache/clear` - Vide le cache

## 🔄 **Fonctionnement**

### **1. Récupération dynamique**
```python
# Récupère tous les projets non-archivés
builds_data = fetch_all_teamcity_builds()
```

### **2. Filtrage par patterns**
```python
# Filtre selon les prefixes du JSON
filtered_builds = config_service.filter_builds_by_project_patterns(builds_data)
```

### **3. Organisation par catégorie**
```python
# Organise en catégories définies dans le JSON
organized_data = {
    "GO2 Version 612": [...],
    "GO2 Version New": [...],
    "Autres": [...]
}
```

### **4. Métadonnées des projets**
```python
# Récupère titre, icône, etc.
metadata = config_service.get_project_metadata("GO2 Version 612")
# → {"title": "title-612", "icon": "database", "builds_id": "builds-612"}
```

## 📊 **Exemple de réponse API**

```json
{
  "builds": {
    "GO2 Version 612": [
      {
        "id": "Go2Version612_ProductInstall_BuildDebug",
        "buildTypeId": "Go2Version612_ProductInstall_BuildDebug",
        "name": "Build Debug",
        "status": "SUCCESS",
        "state": "finished",
        "webUrl": "http://teamcity/viewType.html?buildTypeId=...",
        "projectName": "GO2 Version 612"
      }
    ]
  },
  "categories": {
    "GO2 Version 612": {
      "title": "title-612",
      "icon": "database",
      "builds_id": "builds-612"
    }
  },
  "total_builds": 1,
  "running_count": 0,
  "success_count": 1,
  "failure_count": 0
}
```

## 🎛️ **Configuration utilisateur**

La sélection des builds est stockée dans `config/user_config.json` :

```json
{
  "builds": {
    "selectedBuilds": [
      "Go2Version612_ProductInstall_BuildDebug",
      "Go2VersionNew_ProductCompil_BuildRelease"
    ]
  }
}
```

## 🔄 **Migration depuis l'ancien système**

1. **Les routes existantes continuent de fonctionner**
2. **Nouvelles routes organisées disponibles**
3. **Configuration JSON optionnelle** (fallback automatique)
4. **Cache intelligent** pour les performances

## 🚀 **Démarrage**

```bash
# Installation
pip install -r requirements.txt

# Configuration
cp env.example .env
# Éditer .env avec vos paramètres TeamCity

# Démarrage
python start_server.py
```

## 📈 **Avantages du nouveau système**

- ✅ **Détection automatique** de tous les projets TeamCity
- ✅ **Filtrage intelligent** selon les patterns JSON
- ✅ **Organisation flexible** par catégories
- ✅ **Métadonnées enrichies** (titres, icônes)
- ✅ **Cache optimisé** pour les performances
- ✅ **Rétrocompatibilité** avec l'ancien système
- ✅ **Configuration utilisateur** persistante 