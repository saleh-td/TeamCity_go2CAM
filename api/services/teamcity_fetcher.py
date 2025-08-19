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
    """Récupère le statut du dernier build pour un buildType donné - PRIORITÉ aux builds en cours"""
    try:
        # ÉTAPE 1: Chercher d'abord s'il y a un build en cours (running)
        running_url = f"{TEAMCITY_URL}/app/rest/builds?locator=buildType:{build_type_id},state:running,count:1&fields=build(id,number,status,state,webUrl)"
        
        running_root = _make_teamcity_request(running_url)
        running_build = running_root.find('build')
        
        if running_build is not None:
            # PRIORITÉ ABSOLUE: Il y a un build en cours !
            logger.info(f"Build EN COURS détecté pour {build_type_id}: {running_build.attrib.get('number', '')}")
            return {
                'status': running_build.attrib.get('status', 'UNKNOWN'),
                'state': running_build.attrib.get('state', 'running'),
                'number': running_build.attrib.get('number', ''),
                'webUrl': running_build.attrib.get('webUrl', f"{TEAMCITY_URL}/viewType.html?buildTypeId={build_type_id}")
            }
        
        # ÉTAPE 2: Aucun build en cours, récupérer le dernier build terminé
        finished_url = f"{TEAMCITY_URL}/app/rest/builds?locator=buildType:{build_type_id},count:1&fields=build(id,number,status,state,webUrl)"
        
        finished_root = _make_teamcity_request(finished_url)
        finished_build = finished_root.find('build')
        
        if finished_build is not None:
            return {
                'status': finished_build.attrib.get('status', 'UNKNOWN'),
                'state': finished_build.attrib.get('state', 'finished'),
                'number': finished_build.attrib.get('number', ''),
                'webUrl': finished_build.attrib.get('webUrl', f"{TEAMCITY_URL}/viewType.html?buildTypeId={build_type_id}")
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
    # Inclure les attributs archived si disponibles pour filtrer dynamiquement
    url = (
        f"{TEAMCITY_URL}/app/rest/buildTypes?"
        "fields=buildType("
        "id,name,projectName,"
        "project(id,name,parentProjectId,archived,parentProject(name,archived))"
        ")"
    )
    
    root = _make_teamcity_request(url)
    builds = []
    filtered_count = 0
    
    for buildtype_elem in root.findall('buildType'):
        buildtype_id = buildtype_elem.attrib.get('id', '')
        buildtype_name = buildtype_elem.attrib.get('name', '')
        
        project_elem = buildtype_elem.find('project')
        if project_elem is not None:
            project_name = project_elem.attrib.get('name', '')
            project_archived_attr = project_elem.attrib.get('archived', 'false') == 'true'
            
            # Récupérer l'info sur le projet parent pour une hiérarchie complète
            parent_project_elem = project_elem.find('parentProject')
            if parent_project_elem is not None:
                parent_project_name = parent_project_elem.attrib.get('name', '')
                parent_archived_attr = parent_project_elem.attrib.get('archived', 'false') == 'true'
                # Construire le chemin complet de la hiérarchie
                if parent_project_name and parent_project_name != project_name:
                    full_project_path = f"{parent_project_name} / {project_name}"
                else:
                    full_project_path = project_name
            else:
                full_project_path = project_name
                parent_archived_attr = False
        else:
            project_name = ''
            full_project_path = ''
            project_archived_attr = False
            parent_archived_attr = False
        
        # FILTRAGE INTELLIGENT: Exclure les projets archivés (priorité aux attributs API)
        is_archived_via_attr = project_archived_attr or parent_archived_attr
        if is_archived_via_attr:
            filtered_count += 1
            continue
        # Fallback sur détection par pattern si l'attribut n'est pas disponible et que le chemin suggère une ancienne version
        if not is_archived_via_attr and not is_project_active(full_project_path):
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
    """Récupère les agents TeamCity avec leurs détails complets"""
    url = f"{TEAMCITY_URL}/app/rest/agents"
    
    root = _make_teamcity_request(url)
    agents = []
    
    for agent_elem in root.findall('agent'):
        # Récupérer le href pour accéder aux détails de l'agent
        href = agent_elem.attrib.get('href', '')
        agent_name = agent_elem.attrib.get('name', '')
        
        # Faire un appel séparé pour récupérer les détails de l'agent (comme dans PHP)
        agent_details = _fetch_agent_details(href)
        
        # Déterminer le statut selon la logique PHP
        # connected && enabled && authorized && uptodate = vert, sinon rouge
        is_agent_ok = (
            agent_details.get('connected', False) and 
            agent_details.get('enabled', False) and 
            agent_details.get('authorized', False) and 
            agent_details.get('uptodate', False)
        )
        
        agent_data = {
            'id': agent_elem.attrib.get('id', ''),
            'name': agent_name,
            'status': 'connected' if is_agent_ok else 'disconnected',
            'type': agent_elem.attrib.get('typeId', ''),
            'details': agent_details  # Pour le debug
        }
        agents.append(agent_data)
    
    return agents

def _fetch_agent_details(href: str) -> Dict[str, Any]:
    """Récupère les détails complets d'un agent via son href"""
    if not href:
        return {}
    
    # Construire l'URL complète (href commence par /app/rest/...)
    url = f"{TEAMCITY_URL}{href}"
    
    try:
        root = _make_teamcity_request(url)
        
        # Parser les attributs comme dans le PHP
        details = {
            'connected': root.attrib.get('connected', 'false') == 'true',
            'enabled': root.attrib.get('enabled', 'false') == 'true',
            'authorized': root.attrib.get('authorized', 'false') == 'true',
            'uptodate': root.attrib.get('uptodate', 'false') == 'true',
        }
        
        return details
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des détails de l'agent {href}: {e}")
        return {
            'connected': False,
            'enabled': False,
            'authorized': False,
            'uptodate': False,
        }