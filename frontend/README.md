# TeamCity Dashboard Frontend

## 🚀 Installation et Configuration

### 1. Installation des dépendances
```bash
cd teamcity_monitor/frontend
npm install
```

### 2. Génération du CSS
```bash
# Pour développement (mode watch)
npm run dev

# Pour production (minifié)
npm run build
```

### 3. Lancement du serveur
```bash
# Option 1: Serveur Python simple
npm run serve

# Option 2: Live Server (si vous avez une extension VS Code)
# Clic droit sur index.html > "Open with Live Server"
```

## 📁 Structure du Projet

```
frontend/
├── assets/
│   ├── css/
│   │   ├── input.css      # CSS source avec Tailwind
│   │   └── output.css     # CSS généré (auto-généré)
│   └── js/
│       ├── dashboard.js   # Logic du dashboard principal
│       └── parameters.js  # Logic de la page paramètres
├── index.html            # Page dashboard principale
├── parameters.html       # Page de configuration
├── package.json          # Dépendances Node.js
├── tailwind.config.js    # Configuration Tailwind
└── README.md            # Ce fichier
```

## 🔧 Fonctionnalités

### Dashboard Principal (`index.html`)
- **Affichage optimisé écran mural** : Pas de scroll vertical
- **Colonnes dynamiques** : Seules les colonnes avec builds apparaissent
- **Classification automatique** : 612, New, 611, Autres
- **Actualisation automatique** : Configurable via paramètres
- **Design responsive** : S'adapte à différentes tailles d'écran

### Page Paramètres (`parameters.html`)
- **Configuration colonnes** : Noms et patterns de filtrage
- **Intervalle refresh** : Entre 10 et 3600 secondes
- **Test de connexion** : Vérification API
- **Sauvegarde persistante** : Base de données MySQL

### Résolution du Problème des Colonnes Vides
Le JavaScript filtre automatiquement les colonnes vides. Seules les colonnes contenant des builds sont affichées, évitant les messages "Aucun build".

## 🎨 Personnalisation

### Couleurs du thème (dans `tailwind.config.js`)
- **Arrière-plan** : Noir et gris sombre
- **Accents** : Bleu, Vert, Rouge, Orange
- **Texte** : Blanc et gris adaptés au thème sombre

### Animations et Effets
- **Pulse** : Builds en cours
- **Hover** : Cartes et boutons
- **Glass effect** : Header et notifications

## 🔌 API Endpoints

Le frontend communique avec :
- `http://localhost:8000/api/builds` - Liste des builds
- `http://localhost:8000/api/parameters` - Configuration
- `http://localhost:8000/api/status?id=buildId` - Status spécifique

## 📱 Optimisations Écran Mural

1. **Hauteur fixe** : `height: calc(100vh - 280px)` pour les builds
2. **Pas de scroll global** : `overflow-hidden` sur le body
3. **Scroll localisé** : Seulement dans les colonnes si nécessaire
4. **Grid responsive** : S'adapte au nombre de colonnes
5. **Masquage intelligent** : Colonnes vides cachées

## 🔄 Scripts Disponibles

```bash
npm run dev      # CSS watch mode pour développement
npm run build    # CSS minifié pour production  
npm run serve    # Serveur Python sur port 8080
```

## 🔮 Prochaines Étapes

1. **Démarrer le backend API** (dans `../api/`)
2. **Générer le CSS** avec `npm run dev`
3. **Ouvrir** `index.html` dans le navigateur
4. **Configurer** via la page paramètres si nécessaire

---

**Note importante** : Le CSS doit être généré avec Tailwind avant la première utilisation. Utilisez `npm run dev` pour le mode développement ou `npm run build` pour la production. 