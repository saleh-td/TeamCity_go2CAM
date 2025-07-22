#!/usr/bin/env python3
"""
Script simple pour tester la correction du problème d'incohérence des builds.
"""

import sys
import os
import asyncio
import aiohttp

# Ajouter le répertoire parent au PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from teamcity_monitor.api.services.teamcity_fetcher import fetch_teamcity_builds_alternative

async def test_correction():
    print("🔧 TEST DE LA CORRECTION DES BUILDS")
    print("=" * 50)
    
    # 1. Test de la nouvelle logique
    print("\n1. TEST NOUVELLE LOGIQUE (PHP Compatible)")
    try:
        # Exécuter la fonction corrigée
        builds = await asyncio.get_event_loop().run_in_executor(
            None, fetch_teamcity_builds_alternative
        )
        print(f"   ✅ Builds récupérés: {len(builds)}")
        
        # Afficher quelques exemples
        if builds:
            print(f"\n   📋 Premiers builds:")
            for i, build in enumerate(builds[:5]):
                print(f"      {i+1}. {build.get('name', 'N/A')} ({build.get('buildTypeId', 'N/A')})")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # 2. Test de l'API locale (force refresh pour vider le cache)
    print("\n2. TEST API LOCALE (avec cache vidé)")
    try:
        async with aiohttp.ClientSession() as session:
            # Vider le cache d'abord
            async with session.get("http://localhost:8000/api/teamcity/builds/force-refresh") as response:
                if response.status == 200:
                    data = await response.json()
                    builds_count = data.get('count', 0)
                    print(f"   ✅ Cache vidé et builds récupérés: {builds_count}")
                else:
                    print(f"   ⚠️  Impossible de vider le cache: {response.status}")
            
            # Tester l'endpoint principal
            async with session.get("http://localhost:8000/api/builds") as response:
                if response.status == 200:
                    data = await response.json()
                    builds = data.get('builds', [])
                    print(f"   ✅ Endpoint /api/builds: {len(builds)} builds")
                else:
                    print(f"   ❌ Erreur endpoint: {response.status}")
                    
    except Exception as e:
        print(f"   ⚠️  API locale non accessible: {e}")
    
    print(f"\n🎯 OBJECTIF: Afficher exactement 39 builds (comme l'ancien système PHP)")
    print("   Si le nombre est différent, vérifier la configuration TeamCity")

if __name__ == "__main__":
    asyncio.run(test_correction()) 