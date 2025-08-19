#!/bin/bash
# Script de démarrage rapide TeamCity Monitor

echo "🚀 Démarrage de TeamCity Monitor"

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "❌ Environnement virtuel non trouvé"
    echo "💡 Exécutez d'abord: ./setup.sh"
    exit 1
fi

# Activer l'environnement virtuel
source venv/bin/activate

# Vérifier si les dépendances sont installées
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dépendances manquantes"
    echo "💡 Exécutez d'abord: ./setup.sh"
    exit 1
fi

# Vérifier si le fichier .env existe
if [ ! -f ".env" ]; then
    echo "❌ Fichier .env manquant"
    echo "💡 Exécutez d'abord: ./setup.sh"
    exit 1
fi

echo "✅ Environnement prêt"
echo "🌐 Démarrage du serveur sur http://localhost:8000"
echo ""

# Démarrer le serveur
python start_server.py