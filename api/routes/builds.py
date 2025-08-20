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
    "ttl": timedelta(minutes=10)  # Cache plus long pour éviter les appels répétés
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
        
        if builds_data:
            builds_data = builds_data
        
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
        
        return response_data
        
    except Exception as e:
        logger.error(f"Erreur get_builds_classified: {str(e)}")
        return {
            "parameters": {},
            "columns": {},
            "total_builds": 0
        }

@router.get("/builds/dashboard")
async def get_builds_dashboard(demo: bool = False):
    try:
        selected_builds = user_service.get_selected_builds()
        
        if demo:
            # Mode démo pour tester l'affichage
            builds_data = get_demo_builds_for_testing()
            # Simuler quelques builds sélectionnés
            if not selected_builds:
                selected_builds = ["Go2Version612_Plugins_BuildDebug", "WebServices_Portal_Deploy"]
        else:
            builds_data = await get_teamcity_builds_direct()
        
        if not selected_builds:
            return {
                "builds": [],
                "projects": {},
                "total_builds": 0,
                "running_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "message": "Aucun build sélectionné - allez dans la configuration pour en choisir"
            }
        
        # Filtrer selon la sélection utilisateur
        filtered_builds = [
            build for build in builds_data 
            if build.get("buildTypeId") in selected_builds
        ]
        
        if not filtered_builds and not demo:
            return {
                "builds": [],
                "projects": {},
                "total_builds": 0,
                "running_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "message": "Builds sélectionnés introuvables - vérifiez TeamCity ou utilisez ?demo=true"
            }
        
        # Utiliser la nouvelle structure hiérarchique
        projects_organized = create_complete_tree_structure(filtered_builds)
        
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
            "failure_count": 0,
            "error": str(e)
        }

def organize_builds_by_patterns(builds):
    """Organise les builds automatiquement en analysant leurs patterns"""
    
    project_analysis = analyze_build_projects(builds)
    organized_projects = auto_organize_projects(project_analysis)
    
    return organized_projects

def analyze_build_projects(builds):
    """Analyse automatique basée sur les vrais noms de projets TeamCity"""
    project_groups = {}
    
    for build in builds:
        project_name = build.get("projectName", "Unknown Project")
        project_parts = [part.strip() for part in project_name.split("/")]
        
        if len(project_parts) >= 1:
            main_project = project_parts[0]
            main_project_key = main_project.lower().replace(" ", "").replace(".", "")
            
            if main_project_key not in project_groups:
                project_groups[main_project_key] = {
                    "name": main_project,
                    "subprojects": {}
                }
            
            if len(project_parts) > 1:
                subproject_path = " / ".join(project_parts[1:])
                subproject_key = f"{main_project.upper()} / {subproject_path.upper()}"
            else:
                subproject_key = f"{main_project.upper()} / GENERAL"
            
            if subproject_key not in project_groups[main_project_key]["subprojects"]:
                project_groups[main_project_key]["subprojects"][subproject_key] = {
                    "name": subproject_key,
                    "builds": []
                }
            
            project_groups[main_project_key]["subprojects"][subproject_key]["builds"].append(build)
        else:
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
    """Organisation automatique des projets"""
    
    sorted_projects = sorted(project_analysis.items())
    result = {}
    
    for project_key, project_data in sorted_projects:
        filtered_subprojects = {
            k: v for k, v in project_data["subprojects"].items() 
            if len(v["builds"]) > 0
        }
        
        if filtered_subprojects:
            result[project_key] = {
                "name": project_data["name"],
                "subprojects": filtered_subprojects
            }
    
    return result

@router.get("/builds/dashboard/v2")
async def get_builds_dashboard_v2():
    try:
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
        return user_service.get_config_for_api()
    except Exception as e:
        logger.error(f"Erreur get_configuration: {str(e)}")
        return {"builds": {"selectedBuilds": []}}

@router.get("/builds/tree/force-refresh")
async def force_refresh_builds_tree():
    """Force le rechargement de l'arbre des builds en vidant le cache"""
    try:
        # Vider le cache TeamCity
        cache["teamcity_builds"] = None
        cache["builds_timestamp"] = None
        
        # Recharger les données
        builds_data = await get_teamcity_builds_direct()
        selected_builds = user_service.get_selected_builds()
        tree_structure = create_complete_tree_structure(builds_data)
        
        return {
            "message": "Arbre des builds rechargé avec succès",
            "projects": tree_structure,
            "total_builds": len(builds_data),
            "selected_builds": selected_builds
        }
        
    except Exception as e:
        logger.error(f"Erreur force_refresh_builds_tree: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors du rechargement de l'arbre")

@router.get("/builds/tree")
async def get_builds_tree(demo: bool = False):
    """Crée automatiquement la structure complète des projets TeamCity pour la page de configuration"""
    try:
        if demo:
            # Mode démo avec données de test pour développement
            builds_data = get_demo_builds_for_testing()
        else:
            builds_data = await get_teamcity_builds_direct()
        
        if not builds_data:
            logger.warning("Aucune donnée TeamCity disponible - utilisez ?demo=true pour tester")
            return {
                "projects": {},
                "total_builds": 0,
                "selected_builds": [],
                "message": "Aucune donnée - ajoutez ?demo=true pour tester"
            }
        
        selected_builds = user_service.get_selected_builds()
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

def get_demo_builds_for_testing():
    """Données de test réalistes pour le développement - TEMPORAIRE"""
    return [
        # GO2 Version 612 avec sous-projets
        {"buildTypeId": "Go2Version612_Plugins_BuildDebug", "name": "Build Debug", "projectName": "plugins"},
        {"buildTypeId": "Go2Version612_ProductCompil_BuildRelease", "name": "Build Release", "projectName": "product compil"},
        {"buildTypeId": "Go2Version612_ProductInstall_BuildDebug", "name": "Build Debug", "projectName": "product install"},
        {"buildTypeId": "Go2Version612_InternalLib_BuildRelease", "name": "Build Release", "projectName": "internal librairie"},
        
        # Web Services (projet parent direct)
        {"buildTypeId": "WebServices_Portal_Deploy", "name": "Deploy Portal", "projectName": "Web Services / GO2Portal"},
        {"buildTypeId": "WebServices_FileServer_Build", "name": "Build FileServer", "projectName": "Web Services / FileServer"},
        
        # GO2 Version New avec sous-projets
        {"buildTypeId": "Go2VersionNew_Plugins_BuildDebug", "name": "Build Debug", "projectName": "plugins"},
        {"buildTypeId": "Go2VersionNew_ProductCompil_BuildRelease", "name": "Build Release", "projectName": "product compil"},
    ]


def extract_main_project_from_path(project_path: str) -> str:
    """Extrait le projet principal depuis le chemin complet TeamCity"""
    if not project_path:
        return "Autres"
    
    # Prendre la première partie du chemin comme projet principal
    parts = [part.strip() for part in project_path.split("/")]
    if parts:
        return parts[0]
    
    return "Autres"

def create_complete_tree_structure(builds_data):
    """Crée une structure arborescente intelligente avec regroupement automatique"""
    tree = {}
    
    for build in builds_data:
        project_name = build.get("projectName", "")
        build_type_id = build.get("buildTypeId", "")
        name = build.get("name", "")
        
        if not project_name or not build_type_id:
            continue
        
        # Analyser le projectName pour créer une hiérarchie intelligente
        project_parts = [part.strip() for part in project_name.split("/")]
        
        # RÈGLES INTELLIGENTES DE HIÉRARCHIE
        main_project, category, subcategory = analyze_project_hierarchy(project_parts, build_type_id)
        
        # Construire l'arborescence
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
        
        # Ajouter le build
        tree[main_project]["subprojects"][category]["subprojects"][subcategory]["builds"].append({
            "buildTypeId": build_type_id,
            "name": name,
            "projectName": project_name,
            "webUrl": build.get("webUrl", ""),
            "status": build.get("status", "UNKNOWN"),
            "state": build.get("state", "finished")
        })
    
    return tree

def analyze_project_hierarchy(project_parts, build_type_id):
    """Analyse intelligente de la hiérarchie des projets"""
    
    # CAS SPÉCIAUX : Web Services doit être projet parent
    if any("Web Services" in part for part in project_parts):
        return "Web Services", project_parts[-1] if len(project_parts) > 1 else "General", "Builds"
    
    # DÉTECTION DU PROJET PRINCIPAL via patterns dans buildTypeId
    main_project = detect_main_project_from_buildtype(build_type_id, project_parts)
    
    # SOUS-PROJETS à regrouper sous le projet principal
    subproject_patterns = ["plugins", "product compil", "product install", "internal librairie"]
    
    if len(project_parts) >= 1:
        first_part_lower = project_parts[0].lower()
        
        # Si c'est un sous-projet connu, le regrouper sous le projet principal
        for pattern in subproject_patterns:
            if pattern in first_part_lower:
                category = project_parts[0]  # plugins, product compil, etc.
                subcategory = project_parts[1] if len(project_parts) > 1 else "Builds"
                return main_project, category, subcategory
    
    # STRUCTURE NORMALE
    if len(project_parts) >= 3:
        return project_parts[0], project_parts[1], project_parts[2]
    elif len(project_parts) == 2:
        return project_parts[0], project_parts[1], "Builds"
    elif len(project_parts) == 1:
        return project_parts[0], "General", "Builds"
    else:
        return main_project, "Non classés", "Builds"

def detect_main_project_from_buildtype(build_type_id, project_parts):
    """Détecte le projet principal de manière générique"""
    
    # Utiliser la première partie du projet comme projet principal
    if project_parts and len(project_parts) > 0:
        return project_parts[0]
    
    # Fallback : extraire depuis buildTypeId (première partie avant _)
    if build_type_id and "_" in build_type_id:
        return build_type_id.split("_")[0]
    
    return "Projet Principal"

@router.post("/builds/tree/selection")
async def save_builds_selection(selection_data: dict):
    """OBSOLÈTE : Remplacé par le nouvel endpoint moderne"""
    try:
        return await save_build_selection(selection_data)
    except Exception as e:
        logger.error(f"Erreur dans l'ancien endpoint: {e}")
        raise HTTPException(status_code=500, detail="Utiliser le nouveau endpoint /builds/tree/selection")

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
    """Nouveau endpoint moderne pour sauvegarder les sélections utilisateur"""
    try:
        selected_builds = selection_data.get("selectedBuilds", [])
        
        if not isinstance(selected_builds, list):
            raise HTTPException(status_code=400, detail="selectedBuilds doit être une liste")
        
        # Récupérer les builds TeamCity; si vide, le modèle créera un fallback pour ne pas perdre la sélection
        all_builds = await get_teamcity_builds_direct()
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

@router.get("/teamcity/test-connection")
async def test_teamcity_connection():
    """Teste la connexion à TeamCity et retourne des informations de diagnostic"""
    from ..services.teamcity_fetcher import _is_teamcity_configured, _make_teamcity_request, TEAMCITY_URL, TEAMCITY_TOKEN
    
    try:
        # Vérifier la configuration
        if not _is_teamcity_configured():
            return {
                "status": "error",
                "message": "TeamCity non configuré",
                "details": {
                    "url": TEAMCITY_URL,
                    "token_configured": bool(TEAMCITY_TOKEN),
                    "token_length": len(TEAMCITY_TOKEN) if TEAMCITY_TOKEN else 0
                }
            }
        
        # Test de connexion simple
        test_url = f"{TEAMCITY_URL}/app/rest/buildTypes?locator=count:1"
        root = _make_teamcity_request(test_url)
        
        if root.tag == 'root' and len(root) == 0:
            return {
                "status": "error",
                "message": "Connexion TeamCity échouée",
                "details": {
                    "url": TEAMCITY_URL,
                    "possible_causes": [
                        "Serveur TeamCity inaccessible",
                        "Token invalide ou expiré", 
                        "Problème de réseau/firewall",
                        "URL incorrecte"
                    ]
                }
            }
        
        # Compter les buildTypes récupérés
        buildtypes = root.findall('buildType')
        
        return {
            "status": "success",
            "message": "Connexion TeamCity OK",
            "details": {
                "url": TEAMCITY_URL,
                "buildtypes_found": len(buildtypes),
                "sample_buildtype": buildtypes[0].attrib.get('name', '') if buildtypes else None
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur test connexion TeamCity: {str(e)}")
        return {
            "status": "error", 
            "message": f"Erreur lors du test: {str(e)}",
            "details": {"url": TEAMCITY_URL}
        }

@router.post("/migration/from-json")
async def migrate_from_json():
    """Endpoint pour migrer depuis l'ancien système JSON"""
    try:
        config_path = "config/user_config.json"
        success = user_service.migrate_from_json_config(config_path)
        
        if success:
            return {"message": "Migration réussie depuis JSON vers base de données"}
        else:
            return {"message": "Aucune migration nécessaire ou fichier introuvable"}
            
    except Exception as e:
        logger.error(f"Erreur migration: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la migration")

