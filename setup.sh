#!/bin/bash
# Script d'installation automatique TeamCity Monitor

echo "🚀 Configuration automatique de TeamCity Monitor"
echo "================================================"

# 1. Créer l'environnement virtuel
echo "📦 Création de l'environnement virtuel..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de la création du venv"
    exit 1
fi

# 2. Activer l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# 3. Mettre à jour pip
echo "⬆️  Mise à jour de pip..."
pip install --upgrade pip

# 4. Installer les dépendances
echo "📚 Installation des dépendances..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de l'installation des dépendances"
    exit 1
fi

# 5. Créer le fichier .env
echo "⚙️  Création du fichier .env..."
cat > .env << 'EOF'
# TeamCity Configuration
TEAMCITY_URL=http://192.168.0.48:8080
TEAMCITY_TOKEN=eyJ0eXAiOiAiVENWMiJ9.MC0tbDRZbmFORExVRHhUTFhyakVYdjdidlIw.YzQxYzRmNzYtN2E3OC00ZWExLWEwOTQtYzUwMzcxNmI0NmYw

# Database Configuration (optionnel)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=Lpmdlp123
DB_NAME=sentinel

# Application Configuration
DEBUG=true
LOG_LEVEL=INFO
EOF

# 6. Créer un script d'activation automatique
echo "🔄 Création du script d'activation automatique..."
cat > activate.sh << 'EOF'
#!/bin/bash
# Script d'activation automatique de l'environnement virtuel

if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Environnement virtuel activé"
    echo "🚀 Pour démarrer le serveur: python start_server.py"
    echo "📊 Dashboard: http://localhost:8000/static/index.html"
    echo "⚙️  Config: http://localhost:8000/static/config.html"
else
    echo "❌ Environnement virtuel non trouvé. Exécutez d'abord: ./setup.sh"
fi
EOF

chmod +x activate.sh

# 7. Modifier le .bashrc pour activation automatique (optionnel)
echo "🔧 Configuration de l'activation automatique..."
if [ -f ~/.bashrc ]; then
    # Ajouter l'alias pour ce projet
    if ! grep -q "alias teamcity-activate" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# TeamCity Monitor - Activation automatique" >> ~/.bashrc
        echo "alias teamcity-activate='cd $(pwd) && source venv/bin/activate'" >> ~/.bashrc
        echo "📝 Alias 'teamcity-activate' ajouté à ~/.bashrc"
    fi
fi

echo ""
echo "✅ Installation terminée avec succès !"
echo ""
echo "🎯 Prochaines étapes :"
echo "   1. source venv/bin/activate    # Activer l'environnement"
echo "   2. python start_server.py      # Démarrer le serveur"
echo "   3. Ouvrir: http://localhost:8000/static/index.html"
echo ""
echo "💡 Pour la prochaine fois :"
echo "   - Utilise: ./activate.sh       # Activation rapide"
echo "   - Ou: teamcity-activate        # Depuis n'importe où"
echo ""