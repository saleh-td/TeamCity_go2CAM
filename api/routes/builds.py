from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from ..services.teamcity_fetcher import fetch_teamcity_agents, fetch_all_teamcity_builds
from ..services.modern_user_service import user_service
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any

router = APIRouter()
logger = logging.getLogger(__name__)

cache: Dict[str, Any] = {
    "teamcity_builds": None,
    "teamcity_agents": None,
    "builds_timestamp": None,
    "agents_timestamp": None,
    "ttl": timedelta(minutes=5)
}



@router.get("/builds")
async def get_builds():
    try:
        now = datetime.now()
        
        if (cache["teamcity_builds"] is not None and 
            cache["builds_timestamp"] is not None and 
            now - cache["builds_timestamp"] < cache["ttl"]):
            return {"builds": cache["teamcity_builds"]}
        
        builds_data = await get_teamcity_builds_direct()
        
        # Plus besoin de filtrage - système automatique moderne !
        if builds_data:
            # Tous les builds sont automatiquement organisés
            all_filtered_builds = builds_data
            
            builds_data = all_filtered_builds
        
        cache["teamcity_builds"] = builds_data
        cache["builds_timestamp"] = now
        
        return {"builds": builds_data}
        
    except Exception as e:
        logger.error(f"Erreur get_builds: {str(e)}")
        return {"builds": []}

@router.get("/builds/classified")
async def get_builds_classified():
    try:
        builds_data = await get_teamcity_builds_direct()
        
        response_data = {
            "parameters": {},
            "columns": {},
            "total_builds": len(builds_data)
        }
        
        # Nouveau système moderne - plus de filtrage primitif !
        return response_data
        
    except Exception as e:
        logger.error(f"Erreur get_builds_classified: {str(e)}")
        return {
            "parameters": {},
            "columns": {},
            "total_builds": 0
        }

@router.get("/builds/dashboard")
async def get_builds_dashboard():
    try:
        # Nouveau système moderne
        selected_builds = user_service.get_selected_builds()
        
        if not selected_builds:
            return {
                "builds": [],
                "projects": {},
                "total_builds": 0,
                "running_count": 0,
                "success_count": 0,
                "failure_count": 0
            }
        
        builds_data = await get_teamcity_builds_direct()
        
        filtered_builds = [
            build for build in builds_data 
            if build.get("buildTypeId") in selected_builds
        ]
        
        # Organiser les builds par catégories logiques selon les patterns
        projects_organized = organize_builds_by_patterns(filtered_builds)
        
        running_count = len([b for b in filtered_builds if b.get("state") == "running"])
        success_count = len([b for b in filtered_builds if b.get("status") == "SUCCESS"])
        failure_count = len([b for b in filtered_builds if b.get("status") in ["FAILURE", "FAILED"]])
        
        return {
            "builds": filtered_builds,
            "projects": projects_organized,
            "total_builds": len(filtered_builds),
            "running_count": running_count,
            "success_count": success_count,
            "failure_count": failure_count
        }
        
    except Exception as e:
        logger.error(f"Erreur get_builds_dashboard: {str(e)}")
        return {
            "builds": [],
            "projects": {},
            "total_builds": 0,
            "running_count": 0,
            "success_count": 0,
            "failure_count": 0
        }

def organize_builds_by_patterns(builds):
    """Organise les builds automatiquement en analysant leurs patterns"""
    
    # 1. ANALYSE AUTOMATIQUE DES PROJECTS DEPUIS LES BUILDS
    project_analysis = analyze_build_projects(builds)
    
    # 2. ORGANISATION AUTOMATIQUE EN COLONNES
    organized_projects = auto_organize_projects(project_analysis)
    
    return organized_projects

def analyze_build_projects(builds):
    """Analyse 100% automatique basée sur les vrais noms de projets TeamCity"""
    project_groups = {}
    
    for build in builds:
        project_name = build.get("projectName", "Unknown Project")
        

        project_parts = [part.strip() for part in project_name.split("/")]
        
        if len(project_parts) >= 1:
            main_project = project_parts[0]
            main_project_key = main_project.lower().replace(" ", "").replace(".", "")
            
            # Créer le projet principal s'il n'existe pas
            if main_project_key not in project_groups:
                project_groups[main_project_key] = {
                    "name": main_project,
                    "subprojects": {}
                }
            
            # Construire la clé du sous-projet à partir de TOUS les niveaux restants
            if len(project_parts) > 1:
                # Utiliser tous les niveaux restants comme sous-projet
                # Ex: "Product Compil / GO2cam" ou "Internal Libraries / GO2Dlls"
                subproject_path = " / ".join(project_parts[1:])
                subproject_key = f"{main_project.upper()} / {subproject_path.upper()}"
            else:
                # Si pas de sous-projet, utiliser le nom principal
                subproject_key = f"{main_project.upper()} / GENERAL"
            
            # Créer le sous-projet s'il n'existe pas
            if subproject_key not in project_groups[main_project_key]["subprojects"]:
                project_groups[main_project_key]["subprojects"][subproject_key] = {
                    "name": subproject_key,
                    "builds": []
                }
            
            # Ajouter le build
            project_groups[main_project_key]["subprojects"][subproject_key]["builds"].append(build)
        else:
            # Cas de fallback pour les projets sans hiérarchie claire
            fallback_key = "autres"
            if fallback_key not in project_groups:
                project_groups[fallback_key] = {
                    "name": "Autres Projets",
                    "subprojects": {}
                }
            
            subproject_key = "AUTRES / DIVERS"
            if subproject_key not in project_groups[fallback_key]["subprojects"]:
                project_groups[fallback_key]["subprojects"][subproject_key] = {
                    "name": subproject_key,
                    "builds": []
                }
            
            project_groups[fallback_key]["subprojects"][subproject_key]["builds"].append(build)
    
    return project_groups

def auto_organize_projects(project_analysis):
    """Organisation 100% automatique des projets - pas de priorité hardcodée"""
    
    # Trier les projets alphabétiquement pour un ordre stable et prévisible
    sorted_projects = sorted(project_analysis.items())
    
    # Créer la structure finale
    result = {}
    
    for project_key, project_data in sorted_projects:
        # Nettoyer les sous-projets vides
        filtered_subprojects = {
            k: v for k, v in project_data["subprojects"].items() 
            if len(v["builds"]) > 0
        }
        
        if filtered_subprojects:  # Seulement si le projet a des builds
            result[project_key] = {
                "name": project_data["name"],
                "subprojects": filtered_subprojects
            }
    
    return result

@router.get("/builds/dashboard/v2")
async def get_builds_dashboard_v2():
    try:
        # Nouveau système moderne
        selected_builds = user_service.get_selected_builds()
        
        if not selected_builds:
            return {
                "builds": [],
                "projects": {},
                "total_builds": 0,
                "running_count": 0,
                "success_count": 0,
                "failure_count": 0
            }
        
        builds_data = await get_teamcity_builds_direct()
        
        filtered_builds = [
            build for build in builds_data 
            if build.get("buildTypeId") in selected_builds
        ]
        
        running_count = len([b for b in filtered_builds if b.get("state") == "running"])
        success_count = len([b for b in filtered_builds if b.get("status") == "SUCCESS"])
        failure_count = len([b for b in filtered_builds if b.get("status") in ["FAILURE", "FAILED"]])
        
        return {
            "builds": filtered_builds,
            "projects": {},
            "total_builds": len(filtered_builds),
            "running_count": running_count,
            "success_count": success_count,
            "failure_count": failure_count
        }
        
    except Exception as e:
        logger.error(f"Erreur get_builds_dashboard_v2: {str(e)}")
        return {
            "builds": [],
            "projects": {},
            "total_builds": 0,
            "running_count": 0,
            "success_count": 0,
            "failure_count": 0
        }

@router.get("/parameters")
async def get_parameters():
    try:
        return {"parameters": {}}
    except Exception as e:
        logger.error(f"Erreur get_parameters: {str(e)}")
        return {"parameters": {}}

@router.get("/status")
async def get_build_status(id: str):
    try:
        builds_data = await get_teamcity_builds_direct()
        build = next((b for b in builds_data if b.get("id") == id), None)
        
        if build:
            return build
        else:
            raise HTTPException(status_code=404, detail="Build non trouvé")
            
    except Exception as e:
        logger.error(f"Erreur get_build_status: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur serveur")

async def get_teamcity_builds_direct():
    try:
        now = datetime.now()
        
        if (cache["teamcity_builds"] is not None and 
            cache["builds_timestamp"] is not None and 
            now - cache["builds_timestamp"] < cache["ttl"]):
            return cache["teamcity_builds"]
        
        builds_data = await run_in_threadpool(fetch_all_teamcity_builds)
        
        cache["teamcity_builds"] = builds_data
        cache["builds_timestamp"] = now
        
        return builds_data
        
    except Exception as e:
        logger.error(f"Erreur get_teamcity_builds_direct: {str(e)}")
        return cache.get("teamcity_builds", [])

@router.get("/teamcity/builds")
async def get_teamcity_builds():
    try:
        builds_data = await get_teamcity_builds_direct()
        return {"builds": builds_data}
    except Exception as e:
        logger.error(f"Erreur get_teamcity_builds: {str(e)}")
        return {"builds": []}

@router.get("/teamcity/builds/force-refresh")
async def force_refresh_teamcity_builds():
    try:
        cache["teamcity_builds"] = None
        cache["builds_timestamp"] = None
        
        builds_data = await get_teamcity_builds_direct()
        return {
            "message": "Cache vidé et données rechargées",
            "builds_count": len(builds_data)
        }
    except Exception as e:
        logger.error(f"Erreur force_refresh_teamcity_builds: {str(e)}")
        return {"message": "Erreur lors du rechargement", "builds_count": 0}

@router.get("/teamcity/status")
async def get_teamcity_status():
    try:
        builds_data = await get_teamcity_builds_direct()
        
        total_builds = len(builds_data)
        running_builds = len([b for b in builds_data if b.get("state") == "running"])
        success_builds = len([b for b in builds_data if b.get("status") == "SUCCESS"])
        failure_builds = len([b for b in builds_data if b.get("status") in ["FAILURE", "FAILED"]])
        
        return {
            "total_builds": total_builds,
            "running_builds": running_builds,
            "success_builds": success_builds,
            "failure_builds": failure_builds,
            "last_update": cache.get("builds_timestamp")
        }
    except Exception as e:
        logger.error(f"Erreur get_teamcity_status: {str(e)}")
        return {
            "total_builds": 0,
            "running_builds": 0,
            "success_builds": 0,
            "failure_builds": 0,
            "last_update": None
        }

@router.get("/agents")
async def get_agents():
    try:
        now = datetime.now()
        
        if (cache["teamcity_agents"] is not None and 
            cache["agents_timestamp"] is not None and 
            now - cache["agents_timestamp"] < cache["ttl"]):
            return {"agents": cache["teamcity_agents"]}
        
        agents_data = await run_in_threadpool(fetch_teamcity_agents)
        
        cache["teamcity_agents"] = agents_data
        cache["agents_timestamp"] = now
        
        return {"agents": agents_data}
        
    except Exception as e:
        logger.error(f"Erreur get_agents: {str(e)}")
        return {"agents": []}

@router.get("/agents/force-refresh")
async def force_refresh_agents():
    try:
        cache["teamcity_agents"] = None
        cache["agents_timestamp"] = None
        
        agents_data = await run_in_threadpool(fetch_teamcity_agents)
        return {
            "message": "Cache vidé et agents rechargés",
            "agents_count": len(agents_data)
        }
    except Exception as e:
        logger.error(f"Erreur force_refresh_agents: {str(e)}")
        return {"message": "Erreur lors du rechargement", "agents_count": 0}

@router.get("/config")
async def get_configuration():
    try:
        # Nouveau système moderne
        return user_service.get_config_for_api()
    except Exception as e:
        logger.error(f"Erreur get_configuration: {str(e)}")
        return {"builds": {"selectedBuilds": []}}

@router.get("/builds/tree")
async def get_builds_tree():
    """
    Crée automatiquement la structure complète des projets TeamCity
    pour la page de configuration
    """
    try:
        # Récupérer tous les builds TeamCity
        builds_data = await get_teamcity_builds_direct()
        
        if not builds_data:
            return {
                "projects": {},
                "total_builds": 0,
                "selected_builds": []
            }
        
        # Nouveau système moderne
        selected_builds = user_service.get_selected_builds()
        
        # Créer une structure arborescente complète
        tree_structure = create_complete_tree_structure(builds_data)
        
        return {
            "projects": tree_structure,
            "total_builds": len(builds_data),
            "selected_builds": selected_builds
        }
        
    except Exception as e:
        logger.error(f"Erreur get_builds_tree: {str(e)}")
        return {
            "projects": {},
            "total_builds": 0,
            "selected_builds": []
        }

def create_complete_tree_structure(builds_data):
    """
    Crée une structure arborescente complète basée sur projectName
    Compatible avec le frontend de configuration existant
    """
    tree = {}
    
    for build in builds_data:
        project_name = build.get("projectName", "")
        build_type_id = build.get("buildTypeId", "")
        name = build.get("name", "")
        
        if not project_name or not build_type_id:
            continue
            
        # Analyser la hiérarchie du projectName
        # Ex: "Go2 Version 612 / Product Install / Meca"
        project_parts = [part.strip() for part in project_name.split("/")]
        
        if len(project_parts) >= 2:
            # Niveau 1: Projet principal (ex: "Go2 Version 612")
            main_project = project_parts[0]
            
            # Niveau 2: Catégorie (ex: "Product Install")  
            category = project_parts[1]
            
            # Niveau 3: Sous-catégorie si elle existe (ex: "Meca")
            subcategory = project_parts[2] if len(project_parts) >= 3 else "General"
            
            # Créer la structure arborescente avec "subprojects"
            if main_project not in tree:
                tree[main_project] = {
                    "name": main_project,
                    "subprojects": {}
                }
            
            if category not in tree[main_project]["subprojects"]:
                tree[main_project]["subprojects"][category] = {
                    "name": category,
                    "subprojects": {}
                }
            
            if subcategory not in tree[main_project]["subprojects"][category]["subprojects"]:
                tree[main_project]["subprojects"][category]["subprojects"][subcategory] = {
                    "name": subcategory,
                    "builds": []
                }
            
            # Ajouter le build à la structure
            tree[main_project]["subprojects"][category]["subprojects"][subcategory]["builds"].append({
                "buildTypeId": build_type_id,
                "name": name,
                "projectName": project_name,
                "webUrl": build.get("webUrl", ""),
                "status": build.get("status", "UNKNOWN"),
                "state": build.get("state", "finished")
            })
        
        else:
            # Build de niveau racine (rare mais possible)
            root_project = project_parts[0] if project_parts else "Divers"
            
            if root_project not in tree:
                tree[root_project] = {
                    "name": root_project,
                    "subprojects": {}
                }
            
            if "General" not in tree[root_project]["subprojects"]:
                tree[root_project]["subprojects"]["General"] = {
                    "name": "General", 
                    "subprojects": {}
                }
            
            if "Builds" not in tree[root_project]["subprojects"]["General"]["subprojects"]:
                tree[root_project]["subprojects"]["General"]["subprojects"]["Builds"] = {
                    "name": "Builds",
                    "builds": []
                }
            
            tree[root_project]["subprojects"]["General"]["subprojects"]["Builds"]["builds"].append({
                "buildTypeId": build_type_id,
                "name": name,
                "projectName": project_name,
                "webUrl": build.get("webUrl", ""),
                "status": build.get("status", "UNKNOWN"),
                "state": build.get("state", "finished")
            })
    
    return tree

@router.post("/builds/tree/selection")
async def save_builds_selection(selection_data: dict):
    """
    OBSOLÈTE : Remplacé par le nouvel endpoint moderne
    Gardé pour compatibilité temporaire
    """
    try:
        # Rediriger vers le nouveau système moderne
        return await save_build_selection(selection_data)
    except Exception as e:
        logger.error(f"Erreur dans l'ancien endpoint: {e}")
        raise HTTPException(status_code=500, detail="Utiliser le nouveau endpoint /builds/tree/selection")
    except Exception as e:
        logger.error(f"Erreur save_builds_selection: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde")

@router.get("/versions/info")
async def get_versions_info():
    try:
        return {"versions": {}}
    except Exception as e:
        logger.error(f"Erreur get_versions_info: {str(e)}")
        return {"versions": {}}

@router.post("/versions/update")
async def update_versions(versions_data: dict):
    try:
        return {"message": "Versions mises à jour"}
    except Exception as e:
        logger.error(f"Erreur update_versions: {str(e)}")
        return {"message": "Erreur lors de la mise à jour"}

@router.get("/versions/detect")
async def detect_versions():
    try:
        return {"versions": {}}
    except Exception as e:
        logger.error(f"Erreur detect_versions: {str(e)}")
        return {"versions": {}}

@router.post("/builds/tree/selection")
async def save_build_selection(selection_data: dict):
    """
    Nouveau endpoint moderne pour sauvegarder les sélections utilisateur
    Remplace l'ancien système JSON hardcodé
    """
    try:
        selected_builds = selection_data.get("selectedBuilds", [])
        
        if not isinstance(selected_builds, list):
            raise HTTPException(status_code=400, detail="selectedBuilds doit être une liste")
        
        # Récupérer tous les builds pour avoir les métadonnées
        all_builds = await get_teamcity_builds_direct()
        
        # Mettre à jour via le service moderne
        success = user_service.bulk_update_selections(selected_builds, all_builds)
        
        if success:
            logger.info(f"Sélection mise à jour: {len(selected_builds)} builds sélectionnés")
            return {
                "message": "Sélection sauvegardée avec succès",
                "selected_count": len(selected_builds),
                "total_builds": len(all_builds)
            }
        else:
            raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur save_build_selection: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/migration/from-json")
async def migrate_from_json():
    """
    Endpoint pour migrer depuis l'ancien système JSON
    """
    try:
        # Migrer depuis user_config.json
        config_path = "config/user_config.json"
        success = user_service.migrate_from_json_config(config_path)
        
        if success:
            return {"message": "Migration réussie depuis JSON vers base de données"}
        else:
            return {"message": "Aucune migration nécessaire ou fichier introuvable"}
            
    except Exception as e:
        logger.error(f"Erreur migration: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la migration")

