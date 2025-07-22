#!/usr/bin/env python3
"""
Script de diagnostic pour comprendre la différence entre l'ancien et le nouveau système
dans la récupération des builds.
"""

import requests
import xml.etree.ElementTree as ET
import json
from typing import List, Dict, Any

# Configuration TeamCity
TEAMCITY_URL = 'http://192.168.0.48:8080'
TEAMCITY_TOKEN = 'eyJ0eXAiOiAiVENWMiJ9.MC0tbDRZbmFORExVRHhUTFhyakVYdjdidlIw.YzQxYzRmNzYtN2E3OC00ZWExLWEwOTQtYzUwMzcxNmI0NmYw'

def test_different_approaches():
    """
    Teste différentes approches pour récupérer les builds
    """
    print("🔍 DIAGNOSTIC DES BUILDS RÉCUPÉRÉS")
    print("=" * 60)
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }
    
    # 1. Approche actuelle (sans limite)
    print("\n1. APPROCHE ACTUELLE (sans limite)")
    try:
        url = f"{TEAMCITY_URL}/app/rest/builds?fields=build(id,buildTypeId,number,status,state,webUrl,buildType(id,name,projectName))"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            builds = root.findall('build')
            print(f"   Builds récupérés: {len(builds)}")
        else:
            print(f"   Erreur: {response.status_code}")
    except Exception as e:
        print(f"   Erreur: {e}")
    
    # 2. Approche avec limite (comme ancien système)
    print("\n2. APPROCHE AVEC LIMITE (count=50)")
    try:
        url = f"{TEAMCITY_URL}/app/rest/builds?locator=count:50&fields=build(id,buildTypeId,number,status,state,webUrl,buildType(id,name,projectName))"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            builds = root.findall('build')
            print(f"   Builds récupérés: {len(builds)}")
        else:
            print(f"   Erreur: {response.status_code}")
    except Exception as e:
        print(f"   Erreur: {e}")
    
    # 3. Approche avec buildTypes puis dernier build de chaque
    print("\n3. APPROCHE BUILDTYPES + DERNIER BUILD")
    try:
        # D'abord récupérer tous les buildTypes
        url = f"{TEAMCITY_URL}/app/rest/buildTypes"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            buildtypes = root.findall('buildType')
            print(f"   BuildTypes trouvés: {len(buildtypes)}")
            
            # Récupérer le dernier build de chaque buildType
            builds_count = 0
            for buildtype in buildtypes[:39]:  # Limiter à 39 pour tester
                buildtype_id = buildtype.attrib.get('id')
                try:
                    build_url = f"{TEAMCITY_URL}/app/rest/builds?locator=buildType:{buildtype_id},count:1"
                    build_response = requests.get(build_url, headers=headers, timeout=5)
                    if build_response.status_code == 200:
                        build_root = ET.fromstring(build_response.text)
                        if build_root.findall('build'):
                            builds_count += 1
                except:
                    pass
            
            print(f"   Builds avec cette approche: {builds_count}")
        else:
            print(f"   Erreur: {response.status_code}")
    except Exception as e:
        print(f"   Erreur: {e}")
    
    # 4. Test avec différentes limites
    print("\n4. TEST AVEC DIFFÉRENTES LIMITES")
    for limit in [20, 30, 39, 40, 50]:
        try:
            url = f"{TEAMCITY_URL}/app/rest/builds?locator=count:{limit}&fields=build(id,buildTypeId,number,status,state,webUrl,buildType(id,name,projectName))"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                builds = root.findall('build')
                
                # Compter les buildTypes uniques
                unique_buildtypes = set()
                for build in builds:
                    buildtype_id = build.attrib.get('buildTypeId')
                    if buildtype_id:
                        unique_buildtypes.add(buildtype_id)
                
                print(f"   Limite {limit}: {len(builds)} builds, {len(unique_buildtypes)} buildTypes uniques")
            else:
                print(f"   Limite {limit}: Erreur {response.status_code}")
        except Exception as e:
            print(f"   Limite {limit}: Erreur {e}")
    
    print(f"\n🎯 OBJECTIF: Trouver la limite qui donne exactement 39 builds uniques")
    print(f"   (comme dans l'ancien système PHP)")

def test_classification_logic():
    """
    Teste la logique de classification actuelle
    """
    print(f"\n🔄 TEST DE LA LOGIQUE DE CLASSIFICATION")
    print("=" * 60)
    
    # Simuler l'API locale
    try:
        response = requests.get("http://localhost:8000/api/builds/classified", timeout=10)
        if response.status_code == 200:
            data = response.json()
            columns = data.get('columns', {})
            total_builds = data.get('total_builds', 0)
            
            print(f"   Total builds récupérés: {total_builds}")
            
            # Compter les builds dans chaque colonne
            for col_name, col_data in columns.items():
                if isinstance(col_data, dict):
                    build_count = 0
                    for project_builds in col_data.values():
                        if isinstance(project_builds, list):
                            build_count += len(project_builds)
                    print(f"   Colonne '{col_name}': {build_count} builds")
                    
        else:
            print(f"   Erreur API: {response.status_code}")
    except Exception as e:
        print(f"   Erreur: {e}")

if __name__ == "__main__":
    test_different_approaches()
    test_classification_logic() 