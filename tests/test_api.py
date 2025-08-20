import os
import json
from fastapi.testclient import TestClient

# Assurer l'import de l'application FastAPI
from api.main import app


client = TestClient(app)


def test_get_config_structure():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    # Clés de base présentes
    assert "builds" in data
    assert "config" in data
    assert "selectedBuilds" in data
    # Types attendus
    assert isinstance(data["builds"].get("selectedBuilds", []), list)
    assert isinstance(data.get("selectedBuilds", []), list)


def test_builds_tree_demo_mode():
    resp = client.get("/api/builds/tree", params={"demo": True})
    assert resp.status_code == 200
    data = resp.json()
    assert "projects" in data
    assert isinstance(data["projects"], dict)
    assert data.get("total_builds", 0) > 0


def test_save_selection_and_dashboard_demo():
    # Utiliser les IDs connues du mode demo (définies dans routes/builds.py)
    selected = [
        "Go2Version612_Plugins_BuildDebug",
        "WebServices_Portal_Deploy",
    ]
    resp = client.post("/api/builds/tree/selection", json={"selectedBuilds": selected})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("selected_count") == len(selected)

    # Vérifier le dashboard en mode demo
    dash = client.get("/api/builds/dashboard", params={"demo": True})
    assert dash.status_code == 200
    data = dash.json()
    assert data.get("total_builds", 0) >= len(selected)
    assert isinstance(data.get("projects", {}), dict)

