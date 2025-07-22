from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import json
import os
from pathlib import Path

router = APIRouter()

# Chemin du fichier de configuration
CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "user_config.json"

# Configuration par défaut
DEFAULT_CONFIG = {
    "display": {
        "showSuccess": True,
        "showFailure": True,
        "showRunning": True,
        "showStats": True
    },
    "columns": {
        "showColumn612": True,
        "showColumnNew": True
    },
    "projects": {
        "selectedProjects": [],
        "showProjectTitles": True
    },
    "refresh": {
        "interval": 60,
        "autoRefresh": True
    }
}

def ensure_config_dir():
    """S'assurer que le répertoire de configuration existe"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)

def load_config() -> Dict[str, Any]:
    """Charger la configuration depuis le fichier"""
    ensure_config_dir()
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Erreur lors du chargement de la configuration: {e}")
    
    return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> bool:
    """Sauvegarder la configuration dans le fichier"""
    ensure_config_dir()
    
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Erreur lors de la sauvegarde de la configuration: {e}")
        return False

@router.get("/config")
async def get_configuration():
    """Récupérer la configuration actuelle (compatible Dashboard.js)"""
    config = load_config()
    
    # Structure unifiée compatible avec Dashboard.js
    return {
        "config": config,
        "selectedBuilds": config.get("builds", {}).get("selectedBuilds", []),
        "success": True
    }

@router.post("/config")
async def save_configuration(config_data: Dict[str, Any]):
    """Sauvegarder une nouvelle configuration"""
    
    print(f"=== SAUVEGARDE CONFIG ===")
    print(f"Config reçue: {config_data}")
    print(f"selectedProjects: {config_data.get('projects', {}).get('selectedProjects', [])}")
    
    # Valider la structure de la configuration
    required_sections = ["display", "columns", "projects", "refresh"]
    for section in required_sections:
        if section not in config_data:
            raise HTTPException(status_code=400, detail=f"Section manquante: {section}")
    
    # Sauvegarder la configuration
    if save_config(config_data):
        print(f"Sauvegarde réussie dans {CONFIG_FILE}")
        return {"message": "Configuration sauvegardée avec succès", "config": config_data}
    else:
        print(f"Erreur lors de la sauvegarde")
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde")

@router.delete("/config")
async def reset_configuration():
    """Réinitialiser la configuration aux valeurs par défaut"""
    
    # Pour la réinitialisation, on garde une liste vide de selectedProjects
    # Le frontend initialisera avec tous les projets disponibles
    reset_config = DEFAULT_CONFIG.copy()
    
    if save_config(reset_config):
        return {"message": "Configuration réinitialisée", "config": reset_config}
    else:
        raise HTTPException(status_code=500, detail="Erreur lors de la réinitialisation")

def apply_config_to_builds(builds_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Appliquer les filtres de configuration aux données de builds"""
    
    if not builds_data or "columns" not in builds_data:
        return builds_data
    
    filtered_columns = {}
    
    for column_name, projects in builds_data["columns"].items():
        # Vérifier si la colonne doit être affichée (basé sur les noms automatiques de TeamCity)
        # On identifie les colonnes par leur contenu plutôt que par leur nom configuré
        if "612" in column_name and not config["columns"]["showColumn612"]:
            continue
        if ("New" in column_name or "new" in column_name.lower()) and not config["columns"]["showColumnNew"]:
            continue
            
        filtered_projects = {}
        
        for project_name, builds in projects.items():
            # Filtrer les projets selon la sélection (si selectedProjects est vide, on affiche tout)
            selected_projects = config["projects"].get("selectedProjects", [])
            if selected_projects and project_name not in selected_projects:
                continue
                
            # Filtrer les builds selon le statut
            filtered_builds = []
            for build in builds:
                status = build.get("status", "").upper()
                state = build.get("state", "").lower()
                
                # Debug: log des statuts pour comprendre le problème
                print(f"Build {build.get('name', 'unknown')}: status='{status}', state='{state}'")
                
                # Ne filtrer que si l'option est désactivée
                if status == "SUCCESS" and not config["display"]["showSuccess"]:
                    print(f"  -> Filtré: SUCCESS non affiché")
                    continue
                if status == "FAILURE" and not config["display"]["showFailure"]:
                    print(f"  -> Filtré: FAILURE non affiché")
                    continue
                if (state in ["running", "building"] or status in ["RUNNING", "BUILDING"]) and not config["display"]["showRunning"]:
                    print(f"  -> Filtré: RUNNING/BUILDING non affiché")
                    continue
                    
                print(f"  -> Gardé: status={status}, state={state}")
                filtered_builds.append(build)
            
            if filtered_builds:  # Seulement ajouter le projet s'il a des builds à afficher
                filtered_projects[project_name] = filtered_builds
        
        if filtered_projects:  # Seulement ajouter la colonne s'il y a des projets
            filtered_columns[column_name] = filtered_projects
    
    # Créer les nouvelles données filtrées
    filtered_data = builds_data.copy()
    filtered_data["columns"] = filtered_columns
    filtered_data["user_config"] = config
    
    return filtered_data 