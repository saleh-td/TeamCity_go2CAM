#!/usr/bin/env python3
import sys
import os
import asyncio
import aiohttp
from datetime import datetime

# Ajouter le répertoire parent au PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from teamcity_monitor.api.services.teamcity_fetcher import fetch_teamcity_builds_alternative, TEAMCITY_URL, TEAMCITY_TOKEN

async def verify_teamcity_source():
    print("=== VÉRIFICATION SOURCE DES BUILDS ===")
    print(f"Timestamp: {datetime.now()}")
    print(f"TeamCity URL: {TEAMCITY_URL}")
    print(f"TeamCity Token: {TEAMCITY_TOKEN[:20]}..." if TEAMCITY_TOKEN else "PAS DE TOKEN")
    print()
    
    # 1. Test direct de l'API TeamCity
    print("1. TEST DIRECT API TEAMCITY")
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {TEAMCITY_TOKEN}',
                'Accept': 'application/json'
            }
            
            url = f"{TEAMCITY_URL}/app/rest/builds?locator=count:1000"
            async with session.get(url, headers=headers) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    count = data.get('count', 0)
                    print(f"Builds depuis API TeamCity: {count}")
                else:
                    print(f"Erreur API: {await response.text()}")
    except Exception as e:
        print(f"Erreur test direct: {e}")
    
    print()
    
    # 2. Test via notre service
    print("2. TEST VIA NOTRE SERVICE")
    try:
        builds = await asyncio.get_event_loop().run_in_executor(
            None, fetch_teamcity_builds_alternative
        )
        print(f"Builds via notre service: {len(builds)}")
        
        # Afficher quelques exemples
        if builds:
            print("\nPremiers builds:")
            for i, build in enumerate(builds[:5]):
                print(f"  {i+1}. {build.get('buildType', {}).get('name', 'N/A')}")
        
    except Exception as e:
        print(f"Erreur service: {e}")
    
    print()
    
    # 3. Test des endpoints API locaux
    print("3. TEST ENDPOINTS API LOCAUX")
    try:
        async with aiohttp.ClientSession() as session:
            # Test endpoint builds
            async with session.get("http://localhost:8000/api/builds") as response:
                if response.status == 200:
                    data = await response.json()
                    builds = data.get('builds', [])
                    print(f"Endpoint /api/builds: {len(builds)} builds")
                else:
                    print(f"Erreur endpoint builds: {response.status}")
            
            # Test endpoint teamcity direct
            async with session.get("http://localhost:8000/api/teamcity/builds") as response:
                if response.status == 200:
                    data = await response.json()
                    builds = data.get('builds', [])
                    cached = data.get('cached', False)
                    print(f"Endpoint /api/teamcity/builds: {len(builds)} builds (cached: {cached})")
                else:
                    print(f"Erreur endpoint teamcity: {response.status}")
                    
            # Test status
            async with session.get("http://localhost:8000/api/teamcity/status") as response:
                if response.status == 200:
                    data = await response.json()
                    cache_info = data.get('cache', {})
                    print(f"Cache status: {cache_info.get('builds_count', 0)} builds en cache")
                else:
                    print(f"Erreur status: {response.status}")
                    
    except Exception as e:
        print(f"Erreur endpoints: {e}")

if __name__ == "__main__":
    asyncio.run(verify_teamcity_source()) 