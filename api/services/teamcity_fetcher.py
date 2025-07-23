import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Configuration TeamCity (depuis ConnectionApi.php)
TEAMCITY_URL = os.getenv('TEAMCITY_URL', 'http://192.168.0.48:8080')
TEAMCITY_TOKEN = os.getenv('TEAMCITY_TOKEN', 'eyJ0eXAiOiAiVENWMiJ9.MC0tbDRZbmFORExVRHhUTFhyakVYdjdidlIw.YzQxYzRmNzYtN2E3OC00ZWExLWEwOTQtYzUwMzcxNmI0NmYw')


DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'Lpmdlp123')
DB_NAME = os.getenv('DB_NAME', 'sentinel')

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def fetch_teamcity_builds_alternative() -> List[Dict[str, Any]]:
    """
    Reproduit EXACTEMENT la logique PHP de récupération des builds.
    Corrige le problème d'incohérence entre l'ancien système (39 builds) et le nouveau (70+ builds).
    
    IMPORTANT: Cette fonction utilise la même URL que l'ancien système PHP (/app/rest/builds)
    mais avec les champs nécessaires pour récupérer les noms des builds.
    """
    # Vérifier si TeamCity est configuré
    if not TEAMCITY_TOKEN or TEAMCITY_URL == 'http://localhost:8111':
        logger.warning("TeamCity non configuré")
        return []
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

    try:
        # 🎯 RÉCUPÉRER LES BUILDS EN COURS ET FINIS
        # URL pour récupérer les builds en cours ET les builds finis récents
        url = f"{TEAMCITY_URL}/app/rest/builds?locator=running:any,failedToStart:any,count:50&fields=build(id,buildTypeId,number,status,state,webUrl,buildType(id,name,projectName))"
        
        logger.info(f"Récupération builds (logique PHP: 39 builds max): {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        builds = []
        root = ET.fromstring(response.text)

        # Traiter chaque build EXACTEMENT comme dans api/index.php
        builds = []
        unique_buildtypes = set()  # Pour éviter les doublons
        
        for build_elem in root.findall('build'):
            build_id = build_elem.attrib.get('id', '')
            buildtype_id = build_elem.attrib.get('buildTypeId', '')
            
            # Éviter les doublons de buildTypes (prendre seulement le plus récent)
            if buildtype_id in unique_buildtypes:
                continue
            unique_buildtypes.add(buildtype_id)
            
            # Récupérer le nom du build depuis l'élément buildType
            buildtype_elem = build_elem.find('buildType')
            if buildtype_elem is not None:
                buildtype_name = buildtype_elem.attrib.get('name', '')
                project_name = buildtype_elem.attrib.get('projectName', '')
            else:
                buildtype_name = buildtype_id  # Fallback au buildTypeId si pas de nom
                project_name = ''
            
            # Construire l'URL complète pour TeamCity
            web_url = build_elem.attrib.get('webUrl', '')
            if web_url and not web_url.startswith('http'):
                # Si l'URL est relative, la rendre absolue
                web_url = f"{TEAMCITY_URL}{web_url}"
            
            build_data = {
                'id': buildtype_id,
                'buildTypeId': buildtype_id,
                'name': buildtype_name,
                'projectName': project_name,
                'webUrl': web_url,
                'status': build_elem.attrib.get('status', 'UNKNOWN'),
                'state': build_elem.attrib.get('state', 'finished'),
                'number': build_elem.attrib.get('number', '')
            }
            builds.append(build_data)

        logger.info(f"Builds récupérés (logique PHP compatible): {len(builds)} builds uniques")
        return builds

    except Exception as e:
        logger.error(f"Erreur TeamCity (logique PHP): {str(e)}")
        return []

def fetch_all_teamcity_builds() -> List[Dict[str, Any]]:
    """
    Récupère TOUS les builds TeamCity sans AUCUNE limitation pour la page de configuration.
    Utilise l'API buildTypes pour récupérer tous les types de builds disponibles.
    """
    # Vérifier si TeamCity est configuré
    if not TEAMCITY_TOKEN or TEAMCITY_URL == 'http://localhost:8111':
        print("WARNING: TeamCity non configuré")
        return []
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

    try:
        # Récupérer TOUS les buildTypes SANS AUCUNE LIMITE
        # Cela nous donne tous les types de builds disponibles dans TeamCity
        url = f"{TEAMCITY_URL}/app/rest/buildTypes?fields=buildType(id,name,projectName,project(id,name))&count=10000"
        
        print(f"=== RÉCUPÉRATION COMPLÈTE TEAMCITY ===")
        print(f"URL: {url}")
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        builds = []
        root = ET.fromstring(response.text)

        print(f"Réponse XML reçue, recherche des buildType...")
        
        for buildtype_elem in root.findall('buildType'):
            buildtype_id = buildtype_elem.attrib.get('id', '')
            buildtype_name = buildtype_elem.attrib.get('name', '')
            
            # Récupérer le projet parent
            project_elem = buildtype_elem.find('project')
            if project_elem is not None:
                project_name = project_elem.attrib.get('name', '')
            else:
                project_name = ''
            
            print(f"BuildType trouvé: {buildtype_id} -> {buildtype_name} (Projet: {project_name})")
            
            # Récupérer le statut du build le plus récent pour ce buildType
            try:
                status_url = f"{TEAMCITY_URL}/app/rest/buildTypes/id:{buildtype_id}/builds?locator=running:any,failedToStart:any,count:1&fields=build(status,state,webUrl)"
                status_response = requests.get(status_url, headers=headers, timeout=5)
                if status_response.status_code == 200:
                    status_root = ET.fromstring(status_response.text)
                    latest_build = status_root.find('build')
                    if latest_build is not None:
                        status = latest_build.attrib.get('status', 'UNKNOWN')
                        state = latest_build.attrib.get('state', 'finished')
                        web_url = latest_build.attrib.get('webUrl', '')
                    else:
                        status = 'UNKNOWN'
                        state = 'finished'
                        web_url = ''
                else:
                    status = 'UNKNOWN'
                    state = 'finished'
                    web_url = ''
            except Exception as e:
                print(f"Impossible de récupérer le statut pour {buildtype_name}: {e}")
                status = 'UNKNOWN'
                state = 'finished'
                web_url = ''
            
            # Construire l'URL complète pour TeamCity
            if web_url and not web_url.startswith('http'):
                # Si l'URL est relative, la rendre absolue
                web_url = f"{TEAMCITY_URL}{web_url}"
            
            build_data = {
                'id': buildtype_id,
                'buildTypeId': buildtype_id,
                'name': buildtype_name,
                'projectName': project_name,
                'webUrl': web_url,
                'status': status,
                'state': state,
                'number': '1'  # Placeholder
            }
            builds.append(build_data)

        print(f"=== RÉSULTAT RÉCUPÉRATION ===")
        print(f"TOTAL buildTypes récupérés: {len(builds)}")
        
        # Afficher tous les projets uniques trouvés
        projects = set()
        for build in builds:
            if build['projectName']:
                projects.add(build['projectName'])
        
        print(f"Projets uniques trouvés ({len(projects)}):")
        for project in sorted(projects):
            print(f"  - {project}")
        
        return builds

    except Exception as e:
        print(f"ERREUR TeamCity (tous les builds): {str(e)}")
        return []

def fetch_all_teamcity_projects() -> List[Dict[str, Any]]:
    """
    Récupère TOUS les projets et sous-projets TeamCity pour avoir la structure complète.
    Inclut même les projets sans builds pour reproduire exactement l'arborescence TeamCity.
    """
    # Vérifier si TeamCity est configuré
    if not TEAMCITY_TOKEN or TEAMCITY_URL == 'http://localhost:8111':
        print("WARNING: TeamCity non configuré")
        return []
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

    try:
        print(f"=== RÉCUPÉRATION STRUCTURE COMPLÈTE TEAMCITY ===")
        
        # Récupérer TOUS les projets (structure hiérarchique)
        projects_url = f"{TEAMCITY_URL}/app/rest/projects?fields=project(id,name,parentProject(id,name))&count=10000"
        print(f"URL projets: {projects_url}")
        
        response = requests.get(projects_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        projects_data = []
        root = ET.fromstring(response.text)
        
        print(f"Réponse XML projets reçue, recherche des projets...")
        
        for project_elem in root.findall('project'):
            project_id = project_elem.attrib.get('id', '')
            project_name = project_elem.attrib.get('name', '')
            
            # Récupérer le projet parent
            parent_elem = project_elem.find('parentProject')
            parent_name = parent_elem.attrib.get('name', '') if parent_elem is not None else ''
            
            print(f"Projet trouvé: {project_id} -> {project_name} (Parent: {parent_name})")
            
            # Construire le chemin complet du projet
            if parent_name:
                full_path = f"{parent_name} / {project_name}"
            else:
                full_path = project_name
            
            project_data = {
                'id': project_id,
                'name': project_name,
                'parentName': parent_name,
                'fullPath': full_path,
                'type': 'project'
            }
            projects_data.append(project_data)
        
        # Récupérer TOUS les buildTypes pour avoir les builds
        buildtypes_url = f"{TEAMCITY_URL}/app/rest/buildTypes?fields=buildType(id,name,projectName,project(id,name))&count=10000"
        print(f"URL buildTypes: {buildtypes_url}")
        
        response = requests.get(buildtypes_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        buildtypes_data = []
        root = ET.fromstring(response.text)
        
        print(f"Réponse XML buildTypes reçue, recherche des buildTypes...")
        
        for buildtype_elem in root.findall('buildType'):
            buildtype_id = buildtype_elem.attrib.get('id', '')
            buildtype_name = buildtype_elem.attrib.get('name', '')
            project_name = buildtype_elem.attrib.get('projectName', '')
            
            print(f"BuildType trouvé: {buildtype_id} -> {buildtype_name} (Projet: {project_name})")
            
            # Récupérer le statut du build le plus récent
            try:
                status_url = f"{TEAMCITY_URL}/app/rest/buildTypes/id:{buildtype_id}/builds?locator=count:1&fields=build(status,state,webUrl)"
                status_response = requests.get(status_url, headers=headers, timeout=5)
                if status_response.status_code == 200:
                    status_root = ET.fromstring(status_response.text)
                    latest_build = status_root.find('build')
                    if latest_build is not None:
                        status = latest_build.attrib.get('status', 'UNKNOWN')
                        state = latest_build.attrib.get('state', 'finished')
                        web_url = latest_build.attrib.get('webUrl', '')
                    else:
                        status = 'UNKNOWN'
                        state = 'finished'
                        web_url = ''
                else:
                    status = 'UNKNOWN'
                    state = 'finished'
                    web_url = ''
            except Exception as e:
                print(f"Impossible de récupérer le statut pour {buildtype_name}: {e}")
                status = 'UNKNOWN'
                state = 'finished'
                web_url = ''
            
            buildtype_data = {
                'id': buildtype_id,
                'buildTypeId': buildtype_id,
                'name': buildtype_name,
                'projectName': project_name,
                'webUrl': web_url,
                'status': status,
                'state': state,
                'type': 'buildtype'
            }
            buildtypes_data.append(buildtype_data)
        
        print(f"=== RÉSULTAT RÉCUPÉRATION COMPLÈTE ===")
        print(f"TOTAL projets récupérés: {len(projects_data)}")
        print(f"TOTAL buildTypes récupérés: {len(buildtypes_data)}")
        
        # Afficher tous les projets uniques trouvés
        all_project_paths = set()
        for project in projects_data:
            all_project_paths.add(project['fullPath'])
        for buildtype in buildtypes_data:
            if buildtype['projectName']:
                all_project_paths.add(buildtype['projectName'])
        
        print(f"Chemins de projets uniques trouvés ({len(all_project_paths)}):")
        for path in sorted(all_project_paths):
            print(f"  - {path}")
        
        # Retourner les deux types de données
        return {
            'projects': projects_data,
            'buildtypes': buildtypes_data,
            'all_project_paths': list(all_project_paths)
        }

    except Exception as e:
        print(f"ERREUR TeamCity (structure complète): {str(e)}")
        return {'projects': [], 'buildtypes': [], 'all_project_paths': []}

def filter_active_projects(projects_data, buildtypes_data):
    """
    Filtre les projets pour ne garder que les projets principaux actifs.
    Exclut les projets archivés, inactifs et les sous-projets.
    """
    # Créer un set des noms de projets principaux qui ont des buildTypes actifs
    active_project_names = set()
    for buildtype in buildtypes_data:
        if buildtype['projectName']:
            # Extraire le projet principal (premier niveau)
            project_parts = buildtype['projectName'].split(' / ')
            if project_parts:
                main_project = project_parts[0]
                active_project_names.add(main_project)
    
    # Filtrer les projets principaux uniquement
    filtered_projects = []
    for project in projects_data:
        if project['name'] in active_project_names:
            filtered_projects.append(project)
        else:
            print(f"Projet principal sans buildTypes actifs ignoré: {project['name']}")
    
    print(f"Projets principaux actifs: {len(filtered_projects)}/{len(projects_data)}")
    return filtered_projects, active_project_names

def fetch_all_teamcity_projects_optimized() -> Dict[str, Any]:
    """
    Version optimisée qui ne fait que 2 appels API au total.
    Récupère TOUS les projets et buildTypes sans les statuts individuels.
    """
    # Vérifier si TeamCity est configuré
    if not TEAMCITY_TOKEN or TEAMCITY_URL == 'http://localhost:8111':
        print("WARNING: TeamCity non configuré")
        return {'projects': [], 'buildtypes': [], 'all_project_paths': []}
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

    try:
        print(f"=== RÉCUPÉRATION OPTIMISÉE TEAMCITY ===")
        
        # 1. Récupérer TOUS les projets (structure hiérarchique)
        projects_url = f"{TEAMCITY_URL}/app/rest/projects?fields=project(id,name,parentProject(id,name))&count=10000"
        print(f"URL projets: {projects_url}")
        
        response = requests.get(projects_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        projects_data = []
        root = ET.fromstring(response.text)
        
        print(f"Réponse XML projets reçue, recherche des projets...")
        
        for project_elem in root.findall('project'):
            project_id = project_elem.attrib.get('id', '')
            project_name = project_elem.attrib.get('name', '')
            
            # Récupérer le projet parent
            parent_elem = project_elem.find('parentProject')
            parent_name = parent_elem.attrib.get('name', '') if parent_elem is not None else ''
            
            # Filtrer les projets archivés
            is_archived = project_elem.attrib.get('archived', 'false').lower() == 'true'
            if is_archived:
                print(f"Projet archivé ignoré: {project_id} -> {project_name}")
                continue
                
            # Ignorer les projets racine
            if not project_name or project_name == '<Root project>' or project_name == 'Root project':
                print(f"Projet racine ignoré: {project_id} -> {project_name}")
                continue
            
            # Ne garder que les projets principaux (sans parent ou avec parent racine)
            if parent_name and parent_name not in ['<Root project>', 'Root project']:
                print(f"Projet sous-projet ignoré: {project_id} -> {project_name} (Parent: {parent_name})")
                continue
            
            # Filtrer pour ne garder que les 3 projets principaux actuels
            allowed_main_projects = ["GO2 Version 612", "GO2 Version New", "Web Services"]
            if project_name not in allowed_main_projects:
                print(f"Projet non autorisé ignoré: {project_id} -> {project_name}")
                continue
            
            print(f"Projet principal autorisé trouvé: {project_id} -> {project_name}")
            
            # Pour les projets principaux, utiliser le nom direct
            full_path = project_name
            
            project_data = {
                'id': project_id,
                'name': project_name,
                'parentName': parent_name,
                'fullPath': full_path,
                'type': 'project'
            }
            projects_data.append(project_data)
        
        # 2. Récupérer TOUS les buildTypes (sans les statuts individuels)
        buildtypes_url = f"{TEAMCITY_URL}/app/rest/buildTypes?fields=buildType(id,name,projectName,project(id,name))&count=10000"
        print(f"URL buildTypes: {buildtypes_url}")
        
        response = requests.get(buildtypes_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        buildtypes_data = []
        root = ET.fromstring(response.text)
        
        print(f"Réponse XML buildTypes reçue, recherche des buildTypes...")
        
        for buildtype_elem in root.findall('buildType'):
            buildtype_id = buildtype_elem.attrib.get('id', '')
            buildtype_name = buildtype_elem.attrib.get('name', '')
            project_name = buildtype_elem.attrib.get('projectName', '')
            
            # Filtrer les buildTypes archivés
            is_archived = buildtype_elem.attrib.get('archived', 'false').lower() == 'true'
            if is_archived:
                print(f"BuildType archivé ignoré: {buildtype_id} -> {buildtype_name}")
                continue
                
            # Ignorer les buildTypes sans nom ou de projets racine
            if not buildtype_name or not project_name or project_name == '<Root project>' or project_name == 'Root project':
                print(f"BuildType ignoré: {buildtype_id} -> {buildtype_name} (Projet: {project_name})")
                continue
            
            # Filtrer pour ne garder que les buildTypes des 3 projets principaux actuels
            allowed_main_projects = ["GO2 Version 612", "GO2 Version New", "Web Services"]
            project_parts = project_name.split(' / ')
            if project_parts and project_parts[0] not in allowed_main_projects:
                print(f"BuildType de projet non autorisé ignoré: {buildtype_id} -> {buildtype_name} (Projet: {project_name})")
                continue
            
            print(f"BuildType autorisé trouvé: {buildtype_id} -> {buildtype_name} (Projet: {project_name})")
            
            # Pas de récupération de statut individuel pour optimiser
            buildtype_data = {
                'id': buildtype_id,
                'buildTypeId': buildtype_id,
                'name': buildtype_name,
                'projectName': project_name,
                'webUrl': '',  # Sera rempli plus tard si nécessaire
                'status': 'UNKNOWN',  # Sera rempli plus tard si nécessaire
                'state': 'finished',  # Sera rempli plus tard si nécessaire
                'type': 'buildtype'
            }
            buildtypes_data.append(buildtype_data)
        
        print(f"=== RÉSULTAT RÉCUPÉRATION OPTIMISÉE ===")
        print(f"TOTAL projets récupérés: {len(projects_data)}")
        print(f"TOTAL buildTypes récupérés: {len(buildtypes_data)}")
        
        # Afficher tous les projets uniques trouvés
        all_project_paths = set()
        for project in projects_data:
            all_project_paths.add(project['fullPath'])
        for buildtype in buildtypes_data:
            if buildtype['projectName'] and buildtype['projectName'] != '<Root project>' and buildtype['projectName'] != 'Root project':
                all_project_paths.add(buildtype['projectName'])
        
        print(f"Chemins de projets uniques trouvés ({len(all_project_paths)}):")
        for path in sorted(all_project_paths):
            print(f"  - {path}")
        
        # Retourner les deux types de données
        return {
            'projects': projects_data,
            'buildtypes': buildtypes_data,
            'all_project_paths': list(all_project_paths)
        }

    except Exception as e:
        print(f"ERREUR TeamCity (optimisé): {str(e)}")
        return {'projects': [], 'buildtypes': [], 'all_project_paths': []}

def fetch_current_versions_buildtypes() -> Dict[str, Any]:
    """
    Version ultra-optimisée qui ne récupère QUE les buildTypes des versions actuelles.
    Fait seulement 1 appel API et filtre directement côté serveur.
    """
    # Vérifier si TeamCity est configuré
    if not TEAMCITY_TOKEN or TEAMCITY_URL == 'http://localhost:8111':
        print("WARNING: TeamCity non configuré")
        return {'buildtypes': [], 'all_project_paths': []}
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

    try:
        print(f"=== RÉCUPÉRATION ULTRA-OPTIMISÉE ===")
        
        # Récupérer TOUS les buildTypes en UN SEUL appel
        buildtypes_url = f"{TEAMCITY_URL}/app/rest/buildTypes?fields=buildType(id,name,projectName,project(id,name))&count=10000"
        print(f"URL buildTypes: {buildtypes_url}")
        
        response = requests.get(buildtypes_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        buildtypes_data = []
        root = ET.fromstring(response.text)
        
        print(f"Réponse XML buildTypes reçue, filtrage des versions actuelles...")
        
        # Filtrer directement les buildTypes des versions actuelles
        current_versions = ["GO2 Version 612", "GO2 Version New"]
        
        for buildtype_elem in root.findall('buildType'):
            buildtype_id = buildtype_elem.attrib.get('id', '')
            buildtype_name = buildtype_elem.attrib.get('name', '')
            project_name = buildtype_elem.attrib.get('projectName', '')
            
            # Vérifier si ce buildType appartient à une version actuelle
            is_current_version = False
            for version in current_versions:
                if version in project_name:
                    is_current_version = True
                    break
            
            if is_current_version:
                print(f"BuildType actuel trouvé: {buildtype_id} -> {buildtype_name} (Projet: {project_name})")
                
                buildtype_data = {
                    'id': buildtype_id,
                    'buildTypeId': buildtype_id,
                    'name': buildtype_name,
                    'projectName': project_name,
                    'webUrl': '',  # Sera rempli plus tard si nécessaire
                    'status': 'UNKNOWN',  # Sera rempli plus tard si nécessaire
                    'state': 'finished',  # Sera rempli plus tard si nécessaire
                    'type': 'buildtype'
                }
                buildtypes_data.append(buildtype_data)
        
        print(f"=== RÉSULTAT ULTRA-OPTIMISÉ ===")
        print(f"TOTAL buildTypes filtrés: {len(buildtypes_data)}")
        
        # Extraire les chemins de projets uniques
        all_project_paths = set()
        for buildtype in buildtypes_data:
            if buildtype['projectName']:
                all_project_paths.add(buildtype['projectName'])
        
        print(f"Chemins de projets uniques trouvés ({len(all_project_paths)}):")
        for path in sorted(all_project_paths):
            print(f"  - {path}")
        
        return {
            'buildtypes': buildtypes_data,
            'all_project_paths': list(all_project_paths)
        }

    except Exception as e:
        print(f"ERREUR TeamCity (ultra-optimisé): {str(e)}")
        return {'buildtypes': [], 'all_project_paths': []}

def fetch_selected_builds_status(selected_builds: List[str]) -> List[Dict[str, Any]]:
    """
    Récupère les statuts des builds sélectionnés de manière optimisée.
    Utilise une approche par lot pour éviter les appels individuels lents.
    """
    # Vérifier si TeamCity est configuré
    if not TEAMCITY_TOKEN or TEAMCITY_URL == 'http://localhost:8111':
        logger.warning("TeamCity non configuré")
        return []
    
    if not selected_builds:
        logger.warning("Aucun build sélectionné")
        return []
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

    try:
        builds = []
        
        # Récupérer les builds par groupes pour optimiser les performances
        # On récupère les builds récents pour chaque buildType sélectionné (incluant les builds en cours)
        for buildtype_id in selected_builds:
            try:
                # Vérifier d'abord si le buildType est archivé
                buildtype_url = f"{TEAMCITY_URL}/app/rest/buildTypes/id:{buildtype_id}"
                buildtype_response = requests.get(buildtype_url, headers=headers, timeout=5)
                
                if buildtype_response.status_code == 200:
                    buildtype_root = ET.fromstring(buildtype_response.text)
                    is_archived = buildtype_root.attrib.get('archived', 'false').lower() == 'true'
                    
                    if is_archived:
                        print(f"BuildType archivé ignoré: {buildtype_id}")
                        continue
                
                # URL optimisée : récupère les builds récents pour ce buildType (incluant les builds en cours)
                # Utilise la même logique que l'ancien système PHP : running:any,failedToStart:any
                url = f"{TEAMCITY_URL}/app/rest/builds?locator=buildType:{buildtype_id},running:any,failedToStart:any,count:5&fields=build(id,buildTypeId,number,status,state,webUrl,buildType(id,name,projectName))"
                

                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()

                root = ET.fromstring(response.text)
                build_elems = root.findall('build')
                
                if build_elems:
                    # DEBUG: Log tous les builds trouvés pour ce buildType
                    print(f"🔍 DEBUG - BuildType {buildtype_id}: {len(build_elems)} builds trouvés")
                    for i, build_elem in enumerate(build_elems):
                        build_id = build_elem.attrib.get('id', 'N/A')
                        build_status = build_elem.attrib.get('status', 'N/A')
                        build_state = build_elem.attrib.get('state', 'N/A')
                        print(f"  Build {i+1}: ID={build_id}, Status={build_status}, State={build_state}")
                    
                    # Chercher d'abord un build en cours, sinon prendre le plus récent
                    selected_build_elem = None
                    
                    # Priorité 1: Build en cours
                    for build_elem in build_elems:
                        state = build_elem.attrib.get('state', 'finished')
                        if state.lower() in ['running', 'building']:
                            selected_build_elem = build_elem
                            break
                    
                    # Priorité 2: Build le plus récent (premier de la liste)
                    if selected_build_elem is None:
                        selected_build_elem = build_elems[0]
                    
                    # Récupérer le nom du build depuis l'élément buildType
                    buildtype_elem = selected_build_elem.find('buildType')
                    if buildtype_elem is not None:
                        buildtype_name = buildtype_elem.attrib.get('name', '')
                        project_name = buildtype_elem.attrib.get('projectName', '')
                    else:
                        buildtype_name = buildtype_id
                        project_name = ''
                    
                    # Construire l'URL complète pour TeamCity
                    web_url = selected_build_elem.attrib.get('webUrl', '')
                    if web_url and not web_url.startswith('http'):
                        # Si l'URL est relative, la rendre absolue
                        web_url = f"{TEAMCITY_URL}{web_url}"
                    
                    build_data = {
                        'id': buildtype_id,
                        'buildTypeId': buildtype_id,
                        'name': buildtype_name,
                        'projectName': project_name,
                        'webUrl': web_url,
                        'status': selected_build_elem.attrib.get('status', 'UNKNOWN'),
                        'state': selected_build_elem.attrib.get('state', 'finished'),
                        'number': selected_build_elem.attrib.get('number', '')
                    }
                    builds.append(build_data)
                else:
                    # Si aucun build trouvé, créer un build avec statut UNKNOWN
                    build_data = {
                        'id': buildtype_id,
                        'buildTypeId': buildtype_id,
                        'name': buildtype_id,
                        'projectName': '',
                        'webUrl': '',
                        'status': 'UNKNOWN',
                        'state': 'finished',
                        'number': ''
                    }
                    builds.append(build_data)
                    
            except Exception as e:
                logger.error(f"Erreur pour buildType {buildtype_id}: {str(e)}")
                # En cas d'erreur, créer un build avec statut UNKNOWN
                build_data = {
                    'id': buildtype_id,
                    'buildTypeId': buildtype_id,
                    'name': buildtype_id,
                    'projectName': '',
                    'webUrl': '',
                    'status': 'UNKNOWN',
                    'state': 'finished',
                    'number': ''
                }
                builds.append(build_data)

        logger.info(f"Statuts récupérés pour {len(builds)} builds sélectionnés")
        return builds

    except Exception as e:
        logger.error(f"Erreur fetch_selected_builds_status: {str(e)}")
        return []


def update_database_builds(builds: List[Dict[str, Any]]):
    """
    Met à jour la base de données avec les builds de TeamCity
    """
    try:
        session = SessionLocal()
        
        session.execute(text("DELETE FROM builds"))
        
        for build in builds:
            session.execute(
                text("""
                    INSERT INTO builds (
                        id, name, project_name, web_url, status, state, 
                        last_updated, build_type_id
                    ) VALUES (
                        :id, :name, :project_name, :web_url, :status, :state,
                        :last_updated, :build_type_id
                    )
                """),
                {
                    'id': build['id'],
                    'name': build['name'],
                    'project_name': build['projectName'],
                    'web_url': build['webUrl'],
                    'status': build['status'],
                    'state': build['state'],
                    'last_updated': datetime.now(),
                    'build_type_id': build['buildTypeId']
                }
            )
        
        session.commit()
        logger.info(f"Base de données mise à jour avec {len(builds)} builds")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur lors de la mise à jour de la base de données: {e}")
        raise
    finally:
        session.close()

def fetch_teamcity_agents() -> List[Dict[str, Any]]:
    """
    Récupère la liste des agents TeamCity avec leur statut en temps réel.
    """
    # Vérifier si TeamCity est configuré
    if not TEAMCITY_TOKEN or TEAMCITY_URL == 'http://localhost:8111':
        logger.warning("TeamCity non configuré pour les agents")
        return []
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

    try:
        # Récupérer tous les agents avec leurs détails
        url = f"{TEAMCITY_URL}/app/rest/agents?fields=agent(id,name,connected,enabled,authorized,lastSeen,properties(property(name,value)))"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        agents = []
        root = ET.fromstring(response.text)

        for agent_elem in root.findall('agent'):
            agent_id = agent_elem.attrib.get('id', '')
            agent_name = agent_elem.attrib.get('name', '')
            connected = agent_elem.attrib.get('connected', 'false').lower() == 'true'
            enabled = agent_elem.attrib.get('enabled', 'false').lower() == 'true'
            authorized = agent_elem.attrib.get('authorized', 'false').lower() == 'true'
            last_seen = agent_elem.attrib.get('lastSeen', '')

            # Déterminer le statut de l'agent
            if not connected:
                status = "offline"
            elif not enabled:
                status = "disabled"
            elif not authorized:
                status = "unauthorized"
            else:
                status = "online"

            # Récupérer le build en cours si l'agent est connecté
            current_build = None
            if connected:
                try:
                    # Récupérer les builds en cours pour cet agent
                    build_url = f"{TEAMCITY_URL}/app/rest/agents/id:{agent_id}/builds?locator=running:true&fields=build(id,buildType(name))"
                    build_response = requests.get(build_url, headers=headers, timeout=5)
                    if build_response.status_code == 200:
                        build_root = ET.fromstring(build_response.text)
                        running_builds = build_root.findall('build')
                        if running_builds:
                            # Prendre le premier build en cours
                            build_elem = running_builds[0]
                            buildtype_elem = build_elem.find('buildType')
                            if buildtype_elem is not None:
                                current_build = buildtype_elem.attrib.get('name', 'Build en cours')
                            status = "busy"
                except Exception as e:
                    logger.debug(f"Impossible de récupérer le build en cours pour {agent_name}: {e}")

            agent_data = {
                'name': agent_name,
                'status': status,
                'currentBuild': current_build,
                'lastSeen': last_seen,
                'connected': connected,
                'enabled': enabled,
                'authorized': authorized
            }

            agents.append(agent_data)

        logger.info(f"Récupération de {len(agents)} agents TeamCity")
        return agents

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des agents TeamCity: {str(e)}")
        return []

def fetch_main_projects_only() -> Dict[str, Any]:
    """
    Récupère UNIQUEMENT les 3 projets principaux de TeamCity.
    Force le filtrage pour correspondre exactement à l'interface TeamCity.
    """
    # Vérifier si TeamCity est configuré
    if not TEAMCITY_TOKEN or TEAMCITY_URL == 'http://localhost:8111':
        print("WARNING: TeamCity non configuré")
        return {'projects': [], 'buildtypes': [], 'all_project_paths': []}
    
    headers = {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

    try:
        print(f"=== RÉCUPÉRATION PROJETS PRINCIPAUX SEULEMENT ===")
        
        # Récupérer TOUS les buildTypes
        buildtypes_url = f"{TEAMCITY_URL}/app/rest/buildTypes?fields=buildType(id,name,projectName,project(id,name))&count=10000"
        print(f"URL buildTypes: {buildtypes_url}")
        
        response = requests.get(buildtypes_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        buildtypes_data = []
        root = ET.fromstring(response.text)
        
        # Projets principaux autorisés
        allowed_main_projects = ["GO2 Version 612", "GO2 Version New", "Web Services"]
        
        for buildtype_elem in root.findall('buildType'):
            buildtype_id = buildtype_elem.attrib.get('id', '')
            buildtype_name = buildtype_elem.attrib.get('name', '')
            project_name = buildtype_elem.attrib.get('projectName', '')
            
            # Filtrer les buildTypes archivés
            is_archived = buildtype_elem.attrib.get('archived', 'false').lower() == 'true'
            if is_archived:
                continue
                
            # Ignorer les buildTypes sans nom ou de projets racine
            if not buildtype_name or not project_name or project_name == '<Root project>' or project_name == 'Root project':
                continue
            
            # Extraire le projet principal
            project_parts = project_name.split(' / ')
            if project_parts:
                main_project = project_parts[0]
                
                # Ne garder que les projets principaux autorisés
                if main_project in allowed_main_projects:
                    print(f"BuildType autorisé: {buildtype_id} -> {buildtype_name} (Projet: {main_project})")
                    
                    buildtype_data = {
                        'id': buildtype_id,
                        'buildTypeId': buildtype_id,
                        'name': buildtype_name,
                        'projectName': project_name,
                        'webUrl': '',
                        'status': 'UNKNOWN',
                        'state': 'finished',
                        'type': 'buildtype'
                    }
                    buildtypes_data.append(buildtype_data)
        
        # Créer les projets principaux
        projects_data = []
        for main_project in allowed_main_projects:
            # Vérifier si ce projet a des buildTypes
            has_buildtypes = any(
                buildtype['projectName'].startswith(main_project) 
                for buildtype in buildtypes_data
            )
            
            if has_buildtypes:
                project_data = {
                    'id': main_project,
                    'name': main_project,
                    'parentName': '',
                    'fullPath': main_project,
                    'type': 'project'
                }
                projects_data.append(project_data)
                print(f"Projet principal ajouté: {main_project}")
        
        print(f"=== RÉSULTAT PROJETS PRINCIPAUX ===")
        print(f"Projets principaux: {[p['name'] for p in projects_data]}")
        print(f"BuildTypes: {len(buildtypes_data)}")
        
        return {
            'projects': projects_data,
            'buildtypes': buildtypes_data,
            'all_project_paths': [p['name'] for p in projects_data]
        }

    except Exception as e:
        print(f"ERREUR projets principaux: {str(e)}")
        return {'projects': [], 'buildtypes': [], 'all_project_paths': []}


if __name__ == "__main__":
    try:
        logger.info("=== Récupération des builds TeamCity ===")
        builds = fetch_teamcity_builds_alternative()
        logger.info(f"{len(builds)} builds récupérés depuis TeamCity.")

        update_database_builds(builds)

        for i, build in enumerate(builds[:5]):
            logger.info(f"\nBuild {i + 1}:")
            logger.info(f"  Name: {build['name']}")
            logger.info(f"  Project: {build['projectName']}")
            logger.info(f"  Status: {build['status']}")
            logger.info(f"  State: {build['state']}")
            logger.info(f"  URL: {build['webUrl']}")

    except Exception as e:
        logger.error(f"Erreur lors du test: {e}")