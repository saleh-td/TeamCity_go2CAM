"""
Service moderne pour la gestion des sélections utilisateur
Remplace le système médiocre de fichiers JSON hardcodés
Compatible avec MySQL existant
"""
from typing import List, Dict, Any, Optional
from ..models.user_selection import UserBuildSelection, UserPreferences, DEFAULT_USER_PREFERENCES
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ModernUserService:
    """Service professionnel pour la gestion des sélections utilisateur"""
    
    def __init__(self):
        # Initialiser les tables si nécessaire
        self.initialize_tables()
    
    def initialize_tables(self):
        """Initialise les tables de base de données"""
        try:
            UserBuildSelection.create_table()
            UserPreferences.create_table()
            logger.info("Tables utilisateur initialisées avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des tables: {e}")
            raise
    
    # === GESTION DES SÉLECTIONS DE BUILDS ===
    
    def get_selected_builds(self) -> List[str]:
        """Récupère les IDs des builds sélectionnés"""
        return UserBuildSelection.get_selected_builds()
    
    def update_build_selection(self, build_type_id: str, project_name: str, 
                             build_name: str, is_selected: bool) -> bool:
        """Met à jour la sélection d'un build"""
        return UserBuildSelection.update_selection(build_type_id, project_name, build_name, is_selected)
    
    def bulk_update_selections(self, selected_build_ids: List[str], 
                             all_builds: List[Dict[str, Any]]) -> bool:
        """Met à jour toutes les sélections en une fois (plus efficace)"""
        return UserBuildSelection.bulk_update_selections(selected_build_ids, all_builds)
    
    def clear_all_selections(self) -> bool:
        """Supprime toutes les sélections"""
        return UserBuildSelection.clear_all_selections()
    
    # === GESTION DES PRÉFÉRENCES ===
    
    def get_user_preference(self, key: str, default_value: Any = None) -> Any:
        """Récupère une préférence utilisateur"""
        return UserPreferences.get_preference(key, default_value)
    
    def set_user_preference(self, key: str, value: Any) -> bool:
        """Définit une préférence utilisateur"""
        return UserPreferences.set_preference(key, value)
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Récupère toutes les préférences utilisateur"""
        return UserPreferences.get_all_preferences()
    
    # === MÉTHODES DE MIGRATION ===
    
    def migrate_from_json_config(self, json_config_path: str) -> bool:
        """Migre depuis l'ancien système JSON vers la base de données"""
        try:
            config_file = Path(json_config_path)
            if not config_file.exists():
                logger.warning(f"Fichier de migration non trouvé: {json_config_path}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                old_config = json.load(f)
            
            # Migrer les builds sélectionnés
            selected_builds = old_config.get("builds", {}).get("selectedBuilds", [])
            if selected_builds:
                logger.info(f"Migration de {len(selected_builds)} builds sélectionnés")
                
                # Créer des builds factices pour la migration
                fake_builds = []
                for build_id in selected_builds:
                    fake_builds.append({
                        "buildTypeId": build_id,
                        "projectName": "Migrated",
                        "name": build_id
                    })
                
                success = self.bulk_update_selections(selected_builds, fake_builds)
                if success:
                    logger.info("Migration réussie depuis JSON vers base de données")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la migration: {e}")
            return False
    
    def get_config_for_api(self) -> Dict[str, Any]:
        """Retourne la configuration au format attendu par l'API"""
        try:
            selected_builds = self.get_selected_builds()
            preferences = self.get_all_preferences()
            
            return {
                "builds": {
                    "selectedBuilds": selected_builds
                },
                "config": {
                    "builds": {
                        "selectedBuilds": selected_builds
                    }
                },
                "selectedBuilds": selected_builds,
                "preferences": preferences
            }
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la config API: {e}")
            return {
                "builds": {"selectedBuilds": []},
                "config": {"builds": {"selectedBuilds": []}},
                "selectedBuilds": [],
                "preferences": DEFAULT_USER_PREFERENCES.copy()
            }

# Instance singleton pour utilisation globale
user_service = ModernUserService()
