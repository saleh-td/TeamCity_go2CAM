#!/usr/bin/env python3
"""
Script de démarrage du serveur TeamCity Monitor avec test de la correction.
"""

import subprocess
import sys
import os
import time
import requests
from datetime import datetime

def test_builds_count():
    """Teste le nombre de builds après la correction."""
    try:
        print("\n🔍 Test du nombre de builds...")
        response = requests.get("http://localhost:8000/api/builds", timeout=10)
        if response.status_code == 200:
            data = response.json()
            builds = data.get('builds', [])
            print(f"   ✅ Builds récupérés: {len(builds)}")
            
            if len(builds) == 39:
                print("   🎯 SUCCÈS: Exactement 39 builds comme l'ancien système PHP!")
            elif len(builds) < 50:
                print(f"   ⚠️  Proche de l'objectif: {len(builds)} builds (objectif: 39)")
            else:
                print(f"   ❌ Encore trop de builds: {len(builds)} (objectif: 39)")
            
            return len(builds)
        else:
            print(f"   ❌ Erreur API: {response.status_code}")
            return 0
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")
        return 0

def start_server():
    """Démarre le serveur avec uvicorn."""
    print("🚀 DÉMARRAGE DU SERVEUR TEAMCITY MONITOR")
    print("=" * 50)
    print(f"Timestamp: {datetime.now()}")
    print("URL: http://localhost:8000")
    print("Documentation API: http://localhost:8000/docs")
    print("Dashboard: http://localhost:8000/static/index.html")
    print()
    
    # Installer pymysql si nécessaire
    try:
        import pymysql
        print("✅ Module pymysql trouvé")
    except ImportError:
        print("⚠️  Installation de pymysql...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pymysql==1.1.1"], check=True)
        print("✅ pymysql installé")
    
    # Démarrer le serveur
    print("\n🔧 Démarrage du serveur FastAPI...")
    print("   (Le serveur testera automatiquement la correction après 5 secondes)")
    print()
    
    # Lancer uvicorn en arrière-plan pour pouvoir tester
    try:
        # Démarrer le serveur dans un sous-processus
        server_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "api.main:app", 
            "--reload", 
            "--host", "localhost", 
            "--port", "8000"
        ], cwd=os.path.dirname(__file__))
        
        # Attendre que le serveur démarre
        print("⏳ Attente du démarrage du serveur...")
        time.sleep(5)
        
        # Tester la correction
        builds_count = test_builds_count()
        
        if builds_count > 0:
            print(f"\n🎉 SERVEUR DÉMARRÉ AVEC SUCCÈS!")
            print(f"   Builds disponibles: {builds_count}")
            print(f"   Correction appliquée: {'✅ OUI' if builds_count <= 50 else '❌ NON'}")
        
        print(f"\n📝 POUR TESTER:")
        print(f"   1. Ouvre http://localhost:8000/api/builds")
        print(f"   2. Compare avec l'ancien système PHP")
        print(f"   3. Vérifier l'absence de doublons")
        print(f"\n⚠️  Appuie sur Ctrl+C pour arrêter le serveur")
        
        # Garder le serveur en marche
        try:
            server_process.wait()
        except KeyboardInterrupt:
            print(f"\n🛑 Arrêt du serveur...")
            server_process.terminate()
            server_process.wait()
            print("✅ Serveur arrêté")
            
    except FileNotFoundError:
        print("❌ uvicorn non trouvé. Installe-le avec: pip install uvicorn")
    except Exception as e:
        print(f"❌ Erreur de démarrage: {e}")

if __name__ == "__main__":
    start_server() 