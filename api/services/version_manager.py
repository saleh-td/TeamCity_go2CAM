"""
Service pour gérer automatiquement les versions TeamCity.
Détecte les nouvelles versions et met à jour la configuration.
"""

import json
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class VersionManager:
    """Gestionnaire de versions TeamCity."""
    
    CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "versions_config.json")
    
    @staticmethod
    def load_versions_config() -> Dict[str, Any]:
        """Charge la configuration des versions."""
        try:
            if os.path.exists(VersionManager.CONFIG_PATH):
                with open(VersionManager.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Configuration par défaut
                default_config = {
                    "current_versions": ["GO2 Version 612", "GO2 Version New"],
                    "version_history": ["GO2 Version 6.09", "GO2 Version 6.10", "GO2 Version 6.11", "GO2 Version 612", "GO2 Version New"],
                    "auto_detect_new_versions": True,
                    "max_versions_to_show": 3,
                    "last_updated": datetime.now().isoformat(),
                    "notes": "Configuration par défaut des versions TeamCity"
                }
                VersionManager.save_versions_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration des versions: {e}")
            return {}
    
    @staticmethod
    def save_versions_config(config: Dict[str, Any]):
        """Sauvegarde la configuration des versions."""
        try:
            os.makedirs(os.path.dirname(VersionManager.CONFIG_PATH), exist_ok=True)
            with open(VersionManager.CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration des versions: {e}")
    
    @staticmethod
    def get_current_versions() -> List[str]:
        """Retourne la liste des versions actuelles à afficher."""
        config = VersionManager.load_versions_config()
        return config.get("current_versions", ["GO2 Version 612", "GO2 Version New"])
    
    @staticmethod
    def detect_new_versions(available_projects: List[str]) -> Dict[str, Any]:
        """
        Détecte automatiquement les nouvelles versions TeamCity.
        
        Args:
            available_projects: Liste de tous les projets disponibles dans TeamCity
            
        Returns:
            Dict avec les nouvelles versions détectées et les actions recommandées
        """
        config = VersionManager.load_versions_config()
        current_versions = config.get("current_versions", [])
        version_history = config.get("version_history", [])
        auto_detect = config.get("auto_detect_new_versions", True)
        
        # Filtrer les projets qui ressemblent à des versions GO2
        go2_versions = [p for p in available_projects if "GO2 Version" in p]
        
        # Trouver les nouvelles versions
        new_versions = [v for v in go2_versions if v not in version_history]
        
        # Trouver les versions manquantes dans l'historique
        missing_in_history = [v for v in go2_versions if v not in version_history]
        
        # Trouver les versions actuelles qui n'existent plus
        obsolete_versions = [v for v in current_versions if v not in go2_versions]
        
        # Recommandations automatiques
        recommendations = []
        
        if new_versions:
            recommendations.append(f"Nouvelles versions détectées: {', '.join(new_versions)}")
            
            if auto_detect:
                # Ajouter automatiquement les nouvelles versions à l'historique
                version_history.extend(new_versions)
                version_history = list(set(version_history))  # Supprimer les doublons
                
                # Mettre à jour les versions actuelles (garder les plus récentes)
                max_versions = config.get("max_versions_to_show", 3)
                sorted_versions = sorted(go2_versions, reverse=True)  # Tri par ordre alphabétique inverse
                current_versions = sorted_versions[:max_versions]
                
                recommendations.append(f"Versions actuelles mises à jour: {', '.join(current_versions)}")
        
        if obsolete_versions:
            recommendations.append(f"Versions obsolètes détectées: {', '.join(obsolete_versions)}")
        
        # Mettre à jour la configuration si nécessaire
        if auto_detect and (new_versions or obsolete_versions):
            config.update({
                "current_versions": current_versions,
                "version_history": version_history,
                "last_updated": datetime.now().isoformat()
            })
            VersionManager.save_versions_config(config)
        
        return {
            "new_versions": new_versions,
            "obsolete_versions": obsolete_versions,
            "missing_in_history": missing_in_history,
            "current_versions": current_versions,
            "recommendations": recommendations,
            "auto_updated": auto_detect and (new_versions or obsolete_versions)
        }
    
    @staticmethod
    def update_current_versions(versions: List[str]):
        """Met à jour manuellement la liste des versions actuelles."""
        config = VersionManager.load_versions_config()
        config["current_versions"] = versions
        config["last_updated"] = datetime.now().isoformat()
        VersionManager.save_versions_config(config)
        logger.info(f"Versions actuelles mises à jour: {versions}")
    
    @staticmethod
    def get_version_info() -> Dict[str, Any]:
        """Retourne les informations sur les versions."""
        config = VersionManager.load_versions_config()
        return {
            "current_versions": config.get("current_versions", []),
            "version_history": config.get("version_history", []),
            "auto_detect": config.get("auto_detect_new_versions", True),
            "max_versions": config.get("max_versions_to_show", 3),
            "last_updated": config.get("last_updated", ""),
            "config_path": VersionManager.CONFIG_PATH
        } 