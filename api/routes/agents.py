from fastapi import APIRouter
import requests
import os
import xml.etree.ElementTree as ET
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

TEAMCITY_URL = os.getenv('TEAMCITY_URL', 'http://192.168.0.48:8080')
TEAMCITY_TOKEN = os.getenv('TEAMCITY_TOKEN', '')

@router.get("/agents")
def get_agents():
    """Endpoint principal pour récupérer les agents TeamCity avec leurs vrais statuts"""
    try:
        url = f"{TEAMCITY_URL}/app/rest/agents?fields=agent(id,name,connected,enabled,authorized,typeId,uptodate)"
        headers = {
            'Authorization': f'Bearer {TEAMCITY_TOKEN}',
            'Accept': 'application/xml'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        agents = []
        
        for agent in root.findall('agent'):
            connected = agent.attrib.get("connected", "false") == "true"
            enabled = agent.attrib.get("enabled", "false") == "true"
            authorized = agent.attrib.get("authorized", "false") == "true"
            
            # Déterminer le statut réel de l'agent
            if connected and enabled and authorized:
                status = "online"
            elif connected and enabled:
                status = "busy"  # Connecté mais peut-être occupé
            elif not authorized:
                status = "offline"  # Non autorisé
            else:
                status = "disconnected"  # Vraiment déconnecté
            
            agents.append({
                "id": agent.attrib.get("id", ""),
                "name": agent.attrib.get("name", ""),
                "status": status,
                "connected": connected,
                "enabled": enabled,
                "authorized": authorized,
                "typeId": agent.attrib.get("typeId", ""),
                "uptodate": agent.attrib.get("uptodate", "false") == "true"
            })
        
        logger.info(f"Agents récupérés: {len(agents)}")
        return {"agents": agents}
        
    except Exception as e:
        logger.error(f"Erreur récupération agents: {e}")
        return {"agents": []}

@router.get("/teamcity/agents")
def get_teamcity_agents():
    """Endpoint de compatibilité pour l'ancien système"""
    try:
        url = f"{TEAMCITY_URL}/app/rest/agents"
        headers = {
            'Authorization': f'Bearer {TEAMCITY_TOKEN}',
            'Accept': 'application/xml'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        agents = []
        
        for agent in root.findall('agent'):
            agents.append({
                "id": agent.attrib.get("id", ""),
                "name": agent.attrib.get("name", ""),
                "status": "connected" if agent.attrib.get("connected", "false") == "true" else "disconnected",
                "type": agent.attrib.get("typeId", ""),
            })
        
        return agents
    except Exception as e:
        return [] 