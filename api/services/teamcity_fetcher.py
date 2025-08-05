import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

TEAMCITY_URL = os.getenv('TEAMCITY_URL', 'http://192.168.0.48:8080')
TEAMCITY_TOKEN = os.getenv('TEAMCITY_TOKEN', '')

def _get_headers():
    """Retourne les headers communs pour les requêtes TeamCity"""
    return {
        'Authorization': f'Bearer {TEAMCITY_TOKEN}',
        'Accept': 'application/xml'
    }

def _is_teamcity_configured():
    """Vérifie si TeamCity est configuré"""
    return TEAMCITY_TOKEN and TEAMCITY_URL != 'http://localhost:8111'

def is_project_active(project_name: str) -> bool:
    """
    Détermine si un projet est actif (non-archivé)
    Filtre automatiquement les versions archivées basé sur l'analyse intelligente
    """
    # Patterns des versions archivées détectées automatiquement
    archived_patterns = [
        'GO2 Version 6.09',
        'GO2 Version 6.10', 
        'GO2 Version 6.11',
        # Ajouter ici d'autres patterns archivés détectés dans le futur
    ]
    
    # Exclure les versions archivées
    for pattern in archived_patterns:
        if pattern in project_name:
            logger.debug(f"Projet archivé exclu: {project_name}")
            return False
    
    # Inclure tous les autres projets (actifs et futurs)
    return True

def _make_teamcity_request(url: str) -> ET.Element:
    """Effectue une requête TeamCity et retourne l'élément racine XML"""
    if not _is_teamcity_configured():
        logger.warning("TeamCity non configuré")
        return ET.Element('root')
    
    try:
        response = requests.get(url, headers=_get_headers(), timeout=10)
        response.raise_for_status()
        return ET.fromstring(response.text)
    except Exception as e:
        logger.error(f"Erreur requête TeamCity: {e}")
        return ET.Element('root')

def fetch_latest_build_status(build_type_id: str) -> Dict[str, str]:
    """Récupère le statut du dernier build exécuté pour un buildType donné"""
    try:
        # Récupérer le dernier build pour ce buildType
        url = f"{TEAMCITY_URL}/app/rest/builds?locator=buildType:{build_type_id},count:1&fields=build(id,number,status,state,webUrl)"
        
        root = _make_teamcity_request(url)
        build_elem = root.find('build')
        
        if build_elem is not None:
            return {
                'status': build_elem.attrib.get('status', 'UNKNOWN'),
                'state': build_elem.attrib.get('state', 'finished'),
                'number': build_elem.attrib.get('number', ''),
                'webUrl': build_elem.attrib.get('webUrl', f"{TEAMCITY_URL}/viewType.html?buildTypeId={build_type_id}")
            }
        else:
            # Aucun build exécuté pour ce buildType
            return {
                'status': 'UNKNOWN',
                'state': 'finished',
                'number': '',
                'webUrl': f"{TEAMCITY_URL}/viewType.html?buildTypeId={build_type_id}"
            }
    except Exception as e:
        logger.warning(f"Impossible de récupérer le statut pour {build_type_id}: {e}")
        return {
            'status': 'UNKNOWN',
            'state': 'finished', 
            'number': '',
            'webUrl': f"{TEAMCITY_URL}/viewType.html?buildTypeId={build_type_id}"
        }

def fetch_all_teamcity_builds() -> List[Dict[str, Any]]:
    """Récupère tous les buildTypes TeamCity (configurations de builds) actifs uniquement"""
    url = f"{TEAMCITY_URL}/app/rest/buildTypes?fields=buildType(id,name,projectName,project(id,name,parentProjectId,parentProject(name)))"
    
    root = _make_teamcity_request(url)
    builds = []
    filtered_count = 0
    
    for buildtype_elem in root.findall('buildType'):
        buildtype_id = buildtype_elem.attrib.get('id', '')
        buildtype_name = buildtype_elem.attrib.get('name', '')
        
        project_elem = buildtype_elem.find('project')
        if project_elem is not None:
            project_name = project_elem.attrib.get('name', '')
            
            # Récupérer l'info sur le projet parent pour une hiérarchie complète
            parent_project_elem = project_elem.find('parentProject')
            if parent_project_elem is not None:
                parent_project_name = parent_project_elem.attrib.get('name', '')
                # Construire le chemin complet de la hiérarchie
                if parent_project_name and parent_project_name != project_name:
                    full_project_path = f"{parent_project_name} / {project_name}"
                else:
                    full_project_path = project_name
            else:
                full_project_path = project_name
        else:
            project_name = ''
            full_project_path = ''
        
        # FILTRAGE INTELLIGENT: Exclure les projets archivés
        if not is_project_active(full_project_path):
            filtered_count += 1
            continue
        
        build_data = {
            'id': buildtype_id,
            'buildTypeId': buildtype_id,
            'name': buildtype_name,
            'projectName': full_project_path,  # Utiliser le chemin complet pour la hiérarchie
            'webUrl': f"{TEAMCITY_URL}/viewType.html?buildTypeId={buildtype_id}",
            'status': 'UNKNOWN',  # Sera mis à jour avec le vrai statut
            'state': 'finished',
            'number': ''
        }
        
        # Récupérer le statut du dernier build exécuté pour ce buildType
        last_build_status = fetch_latest_build_status(buildtype_id)
        if last_build_status:
            build_data.update(last_build_status)
        
        builds.append(build_data)
    
    logger.info(f"Builds récupérés: {len(builds)} actifs, {filtered_count} archivés filtrés")
    return builds

def fetch_all_teamcity_projects() -> List[Dict[str, Any]]:
    """Récupère tous les projets TeamCity"""
    url = f"{TEAMCITY_URL}/app/rest/projects?fields=project(id,name,parentProjectId)"
    
    root = _make_teamcity_request(url)
    projects = []
    
    for project_elem in root.findall('project'):
        project_data = {
            'id': project_elem.attrib.get('id', ''),
            'name': project_elem.attrib.get('name', ''),
            'parentProjectId': project_elem.attrib.get('parentProjectId', '')
        }
        projects.append(project_data)
    
    return projects

def fetch_all_teamcity_projects_optimized() -> Dict[str, Any]:
    """Récupère les projets et buildtypes optimisés depuis l'API buildTypes"""
    url = f"{TEAMCITY_URL}/app/rest/buildTypes?fields=buildType(id,name,projectName,project(id,name,parentProjectId))"
    
    root = _make_teamcity_request(url)
    buildtypes = []
    all_project_paths = set()
    
    for buildtype_elem in root.findall('buildType'):
        project_elem = buildtype_elem.find('project')
        if project_elem is not None:
            project_name = project_elem.attrib.get('name', '')
            project_id = project_elem.attrib.get('id', '')
            parent_project_id = project_elem.attrib.get('parentProjectId', '')
            
            buildtype_data = {
                'id': buildtype_elem.attrib.get('id', ''),
                'name': buildtype_elem.attrib.get('name', ''),
                'projectName': project_name,
                'projectId': project_id,
                'parentProjectId': parent_project_id
            }
            buildtypes.append(buildtype_data)
            all_project_paths.add(project_name)
    
    return {
        'projects': [],
        'buildtypes': buildtypes,
        'all_project_paths': list(all_project_paths)
    }

def fetch_current_versions_buildtypes() -> List[Dict[str, Any]]:
    """Récupère les buildtypes avec leurs URLs"""
    url = f"{TEAMCITY_URL}/app/rest/buildTypes?fields=buildType(id,name,projectName,project(id,name,parentProjectId))"
    
    root = _make_teamcity_request(url)
    buildtypes = []
    
    for buildtype_elem in root.findall('buildType'):
        project_elem = buildtype_elem.find('project')
        if project_elem is not None:
            project_name = project_elem.attrib.get('name', '')
            project_id = project_elem.attrib.get('id', '')
            
            buildtype_data = {
                'id': buildtype_elem.attrib.get('id', ''),
                'name': buildtype_elem.attrib.get('name', ''),
                'projectName': project_name,
                'projectId': project_id,
                'buildTypeId': buildtype_elem.attrib.get('id', ''),
                'status': 'UNKNOWN',
                'state': 'finished',
                'webUrl': f"{TEAMCITY_URL}/viewType.html?buildTypeId={buildtype_elem.attrib.get('id', '')}"
            }
            buildtypes.append(buildtype_data)
    
    return buildtypes

def fetch_teamcity_agents() -> List[Dict[str, Any]]:
    """Récupère les agents TeamCity"""
    url = f"{TEAMCITY_URL}/app/rest/agents"
    
    root = _make_teamcity_request(url)
    agents = []
    
    for agent_elem in root.findall('agent'):
        agent_data = {
            'id': agent_elem.attrib.get('id', ''),
            'name': agent_elem.attrib.get('name', ''),
            'status': 'connected' if agent_elem.attrib.get('connected', 'false') == 'true' else 'disconnected',
            'type': agent_elem.attrib.get('typeId', ''),
        }
        agents.append(agent_data)
    
    return agents