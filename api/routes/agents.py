from fastapi import APIRouter
import requests
import os
import xml.etree.ElementTree as ET

router = APIRouter()

TEAMCITY_URL = os.getenv('TEAMCITY_URL', 'http://localhost:8111')
TEAMCITY_TOKEN = os.getenv('TEAMCITY_TOKEN', '')

@router.get("/teamcity/agents")
def get_teamcity_agents():
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