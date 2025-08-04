import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from typing import List, Dict, Any
import logging

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

def fetch_all_teamcity_builds() -> List[Dict[str, Any]]:
    """Récupère tous les builds TeamCity avec déduplication par buildType"""
    url = f"{TEAMCITY_URL}/app/rest/builds?locator=running:any,failedToStart:any,count:100&fields=build(id,buildTypeId,number,status,state,webUrl,buildType(id,name,projectName))"
    
    root = _make_teamcity_request(url)
    builds = []
    unique_buildtypes = set()
    
    for build_elem in root.findall('build'):
        buildtype_id = build_elem.attrib.get('buildTypeId', '')
        
        if buildtype_id in unique_buildtypes:
            continue
        unique_buildtypes.add(buildtype_id)
        
        buildtype_elem = build_elem.find('buildType')
        if buildtype_elem is not None:
            buildtype_name = buildtype_elem.attrib.get('name', '')
            project_name = buildtype_elem.attrib.get('projectName', '')
        else:
            buildtype_name = buildtype_id
            project_name = ''
        
        web_url = build_elem.attrib.get('webUrl', '')
        if web_url and not web_url.startswith('http'):
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