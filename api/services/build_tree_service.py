"""
Service pour gérer l'arborescence des builds TeamCity.
Reproduit la structure hiérarchique de TeamCity pour la configuration utilisateur.
"""

import logging
from typing import Dict, List, Any, Optional
from .teamcity_fetcher import fetch_all_teamcity_builds

logger = logging.getLogger(__name__)

class BuildTreeService:
    """Service pour créer et gérer l'arborescence des builds TeamCity."""
    
    @staticmethod
    def get_builds_tree() -> Dict[str, Any]:
        """
        Récupère et organise tous les builds en arborescence hiérarchique.
        Inclut TOUS les projets et sous-projets, même ceux sans builds.
        
        Returns:
            Dict contenant l'arborescence des builds organisée par projet/sous-projet
        """
        try:
            print(f"\n=== SERVICE ARBRE - DÉBUT ===")
            
            # Récupérer TOUS les projets et buildTypes depuis TeamCity
            from .teamcity_fetcher import fetch_all_teamcity_projects
            complete_data = fetch_all_teamcity_projects()
            
            projects_data = complete_data.get('projects', [])
            buildtypes_data = complete_data.get('buildtypes', [])
            all_project_paths = complete_data.get('all_project_paths', [])
            
            print(f"Service arbre: {len(projects_data)} projets, {len(buildtypes_data)} buildTypes, {len(all_project_paths)} chemins uniques")
            
            if not all_project_paths:
                print("AUCUN projet récupéré depuis TeamCity")
                return {"projects": {}, "total_builds": 0}
            
            # Construire l'arborescence complète avec TOUS les projets
            tree = BuildTreeService._build_complete_tree(all_project_paths, buildtypes_data)
            
            print(f"Service arbre: Arborescence créée avec {len(tree['projects'])} projets principaux")
            return tree
            
        except Exception as e:
            print(f"ERREUR Service arbre: {e}")
            return {"projects": {}, "total_builds": 0}
    
    @staticmethod
    def get_all_builds_tree() -> Dict[str, Any]:
        """
        Récupère l'arborescence complète avec TOUS les projets TeamCity actifs.
        Version filtrée qui exclut les projets archivés et inactifs.
        
        Returns:
            Dict contenant l'arborescence complète (projets actifs uniquement)
        """
        try:
            print(f"\n=== SERVICE ARBRE COMPLET (ACTIFS) - DÉBUT ===")
            
            # Utiliser la version optimisée qui fonctionnait avant
            from .teamcity_fetcher import fetch_all_teamcity_projects_optimized
            complete_data = fetch_all_teamcity_projects_optimized()
            
            projects_data = complete_data.get('projects', [])
            buildtypes_data = complete_data.get('buildtypes', [])
            all_project_paths = complete_data.get('all_project_paths', [])
            
            print(f"Service arbre complet: {len(projects_data)} projets actifs, {len(buildtypes_data)} buildTypes actifs, {len(all_project_paths)} chemins uniques")
            
            if not all_project_paths:
                print("AUCUN projet actif récupéré depuis TeamCity")
                return {"projects": {}, "total_builds": 0}
            
            # Construire l'arborescence complète avec les projets actifs uniquement
            tree = BuildTreeService._build_complete_tree(all_project_paths, buildtypes_data)
            
            print(f"Service arbre complet: Arborescence créée avec {len(tree['projects'])} projets principaux actifs")
            return tree
            
        except Exception as e:
            print(f"ERREUR Service arbre complet: {e}")
            return {"projects": {}, "total_builds": 0}
    
    @staticmethod
    def get_filtered_builds_tree() -> Dict[str, Any]:
        """
        Récupère l'arborescence filtrée avec seulement les projets principaux actuels.
        Optimisé pour la page de configuration avec détection automatique des nouvelles versions.
        
        Returns:
            Dict contenant l'arborescence filtrée
        """
        try:
            print(f"\n=== SERVICE ARBRE FILTRÉ - DÉBUT ===")
            
            # Récupérer UNIQUEMENT les buildTypes des versions actuelles (version ultra-optimisée)
            from .teamcity_fetcher import fetch_current_versions_buildtypes
            complete_data = fetch_current_versions_buildtypes()
            
            projects_data = []  # Pas besoin des projets séparés
            buildtypes_data = complete_data.get('buildtypes', [])
            all_project_paths = complete_data.get('all_project_paths', [])
            
            print(f"Service arbre filtré: {len(buildtypes_data)} buildTypes filtrés, {len(all_project_paths)} chemins uniques")
            
            if not all_project_paths:
                print("AUCUN projet récupéré depuis TeamCity")
                return {"projects": {}, "total_builds": 0}
            
            # Construire l'arborescence complète
            complete_tree = BuildTreeService._build_complete_tree(all_project_paths, buildtypes_data)
            
            # Utiliser le gestionnaire de versions pour détecter les nouvelles versions
            from .version_manager import VersionManager
            
            # Détecter les nouvelles versions
            version_info = VersionManager.detect_new_versions(list(complete_tree["projects"].keys()))
            
            if version_info["recommendations"]:
                print("=== DÉTECTION DE VERSIONS ===")
                for rec in version_info["recommendations"]:
                    print(f"  - {rec}")
            
            # Utiliser les versions actuelles (mises à jour automatiquement si nécessaire)
            current_versions = version_info["current_versions"]
            
            # Filtrer pour ne garder que les projets principaux actuels
            filtered_projects = {}
            
            for project_name in current_versions:
                if project_name in complete_tree["projects"]:
                    filtered_projects[project_name] = complete_tree["projects"][project_name]
                    print(f"Projet ajouté au filtre: {project_name}")
                else:
                    print(f"ATTENTION: Projet {project_name} non trouvé dans les données TeamCity")
            
            # Compter les builds dans les projets filtrés
            total_builds = 0
            for project_data in filtered_projects.values():
                total_builds += BuildTreeService._count_builds_in_project(project_data)
            
            filtered_tree = {
                "projects": filtered_projects,
                "total_builds": total_builds,
                "version_info": version_info
            }
            
            print(f"Service arbre filtré: Arborescence créée avec {len(filtered_projects)} projets principaux")
            return filtered_tree
            
        except Exception as e:
            print(f"ERREUR Service arbre filtré: {e}")
            return {"projects": {}, "total_builds": 0}
    
    @staticmethod
    def _count_builds_in_project(project_data: Dict[str, Any]) -> int:
        """Compte récursivement tous les builds dans un projet et ses sous-projets."""
        count = len(project_data.get("builds", []))
        
        for subproject_data in project_data.get("subprojects", {}).values():
            count += BuildTreeService._count_builds_in_project(subproject_data)
        
        return count
    
    @staticmethod
    def _create_tree_from_builds(builds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Crée l'arborescence à partir d'une liste de builds déjà filtrée.
        
        Args:
            builds: Liste de builds déjà filtrée
            
        Returns:
            Dict contenant l'arborescence des builds
        """
        try:
            if not builds:
                logger.warning("Aucun build fourni pour créer l'arborescence")
                return {"projects": {}, "total_builds": 0}
            
            # Organiser les builds en arborescence
            tree = BuildTreeService._organize_builds_hierarchy(builds)
            
            logger.info(f"Arborescence créée avec {len(tree['projects'])} projets principaux")
            return tree
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'arborescence: {e}")
            return {"projects": {}, "total_builds": 0}
    
    @staticmethod
    def _organize_builds_hierarchy(builds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Organise les builds en structure hiérarchique basée sur projectName (découpé par ' / ').
        Ajoute des logs détaillés pour le debug.
        """
        import pprint
        projects = {}
        total_builds = 0

        print(f"=== DEBUG: Début construction arborescence avec {len(builds)} builds ===")

        for build in builds:
            project_name = build.get('projectName', '')
            build_id = build.get('buildTypeId', '')
            if not project_name:
                print(f"WARNING: Build sans projectName: {build_id}")
                continue
            # Découper la hiérarchie TeamCity réelle
            hierarchy = project_name.split(' / ')
            print(f"DEBUG: Build {build_id} -> hiérarchie extraite: {hierarchy}")
            if not hierarchy:
                print(f"WARNING: Build {build_id} avec projectName vide après split: {project_name}")
                continue
            BuildTreeService._add_build_to_tree_by_projectname(projects, hierarchy, build)
            total_builds += 1

        # Log structure finale pour chaque projet principal
        print(f"\n=== DEBUG: Structure finale de l'arborescence ===")
        for proj, data in projects.items():
            sub_count = len(data.get('subprojects', {}))
            build_count = len(data.get('builds', []))
            print(f"INFO: Projet '{proj}': {sub_count} sous-projets, {build_count} builds à la racine")
            if sub_count == 0 and build_count == 0:
                print(f"WARNING: Projet '{proj}' sans sous-projets ni builds !")
            print(f"DEBUG: Structure projet '{proj}':")
            pprint.pprint(data)
            print("---")

        print(f"INFO: Arborescence finale : {len(projects)} projets principaux, {total_builds} builds au total.")
        return {
            "projects": projects,
            "total_builds": total_builds
        }

    @staticmethod
    def _add_build_to_tree_by_projectname(projects: Dict[str, Any], hierarchy: List[str], build: Dict[str, Any]):
        """
        Ajoute un build à l'arborescence selon la hiérarchie extraite de projectName. Ajoute des logs si anomalie.
        """
        current_level = projects
        for idx, level in enumerate(hierarchy):
            if not level:
                print(f"WARNING: Niveau vide dans la hiérarchie: {hierarchy} pour build {build.get('buildTypeId', '')}")
                continue
            if level not in current_level:
                current_level[level] = {
                    "name": level,
                    "subprojects": {},
                    "builds": []
                }
            if idx == len(hierarchy) - 1:
                # Dernier niveau : on ajoute le build ici
                build_info = {
                    "id": build.get("buildTypeId", ""),
                    "name": build.get("name", build.get("buildTypeId", "")),
                    "buildTypeId": build.get("buildTypeId", ""),
                    "status": build.get("status", "UNKNOWN"),
                    "state": build.get("state", "finished"),
                    "webUrl": build.get("webUrl", ""),
                    "projectName": build.get("projectName", ""),
                    "selected": False
                }
                current_level[level]["builds"].append(build_info)
                print(f"DEBUG: Ajouté build {build_info['id']} dans {hierarchy}")
            current_level = current_level[level]["subprojects"]
    
    @staticmethod
    def _parse_build_hierarchy(buildtype_id: str, project_name: str) -> Optional[Dict[str, Any]]:
        """
        Parse un buildTypeId pour extraire la hiérarchie.
        
        Exemples:
        - Go2Version612_ProductInstall_Meca_InstallGO2cam
        - Go2VersionNew_Plugins_AlignerTrimmingCam_MakeInstallers
        - InternalLibNew_GO2Dlls_TestIncrementalBuild
        """
        if not buildtype_id:
            return None
        
        # Diviser le buildTypeId en parties
        parts = buildtype_id.split('_')
        
        if len(parts) < 2:
            return None
        
        # Déterminer le projet racine
        main_project = BuildTreeService._get_main_project(parts[0])
        
        # Extraire les sous-projets et le nom du build
        subprojects = []
        build_name = parts[-1]  # Le dernier élément est généralement le nom du build
        
        # Traiter les parties intermédiaires comme des sous-projets
        for i in range(1, len(parts) - 1):
            subproject = BuildTreeService._format_subproject_name(parts[i])
            if subproject:
                subprojects.append(subproject)
        
        return {
            "main_project": main_project,
            "subprojects": subprojects,
            "build_name": BuildTreeService._format_build_name(build_name)
        }
    
    @staticmethod
    def _get_main_project(project_part: str) -> str:
        """Convertit la partie projet en nom lisible."""
        project_mapping = {
            "Go2Version612": "GO2 Version 612",
            "Go2VersionNew": "GO2 Version New",
            "InternalLibNew": "Internal Libraries New",
            "GO2camNew": "GO2cam New",
            "GO2DentalNew": "GO2 Dental New",
            "GO2DesignerNew": "GO2 Designer New",
            "GO2OperatorNew": "GO2 Operator New",
            "GO2ConnecticNew": "GO2 Connectic New",
            "GO2implantNew": "GO2 Implant New",
            "InstalleursNew": "Installeurs New",
            "WebServices": "Web Services",
            "TestCustomerJs": "Test Customer JS",
        }
        
        return project_mapping.get(project_part, project_part)
    
    @staticmethod
    def _format_subproject_name(subproject_part: str) -> str:
        """Convertit une partie de sous-projet en nom lisible."""
        subproject_mapping = {
            "ProductInstall": "Product Install",
            "ProductCompil": "Product Compil",
            "InternalLibraries": "Internal Libraries",
            "InternalExecutables": "Internal Executables",
            "PpTranslate": "PP Translate",
            "Plugins": "Plugins",
            "Solidworks": "Solidworks",
            "AlignerTrimmingCam": "Aligner Trimming Cam",
            "GrindingBlackbox": "Grinding Blackbox",
            "Casm": "Casm",
            "GO2Dlls": "GO2 Dlls",
            "Meca": "Meca",
            "Dental": "Dental",
            "GO2cam": "GO2cam",
            "GO2dental": "GO2dental",
            "GO2operator": "GO2operator",
            "GO2designer": "GO2designer",
            "GO2implant": "GO2implant",
            "GObot": "GObot",
        }
        
        return subproject_mapping.get(subproject_part, subproject_part)
    
    @staticmethod
    def _format_build_name(build_part: str) -> str:
        """Convertit une partie de build en nom lisible."""
        build_mapping = {
            "InstallGO2cam": "Install GO2cam",
            "InstallGO2designer": "Install GO2designer",
            "InstallGO2operator": "Install GO2operator",
            "InstallGO2dental": "Install GO2dental",
            "InstallGO2implant": "Install GO2implant",
            "TestGO2cam": "Test GO2cam",
            "TestGO2dental": "Test GO2dental",
            "TestGO2Dental": "Test GO2Dental",
            "TestGO2camPp": "Test GO2cam PP",
            "TestGO2DentalPp": "Test GO2Dental PP",
            "BuildDebug": "Build Debug",
            "BuildRelease": "Build Release",
            "PrepareInstall": "Prepare Install",
            "MakeInstallers": "Make Installers",
            "TestIncrementalBuild": "Test Incremental Build",
            "TestFullRebuild": "Test Full Rebuild",
            "IncrementalBuild": "Incremental Build",
            "DocumentationApiPp": "Documentation API PP",
            "UpdateResTradLex": "Update Res Trad Lex",
            "CommitOem": "Commit OEM",
            "Commit": "Commit",
            "NgTools": "NG Tools",
            "NgEncrypt": "NG Encrypt",
            "Build": "Build",
            "Test": "Test",
            "Testing": "Testing",
            "UpdateVARsArea": "Update VARs Area",
        }
        
        return build_mapping.get(build_part, build_part)
    
    @staticmethod
    def apply_user_selection(tree: Dict[str, Any], selected_builds: List[str]) -> Dict[str, Any]:
        """
        Applique la sélection utilisateur à l'arborescence.
        
        Args:
            tree: L'arborescence des builds
            selected_builds: Liste des buildTypeId sélectionnés
            
        Returns:
            L'arborescence avec les statuts de sélection mis à jour
        """
        def update_selection(node):
            if "builds" in node:
                for build in node["builds"]:
                    build["selected"] = build["buildTypeId"] in selected_builds
            
            if "subprojects" in node:
                for subproject in node["subprojects"].values():
                    update_selection(subproject)
        
        # Mettre à jour la sélection pour tous les projets
        for project in tree["projects"].values():
            update_selection(project)
        
        return tree
    
    @staticmethod
    def get_selected_builds_from_tree(tree: Dict[str, Any]) -> List[str]:
        """
        Extrait la liste des buildTypeId sélectionnés depuis l'arborescence.
        
        Args:
            tree: L'arborescence des builds
            
        Returns:
            Liste des buildTypeId sélectionnés
        """
        selected = []
        
        def collect_selected(node):
            if "builds" in node:
                for build in node["builds"]:
                    if build.get("selected", False):
                        selected.append(build["buildTypeId"])
            
            if "subprojects" in node:
                for subproject in node["subprojects"].values():
                    collect_selected(subproject)
        
        # Collecter les builds sélectionnés de tous les projets
        for project in tree["projects"].values():
            collect_selected(project)
        
        return selected 

    @staticmethod
    def _build_complete_tree(all_project_paths: List[str], buildtypes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Construit l'arborescence exactement comme TeamCity.
        Restaure la hiérarchie complète avec tous les niveaux.
        """
        projects = {}
        total_builds = 0
        
        # Organiser les buildTypes par hiérarchie complète
        for buildtype in buildtypes_data:
            project_name = buildtype.get('projectName', '')
            if project_name:
                project_parts = project_name.split(' / ')
                if len(project_parts) >= 1:
                    main_project = project_parts[0]
                    
                    # Créer le projet principal s'il n'existe pas
                    if main_project not in projects:
                        projects[main_project] = {
                            "name": main_project,
                            "subprojects": {},
                            "builds": []
                        }
                    
                    # Construire la hiérarchie complète
                    current_level = projects[main_project]
                    
                    # Parcourir tous les niveaux de la hiérarchie
                    for i, part in enumerate(project_parts[1:], 1):
                        if part not in current_level["subprojects"]:
                            current_level["subprojects"][part] = {
                                "name": part,
                                "subprojects": {},
                                "builds": []
                            }
                        current_level = current_level["subprojects"][part]
                    
                    # Ajouter le build au niveau final
                    build_info = {
                        "id": buildtype.get("buildTypeId", ""),
                        "name": buildtype.get("name", buildtype.get("buildTypeId", "")),
                        "buildTypeId": buildtype.get("buildTypeId", ""),
                        "status": buildtype.get("status", "UNKNOWN"),
                        "state": buildtype.get("state", "finished"),
                        "webUrl": buildtype.get("webUrl", ""),
                        "projectName": buildtype.get("projectName", ""),
                        "selected": True
                    }
                    current_level["builds"].append(build_info)
                    total_builds += 1
        
        print(f"Structure hiérarchique complète restaurée: {list(projects.keys())}")
        for project_name, project in projects.items():
            print(f"  {project_name}: {list(project['subprojects'].keys())}")
            for sub_name, sub_project in project['subprojects'].items():
                print(f"    {sub_name}: {list(sub_project['subprojects'].keys())}")
        
        return {
            "projects": projects,
            "total_builds": total_builds
        }
    
    @staticmethod
    def _add_project_path_to_tree(projects: Dict[str, Any], hierarchy: List[str], buildtypes: List[Dict[str, Any]]):
        """
        Ajoute un chemin de projet complet à l'arborescence, même s'il n'y a pas de builds.
        """
        current_level = projects
        
        # Créer tous les niveaux de la hiérarchie
        for idx, level in enumerate(hierarchy):
            if not level:
                continue
                
            if level not in current_level:
                current_level[level] = {
                    "name": level,
                    "subprojects": {},
                    "builds": []
                }
            
            # Si c'est le dernier niveau et qu'il y a des buildTypes, les ajouter
            if idx == len(hierarchy) - 1 and buildtypes:
                for buildtype in buildtypes:
                    build_info = {
                        "id": buildtype.get("buildTypeId", ""),
                        "name": buildtype.get("name", buildtype.get("buildTypeId", "")),
                        "buildTypeId": buildtype.get("buildTypeId", ""),
                        "status": buildtype.get("status", "UNKNOWN"),
                        "state": buildtype.get("state", "finished"),
                        "webUrl": buildtype.get("webUrl", ""),
                        "projectName": buildtype.get("projectName", ""),
                        "selected": True
                    }
                    current_level[level]["builds"].append(build_info)
            
            current_level = current_level[level]["subprojects"] 