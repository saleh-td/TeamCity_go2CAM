# TeamCity Monitor - GO2CAM

## 📋 Description

Système de monitoring moderne pour TeamCity avec interface web responsive. Permet de surveiller les builds et agents TeamCity en temps réel avec une interface utilisateur intuitive.

## 🚀 Fonctionnalités

- **Dashboard en temps réel** : Affichage des statuts des builds avec animations
- **Configuration interactive** : Interface pour sélectionner les builds à surveiller
- **API REST moderne** : Backend Python FastAPI performant
- **Interface responsive** : Frontend HTML/CSS/JS moderne
- **Synchronisation automatique** : Rafraîchissement des données toutes les 60 secondes
- **Gestion des agents** : Surveillance des agents TeamCity

## 🛠️ Technologies

- **Backend** : Python 3.12, FastAPI, uvicorn
- **Frontend** : HTML5, CSS3, JavaScript ES6+
- **Base de données** : MySQL (optionnel)
- **API** : TeamCity REST API
- **Déploiement** : Docker-ready

## 📦 Installation

### Prérequis

- Python 3.12+
- MySQL (optionnel)
- Accès à TeamCity

### Installation locale

1. **Cloner le repository**
   ```bash
   git clone https://github.com/saleh-td/TeamCity_go2CAM.git
   cd TeamCity_go2CAM
   ```

2. **Créer l'environnement virtuel**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration**
   - Copier `.env.example` vers `.env`
   - Configurer les variables d'environnement TeamCity

5. **Lancer l'application**
   ```bash
   python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Accéder à l'application**
   - Dashboard : http://localhost:8000/static/index.html
   - Configuration : http://localhost:8000/static/config.html
   - API Docs : http://localhost:8000/docs

## 🔧 Configuration

### Variables d'environnement

Créer un fichier `.env` :

```env
# TeamCity Configuration
TEAMCITY_URL=http://192.168.0.48:8080
TEAMCITY_TOKEN=your_teamcity_token_here

# Database Configuration (optionnel)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=sentinel
```

### Configuration des builds

1. Accéder à http://localhost:8000/static/config.html
2. Sélectionner les builds à surveiller
3. Sauvegarder la configuration

## 📁 Structure du projet

```
teamcity_monitor/
├── api/                    # Backend FastAPI
│   ├── routes/            # Routes API
│   ├── services/          # Services métier
│   └── main.py           # Point d'entrée API
├── frontend/              # Interface utilisateur
│   ├── assets/           # CSS, JS, images
│   ├── index.html        # Dashboard principal
│   └── config.html       # Page de configuration
├── config/               # Configuration utilisateur
├── core/                 # Logique métier
└── README.md            # Documentation
```

## 🔌 API Endpoints

- `GET /api/builds` - Récupérer tous les builds
- `GET /api/agents` - Récupérer les agents
- `GET /api/config` - Récupérer la configuration
- `POST /api/builds/tree/selection` - Sauvegarder la sélection

## 🚀 Déploiement

### Docker

```bash
docker build -t teamcity-monitor .
docker run -p 8000:8000 teamcity-monitor
```

### Production

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 👥 Auteurs

- **Saleh** - *Développement initial* - [saleh-td](https://github.com/saleh-td)

## 🙏 Remerciements

- TeamCity pour l'API REST
- FastAPI pour le framework backend
- Tous les contributeurs du projet 