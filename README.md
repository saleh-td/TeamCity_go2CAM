# TeamCity Monitor

Un outil de surveillance des builds TeamCity **100% générique** avec intégration dynamique.

## 🎯 **Système générique**

L'application fonctionne avec **n'importe quel serveur TeamCity** :
- **Récupération automatique** : Tous les projets et builds via l'API TeamCity
- **Filtrage intelligent** : Exclusion automatique des projets archivés
- **Interface utilisateur** : Sélection libre des builds à monitorer

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

## 🔧 **Configuration automatique**

L'application se configure automatiquement :

### **Détection des projets**
```json
{
  "detection": "automatic",
  "source": "teamcity_api",
  "filtering": "archived_attribute",
  "user_selection": "web_interface"
}
```

### **Fonctionnalités automatiques**
```json
{
  "features": {
    "project_detection": "dynamic_from_teamcity",
    "archived_filtering": "api_attribute_based",
    "build_status": "real_time",
    "user_selection": "web_interface",
    "cache": "5_minutes"
  }
}
```

## 🚀 **API endpoints**

### **Builds et projets**
- `GET /api/builds` - Tous les builds actifs
- `GET /api/builds/tree` - Arborescence des projets pour configuration
- `GET /api/builds/dashboard` - Dashboard avec builds sélectionnés
- `POST /api/builds/tree/selection` - Sauvegarder sélection utilisateur

### **Agents et diagnostic**
- `GET /api/agents` - Agents TeamCity
- `GET /api/teamcity/test-connection` - Test de connexion TeamCity

### **Configuration**
- `GET /api/config` - Configuration utilisateur

## 🔄 **Fonctionnement**

### **1. Récupération automatique**
```python
# Récupère TOUS les projets depuis TeamCity
builds_data = fetch_all_teamcity_builds()
```

### **2. Filtrage intelligent**
```python
# Filtre automatiquement les projets archivés via l'API
if not is_project_active(project_name, project_archived, parent_archived):
    continue  # Exclure automatiquement
```

### **3. Organisation dynamique**
```python
# Structure basée sur la hiérarchie réelle TeamCity
tree = create_complete_tree_structure(builds_data)
```

### **4. Sélection utilisateur**
```python
# L'utilisateur choisit ce qu'il veut monitorer
selected_builds = user_service.get_selected_builds()
```

## 📊 **Exemple de réponse API**

```json
{
  "projects": {
    "Mon Projet Principal": {
      "name": "Mon Projet Principal",
      "subprojects": {
        "Compilation": {
          "name": "Compilation", 
          "subprojects": {
            "Builds": {
              "name": "Builds",
              "builds": [
                {
                  "buildTypeId": "MonProjet_Compilation_BuildDebug",
                  "name": "Build Debug",
                  "status": "SUCCESS",
                  "state": "finished",
                  "projectName": "Mon Projet Principal / Compilation"
                }
              ]
            }
          }
        }
      }
    }
  },
  "total_builds": 1,
  "selected_builds": []
}
```

## 🎛️ **Configuration utilisateur**

La sélection des builds est stockée en base de données :

```json
{
  "builds": {
    "selectedBuilds": [
      "MonProjet_Compilation_BuildDebug",
      "AutreProjet_Tests_BuildRelease"
    ]
  }
}
```

## 🔄 **Fonctionnalités**

1. **Application 100% générique** - fonctionne avec n'importe quel TeamCity
2. **Détection automatique** - aucune configuration manuelle requise
3. **Filtrage intelligent** - projets archivés exclus automatiquement
4. **Cache optimisé** - performances améliorées

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

## 🗄️ **Base de données (optionnelle)**

L'application fonctionne avant tout en communiquant directement avec TeamCity (aucun mapping/valeurs en dur).
La base de données est utilisée UNIQUEMENT pour persister les sélections utilisateur faites dans `config.html`.

- **Pourquoi**: quand un utilisateur coche/décoche des builds dans `config.html`, sa sélection doit être mémorisée
  pour que le dashboard l'affiche ensuite sans tout reconfigurer.
- **Comment**: `POST /api/builds/tree/selection` enregistre la sélection dans la table `user_build_selections`.
- **Lecture côté dashboard**: `GET /api/config` renvoie la liste `selectedBuilds` pour filtrer les builds.
- **Robustesse**: si la base est indisponible, un fallback fichier est utilisé automatiquement:
  `config/selected_builds.json`.

En pratique, vous pouvez donc démarrer et utiliser le projet SANS base de données. Dès qu'une DB MySQL est
disponible, l'application l'utilise et crée les tables si elles n'existent pas.

### Variables `.env`

Créez un fichier `.env` à la racine avec vos informations (exemple minimal):

```
# TeamCity
TEAMCITY_URL=http://XXXXXXXXXXX
TEAMCITY_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# Base de données (optionnelle)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=XXXX
DB_NAME=XXX
```

Notes:
- Ne commitez jamais le vrai token TeamCity ni les mots de passe.
- Si la base est hors ligne ou vide, vos sélections seront quand même conservées via le fallback fichier.
- Les tables sont créées automatiquement au démarrage (si la DB répond).

## 🧪 Tests

```bash
pip install -r requirements.txt
pytest -q
```

## 📈 **Avantages**

- ✅ **100% générique** - fonctionne avec tout TeamCity
- ✅ **Zéro configuration** - détection automatique
- ✅ **Filtrage intelligent** - projets archivés exclus
- ✅ **Interface intuitive** - sélection par l'utilisateur
- ✅ **Cache optimisé** - performances excellentes
- ✅ **Base de données** - persistance des sélections
- ✅ **API complète** - extensible et documentée 