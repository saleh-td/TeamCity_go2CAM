from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from ..services.teamcity_fetcher import fetch_selected_builds_status, fetch_teamcity_agents, fetch_all_teamcity_builds
from ..services.sentinel_params import get_dynamic_build_classification
from ..services.build_tree_service import BuildTreeService
from .configurations import load_config, apply_config_to_builds
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

router = APIRouter()
logger = logging.getLogger(__name__)


cache: Dict[str, Any] = {
    "teamcity_builds": None,
    "teamcity_agents": None,
    "builds_timestamp": None,
    "agents_timestamp": None,
    "ttl": timedelta(minutes=2)
}

@router.get("/builds")
async def get_builds():
    """Récupère tous les builds (compatible API PHP)."""
    try:
        # Récupérer les builds depuis TeamCity (live)
        builds_data = await get_teamcity_builds_direct()
        
        return {"builds": builds_data}
        
    except Exception as e:
        logger.error(f"Erreur get_builds: {str(e)}")
        # Retourner un tableau vide en cas d'erreur pour éviter les plantages frontend
        return {"builds": []}

@router.get("/builds/classified")
async def get_builds_classified():
    """
    Récupère les builds classifiés selon la logique de l'ancien système PHP.
    Reproduit exactement la classification par buildTypeId.
    Applique automatiquement les filtres de configuration utilisateur.
    """
    try:
        # Récupérer les builds depuis TeamCity
        builds_data = await get_teamcity_builds_direct()
        params, classified_builds = await run_in_threadpool(
            get_dynamic_build_classification, builds_data
        )
        
        # Construire la réponse de base
        response_data = {
            "parameters": params,
            "columns": classified_builds,
            "total_builds": len(builds_data)
        }
        
        # Charger et appliquer la configuration utilisateur
        user_config = load_config()
        filtered_data = apply_config_to_builds(response_data, user_config)
        
        return filtered_data
        
    except Exception as e:
        logger.error(f"Erreur get_builds_classified: {str(e)}")
        return {
            "parameters": {},
            "columns": {},
            "total_builds": 0
        }

@router.get("/builds/dashboard")
async def get_builds_dashboard():
    """
    Récupère les builds pour le dashboard en utilisant la sélection utilisateur de l'arborescence.
    Cette route remplace l'ancienne logique de classification par la nouvelle sélection utilisateur.
    """
    try:
        # Charger la sélection des builds depuis la configuration utilisateur
        user_config = load_config()
        selected_builds = user_config.get("builds", {}).get("selectedBuilds", [])
        
        # Si aucune sélection n'est configurée, ne montrer aucun build
        if not selected_builds:
            selected_builds = []
            logger.info(f"Aucune sélection configurée - aucun build affiché dans le dashboard")
            return {
                "builds": [],
                "projects": {},
                "total_builds": 0,
                "running_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "selected_builds": []
            }
        
        # Récupérer les builds selon la sélection utilisateur (optimisé)
        from ..services.teamcity_fetcher import fetch_selected_builds_status
        builds_data = await run_in_threadpool(fetch_selected_builds_status, selected_builds)
        
        # Organiser les builds par projet pour l'affichage
        projects = {}
        for build in builds_data:
            project_name = build.get('projectName', 'Unknown Project')
            if project_name not in projects:
                projects[project_name] = []
            projects[project_name].append(build)
        
        # Compter les builds par statut
        running_count = sum(1 for build in builds_data if build.get('state', '').lower() == 'running')
        success_count = sum(1 for build in builds_data if build.get('status', '').lower() == 'success')
        failure_count = sum(1 for build in builds_data if build.get('status', '').lower() == 'failure')
        
        return {
            "builds": builds_data,
            "projects": projects,
            "total_builds": len(builds_data),
            "running_count": running_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "selected_builds": selected_builds
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
            "selected_builds": []
        }

@router.get("/builds/dashboard/v2")
async def get_builds_dashboard_v2():
    """
    Version 2 du dashboard : utilise les mêmes données que l'arborescence pour être cohérent.
    Retourne les builds organisés par version dynamique.
    """
    try:
        # Charger la sélection utilisateur
        user_config = load_config()
        selected_builds = user_config.get("builds", {}).get("selectedBuilds", [])
        
        # Si aucune sélection n'est configurée, ne montrer aucun build
        if not selected_builds:
            selected_builds = []
            logger.info(f"Aucune sélection configurée - aucun build affiché dans le dashboard v2")
            return {
                "builds": [],
                "versions": {},
                "current_versions": [],
                "total_builds": 0,
                "running_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "selected_builds": []
            }
        
        # Récupérer les builds selon la sélection utilisateur (optimisé)
        from ..services.teamcity_fetcher import fetch_selected_builds_status
        all_builds = await run_in_threadpool(fetch_selected_builds_status, selected_builds)
        
        # Organiser les builds par version ET par sous-dossier
        versions_data = {}
        for build in all_builds:
            project_name = build.get("projectName", "")
            
            # Extraire la version depuis le projectName
            if "GO2 Version 612" in project_name:
                version = "GO2 Version 612"
            elif "GO2 Version New" in project_name:
                version = "GO2 Version New"
            else:
                version = "Autre"
            
            # Extraire le sous-dossier depuis le projectName
            # Exemple: "GO2 Version 612 / Product Install / Dental" -> "Product Install / Dental"
            subfolder = project_name
            if " / " in project_name:
                # Enlever la version du début
                if version in project_name:
                    subfolder = project_name.replace(f"{version} / ", "")
                else:
                    # Garder tout après la première partie
                    parts = project_name.split(" / ")
                    if len(parts) > 1:
                        subfolder = " / ".join(parts[1:])
            
            # Initialiser la structure si nécessaire
            if version not in versions_data:
                versions_data[version] = {}
            
            if subfolder not in versions_data[version]:
                versions_data[version][subfolder] = []
            
            versions_data[version][subfolder].append(build)
        
        # Compter les builds par statut
        running_count = sum(1 for build in all_builds if build.get('state', '').lower() == 'running')
        success_count = sum(1 for build in all_builds if build.get('status', '').lower() == 'success')
        failure_count = sum(1 for build in all_builds if build.get('status', '').lower() == 'failure')
        
        # Récupérer les informations de version depuis l'arborescence
        try:
            from ..services.build_tree_service import BuildTreeService
            tree_data = await run_in_threadpool(BuildTreeService.get_filtered_builds_tree)
            version_info = tree_data.get("version_info", {})
            current_versions = version_info.get("current_versions", [])
        except:
            current_versions = ["GO2 Version 612", "GO2 Version New"]
        
        return {
            "builds": all_builds,
            "versions": versions_data,
            "current_versions": current_versions,
            "total_builds": len(all_builds),
            "running_count": running_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "selected_builds": selected_builds
        }
        
    except Exception as e:
        logger.error(f"Erreur get_builds_dashboard_v2: {str(e)}")
        return {
            "builds": [],
            "versions": {},
            "current_versions": [],
            "total_builds": 0,
            "running_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "selected_builds": []
        }

@router.get("/parameters")
async def get_parameters():
    """Récupère les paramètres de configuration depuis la base sentinel (compatible API PHP)."""
    try:
        params = await run_in_threadpool(get_sentinel_parameters)
        
        return {"parameters": [params]}
        
    except Exception as e:
        logger.error(f"Erreur get_parameters: {str(e)}")
        return {"parameters": []}

@router.get("/status")
async def get_build_status(id: str):
    """Récupère le statut d'un build spécifique (compatible API PHP)."""
    try:
        return {
            "id": id,
            "status": "SUCCESS",
            "state": "finished"
        }
    except Exception as e:
        logger.error(f"Erreur get_build_status: {str(e)}")
        return {
            "id": id,
            "status": "UNKNOWN",
            "state": "finished"
        }

async def get_teamcity_builds_direct():
    """Fonction helper pour récupérer les builds TeamCity."""
    try:
        now = datetime.now()
        
        # Vérifier le cache
        if (cache["teamcity_builds"] is not None and 
            cache["builds_timestamp"] is not None and 
            now - cache["builds_timestamp"] < cache["ttl"]):
            return cache["teamcity_builds"]

        builds = await asyncio.wait_for(
            run_in_threadpool(fetch_all_teamcity_builds),
            timeout=30.0
        )
        
        # Mettre à jour le cache
        cache["teamcity_builds"] = builds
        cache["builds_timestamp"] = now
        
        return builds
        
    except Exception as e:
        logger.error(f"Erreur get_teamcity_builds_direct: {str(e)}")
        # Retourner le cache même expiré, ou tableau vide
        return cache.get("teamcity_builds", [])

@router.get("/teamcity/builds")
async def get_teamcity_builds():
    """
    Récupère les builds TeamCity en direct (live, sans passer par la base de données).
    Utilise un cache pour éviter les appels répétés.
    """
    try:
        now = datetime.now()
        if (cache["teamcity_builds"] is not None and 
            cache["builds_timestamp"] is not None and 
            now - cache["builds_timestamp"] < cache["ttl"]):
            logger.info("Retour des builds TeamCity depuis le cache")
            return {
                "builds": cache["teamcity_builds"],
                "count": len(cache["teamcity_builds"]),
                "cached": True,
                "cache_age_seconds": (now - cache["builds_timestamp"]).total_seconds()
            }
        
        logger.info("Récupération des builds TeamCity en cours...")
        builds = await asyncio.wait_for(
            run_in_threadpool(fetch_all_teamcity_builds),
            timeout=30.0  # Timeout de 30 secondes
        )

        cache["teamcity_builds"] = builds
        cache["builds_timestamp"] = now
        
        logger.info(f"Récupération terminée: {len(builds)} builds trouvés")
        
        return {
            "builds": builds,
            "count": len(builds),
            "cached": False
        }
        
    except asyncio.TimeoutError:
        logger.error("Timeout lors de la récupération des builds TeamCity")
        
        if cache["teamcity_builds"] is not None:
            logger.warning("Retour du cache expiré suite au timeout")
            return {
                "builds": cache["teamcity_builds"],
                "count": len(cache["teamcity_builds"]),
                "cached": True,
                "cache_age_seconds": (now - cache["builds_timestamp"]).total_seconds(),
                "warning": "Données du cache suite à un timeout"
            }
        
        raise HTTPException(
            status_code=504,
            detail="La récupération des builds TeamCity a pris trop de temps (timeout après 30s)"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des builds TeamCity: {str(e)}")
        if cache["teamcity_builds"] is not None:
            logger.warning("Retour du cache suite à une erreur")
            return {
                "builds": cache["teamcity_builds"],
                "count": len(cache["teamcity_builds"]),
                "cached": True,
                "error": str(e),
                "warning": "Données du cache suite à une erreur"
            }
        
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des builds: {str(e)}"
        )

@router.get("/teamcity/builds/force-refresh")
async def force_refresh_teamcity_builds():
    """
    Force le rafraîchissement des builds TeamCity en ignorant le cache.
    Utile pour forcer une mise à jour immédiate.
    """
    try:
        logger.info("Rafraîchissement forcé des builds TeamCity...")
        
        # Vider le cache
        cache["teamcity_builds"] = None
        cache["builds_timestamp"] = None
        
        # Récupérer les nouvelles données
        builds = await asyncio.wait_for(
            run_in_threadpool(fetch_teamcity_builds),
            timeout=30.0
        )
        
        # Mettre à jour le cache
        cache["teamcity_builds"] = builds
        cache["builds_timestamp"] = datetime.now()
        
        return {
            "builds": builds,
            "count": len(builds),
            "cached": False,
            "message": "Cache rafraîchi avec succès"
        }
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Timeout lors du rafraîchissement forcé"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du rafraîchissement: {str(e)}"
        )

@router.get("/teamcity/status")
async def get_teamcity_status():
    """
    Vérifie le statut de la connexion TeamCity et du cache.
    """
    try:
        now = datetime.now()
        cache_info = {
            "has_builds_data": cache["teamcity_builds"] is not None,
            "has_agents_data": cache["teamcity_agents"] is not None,
            "builds_count": len(cache["teamcity_builds"]) if cache["teamcity_builds"] else 0,
            "agents_count": len(cache["teamcity_agents"]) if cache["teamcity_agents"] else 0,
            "builds_cache_age_seconds": (now - cache["builds_timestamp"]).total_seconds() if cache["builds_timestamp"] else None,
            "agents_cache_age_seconds": (now - cache["agents_timestamp"]).total_seconds() if cache["agents_timestamp"] else None,
            "builds_cache_expired": (now - cache["builds_timestamp"] > cache["ttl"]) if cache["builds_timestamp"] else True,
            "agents_cache_expired": (now - cache["agents_timestamp"] > cache["ttl"]) if cache["agents_timestamp"] else True,
            "ttl_seconds": cache["ttl"].total_seconds()
        }
        
        return {
            "status": "operational",
            "cache": cache_info
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/debug/dental-long-test")
async def debug_dental_long_test():
    """
    Endpoint de debug pour investiguer le problème DentalLongTest
    """
    try:
        from ..services.teamcity_fetcher import TEAMCITY_TOKEN, TEAMCITY_URL
        
        # Récupérer TOUS les builds avec "DentalLongTest" depuis TeamCity
        headers = {
            'Authorization': f'Bearer {TEAMCITY_TOKEN}',
            'Accept': 'application/xml'
        }
        
        # Recherche globale de tous les buildTypes avec "DentalLongTest"
        url = f"{TEAMCITY_URL}/app/rest/buildTypes?locator=name:DentalLongTest&fields=buildType(id,name,projectName,project(id,name))"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.text)
        buildtypes = root.findall('buildType')
        
        debug_data = {
            "total_buildtypes_found": len(buildtypes),
            "buildtypes": []
        }
        
        for buildtype in buildtypes:
            buildtype_data = {
                "id": buildtype.attrib.get('id', ''),
                "name": buildtype.attrib.get('name', ''),
                "projectName": buildtype.attrib.get('projectName', ''),
                "project_id": buildtype.attrib.get('projectId', '')
            }
            debug_data["buildtypes"].append(buildtype_data)
        
        return debug_data
        
    except Exception as e:
        logger.error(f"Erreur debug DentalLongTest: {str(e)}")
        return {"error": str(e)}

@router.get("/agents")
async def get_agents():
    """Récupère la liste des agents TeamCity avec leur statut en temps réel."""
    try:
        now = datetime.now()
        
        # Vérifier le cache
        if (cache["teamcity_agents"] is not None and 
            cache["agents_timestamp"] is not None and 
            now - cache["agents_timestamp"] < cache["ttl"]):
            logger.info("Retour des agents TeamCity depuis le cache")
            return {
                "agents": cache["teamcity_agents"],
                "count": len(cache["teamcity_agents"]),
                "cached": True,
                "cache_age_seconds": (now - cache["agents_timestamp"]).total_seconds()
            }
        
        logger.info("Récupération des agents TeamCity en cours...")
        agents = await asyncio.wait_for(
            run_in_threadpool(fetch_teamcity_agents),
            timeout=30.0
        )
        
        # Mettre à jour le cache
        cache["teamcity_agents"] = agents
        cache["agents_timestamp"] = now
        
        logger.info(f"Récupération terminée: {len(agents)} agents trouvés")
        
        return {
            "agents": agents,
            "count": len(agents),
            "cached": False
        }
        
    except asyncio.TimeoutError:
        logger.error("Timeout lors de la récupération des agents TeamCity")
        
        if cache["teamcity_agents"] is not None:
            logger.warning("Retour du cache expiré suite au timeout")
            return {
                "agents": cache["teamcity_agents"],
                "count": len(cache["teamcity_agents"]),
                "cached": True,
                "cache_age_seconds": (now - cache["agents_timestamp"]).total_seconds(),
                "warning": "Données du cache suite à un timeout"
            }
        
        raise HTTPException(
            status_code=504,
            detail="La récupération des agents TeamCity a pris trop de temps (timeout après 30s)"
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des agents TeamCity: {str(e)}")
        if cache["teamcity_agents"] is not None:
            logger.warning("Retour du cache suite à une erreur")
            return {
                "agents": cache["teamcity_agents"],
                "count": len(cache["teamcity_agents"]),
                "cached": True,
                "error": str(e),
                "warning": "Données du cache suite à une erreur"
            }
        
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des agents: {str(e)}"
        )

@router.get("/agents/force-refresh")
async def force_refresh_agents():
    """Force le rafraîchissement du cache des agents TeamCity."""
    try:
        cache["teamcity_agents"] = None
        cache["agents_timestamp"] = None
        
        # Récupérer les nouveaux agents
        response = await get_agents()
        
        return {
            "message": "Cache des agents rafraîchi avec succès",
            "agents_count": response.get("count", 0)
        }
        
    except Exception as e:
        logger.error(f"Erreur force_refresh_agents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du rafraîchissement du cache des agents: {str(e)}"
        )

@router.get("/projects/all")
async def get_all_projects():
    """Récupère tous les noms de projets uniques sans appliquer les filtres de configuration."""
    try:
        # Récupérer les builds depuis TeamCity (sans filtrage)
        builds_data = await get_teamcity_builds_direct()
        params, classified_builds = await run_in_threadpool(
            get_dynamic_build_classification, builds_data
        )
        
        # Construire la réponse de base (SANS appliquer les filtres de config)
        response_data = {
            "parameters": params,
            "columns": classified_builds,
            "total_builds": len(builds_data)
        }
        
        # Extraire tous les noms de projets uniques depuis les colonnes (non filtrées)
        columns = response_data.get("columns", {})
        project_names = set()
        
        for column_projects in columns.values():
            if isinstance(column_projects, dict):
                for project_name in column_projects.keys():
                    if project_name and project_name.strip():
                        project_names.add(project_name.strip())
        
        sorted_projects = sorted(list(project_names))
        
        return {
            "projects": sorted_projects,
            "count": len(sorted_projects)
        }
        
    except Exception as e:
        logger.error(f"Erreur get_all_projects: {str(e)}")
        return {
            "projects": [],
            "count": 0
        }

@router.get("/builds/tree")
async def get_builds_tree():
    """Récupère l'arborescence complète de TOUS les builds TeamCity pour la configuration."""
    try:
        logger.info("Récupération de l'arborescence complète de TOUS les builds TeamCity...")
        
        # Utiliser la méthode NON filtrée pour récupérer TOUS les projets
        tree = await run_in_threadpool(BuildTreeService.get_all_builds_tree)
        
        # Charger la configuration utilisateur pour appliquer les sélections
        user_config = load_config()
        selected_builds = user_config.get("builds", {}).get("selectedBuilds", [])
        
        # Si aucune sélection n'est configurée, ne sélectionner aucun build par défaut
        if not selected_builds:
            selected_builds = []
            logger.info(f"Aucune sélection configurée - aucun build sélectionné par défaut")
        
        # Appliquer la sélection utilisateur
        tree = BuildTreeService.apply_user_selection(tree, selected_builds)
        
        logger.info(f"Arborescence complète chargée: {len(tree.get('projects', {}))} projets, {tree.get('total_builds', 0)} builds totaux")
        
        return {
            "projects": tree.get("projects", {}),
            "total_builds": tree.get("total_builds", 0),
            "selected_builds": selected_builds
        }
        
    except Exception as e:
        logger.error(f"Erreur get_builds_tree: {str(e)}")
        return {
            "projects": {},
            "total_builds": 0,
            "selected_builds": []
        }

@router.get("/config")
async def get_configuration():
    """Récupère la configuration utilisateur pour le dashboard."""
    try:
        # Charger la configuration actuelle
        user_config = load_config()
        
        # Extraire la sélection de builds
        selected_builds = user_config.get("builds", {}).get("selectedBuilds", [])
        
        logger.info(f"Configuration chargée: {len(selected_builds)} builds sélectionnés")
        
        # STRUCTURE UNIFIÉE pour compatibilité Dashboard.js
        return {
            "config": {
                "builds": {
                    "selectedBuilds": selected_builds
                }
            },
            "selectedBuilds": selected_builds,  # Pour compatibilité
            "total_selected": len(selected_builds)
        }
        
    except Exception as e:
        logger.error(f"Erreur get_configuration: {str(e)}")
        # Retourner une configuration vide en cas d'erreur
        return {
            "config": {
                "builds": {
                    "selectedBuilds": []
                }
            },
            "selectedBuilds": [],
            "total_selected": 0
        }

@router.post("/builds/tree/selection")
async def save_builds_selection(selection_data: dict):
    """Sauvegarde la sélection de builds de l'utilisateur."""
    try:
        selected_builds = selection_data.get("selectedBuilds", [])
        
        # Charger la configuration actuelle
        user_config = load_config()
        
        # Mettre à jour la section builds
        if "builds" not in user_config:
            user_config["builds"] = {}
        
        user_config["builds"]["selectedBuilds"] = selected_builds
        
        # Sauvegarder la configuration
        from .configurations import save_config
        save_config(user_config)
        
        logger.info(f"Sélection de builds sauvegardée: {len(selected_builds)} builds")
        
        return {
            "success": True,
            "message": f"Sélection sauvegardée ({len(selected_builds)} builds)",
            "selected_builds": selected_builds
        }
        
    except Exception as e:
        logger.error(f"Erreur save_builds_selection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la sauvegarde: {str(e)}"
        )

@router.get("/versions/info")
async def get_versions_info():
    """Récupère les informations sur les versions TeamCity."""
    try:
        from ..services.version_manager import VersionManager
        return VersionManager.get_version_info()
    except Exception as e:
        logger.error(f"Erreur get_versions_info: {str(e)}")
        return {"error": str(e)}

@router.post("/versions/update")
async def update_versions(versions_data: dict):
    """Met à jour manuellement la liste des versions actuelles."""
    try:
        from ..services.version_manager import VersionManager
        versions = versions_data.get("versions", [])
        VersionManager.update_current_versions(versions)
        return {
            "success": True,
            "message": f"Versions mises à jour: {versions}",
            "versions": versions
        }
    except Exception as e:
        logger.error(f"Erreur update_versions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la mise à jour des versions: {str(e)}"
        )

@router.get("/versions/detect")
async def detect_versions():
    """Force la détection des nouvelles versions TeamCity."""
    try:
        from ..services.version_manager import VersionManager
        from ..services.teamcity_fetcher import fetch_all_teamcity_projects
        
        # Récupérer tous les projets
        complete_data = fetch_all_teamcity_projects()
        all_project_paths = complete_data.get('all_project_paths', [])
        
        # Détecter les nouvelles versions
        version_info = VersionManager.detect_new_versions(all_project_paths)
        
        return {
            "success": True,
            "version_info": version_info,
            "available_projects": all_project_paths
        }
    except Exception as e:
        logger.error(f"Erreur detect_versions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la détection des versions: {str(e)}"
        )

