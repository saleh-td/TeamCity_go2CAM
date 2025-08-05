"""
Modèle moderne pour la sélection utilisateur
Remplace le système médiocre de fichiers JSON hardcodés
Compatible avec MySQL existant
"""
import mysql.connector
from datetime import datetime
import json
from typing import List, Dict, Any, Optional
import logging
from ..database.config import get_db_connection, execute_query, execute_update

logger = logging.getLogger(__name__)

class UserBuildSelection:
    """
    Modèle moderne pour stocker les sélections de builds utilisateur
    Remplace user_config.json hardcodé - Compatible MySQL
    """
    
    @staticmethod
    def create_table():
        """Crée la table si elle n'existe pas"""
        query = """
        CREATE TABLE IF NOT EXISTS user_build_selections (
            build_type_id VARCHAR(255) PRIMARY KEY,
            project_name VARCHAR(255) NOT NULL,
            build_name VARCHAR(500) NOT NULL,
            is_selected BOOLEAN DEFAULT TRUE,
            selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            user_notes TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        try:
            execute_update(query)
            logger.info("Table user_build_selections créée/vérifiée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la création de la table user_build_selections: {e}")
            raise
    
    @staticmethod
    def get_selected_builds() -> List[str]:
        """Récupère tous les builds sélectionnés"""
        try:
            query = "SELECT build_type_id FROM user_build_selections WHERE is_selected = TRUE"
            results = execute_query(query)
            return [row['build_type_id'] for row in results]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des builds sélectionnés: {e}")
            return []
    
    @staticmethod
    def get_build_info(build_type_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un build spécifique"""
        try:
            query = """
            SELECT build_type_id, project_name, build_name, is_selected 
            FROM user_build_selections 
            WHERE build_type_id = %s
            """
            result = execute_query(query, (build_type_id,), fetch_one=True)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos du build {build_type_id}: {e}")
            return None
    
    @staticmethod
    def update_selection(build_type_id: str, project_name: str, build_name: str, is_selected: bool) -> bool:
        """Met à jour ou insère une sélection"""
        try:
            # Vérifier si existe
            check_query = "SELECT build_type_id FROM user_build_selections WHERE build_type_id = %s"
            existing = execute_query(check_query, (build_type_id,), fetch_one=True)
            
            if existing:
                # Mettre à jour
                update_query = """
                UPDATE user_build_selections 
                SET project_name = %s, build_name = %s, is_selected = %s, last_updated = NOW()
                WHERE build_type_id = %s
                """
                execute_update(update_query, (project_name, build_name, is_selected, build_type_id))
            else:
                # Insérer
                insert_query = """
                INSERT INTO user_build_selections (build_type_id, project_name, build_name, is_selected)
                VALUES (%s, %s, %s, %s)
                """
                execute_update(insert_query, (build_type_id, project_name, build_name, is_selected))
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la sélection: {e}")
            return False
    
    @staticmethod
    def bulk_update_selections(selected_build_ids: List[str], all_builds: List[Dict[str, Any]]) -> bool:
        """Met à jour toutes les sélections en une fois"""
        try:
            # Supprimer toutes les anciennes sélections
            execute_update("DELETE FROM user_build_selections")
            
            # Insérer les nouvelles sélections
            for build in all_builds:
                build_id = build.get("buildTypeId")
                if build_id:
                    UserBuildSelection.update_selection(
                        build_id,
                        build.get("projectName", "Unknown"),
                        build.get("name", build_id),
                        build_id in selected_build_ids
                    )
            
            logger.info(f"Mise à jour en lot réussie: {len(selected_build_ids)} builds sélectionnés")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour en lot: {e}")
            return False
    
    @staticmethod
    def clear_all_selections() -> bool:
        """Supprime toutes les sélections"""
        try:
            execute_update("DELETE FROM user_build_selections")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des sélections: {e}")
            return False

class UserPreferences:
    """
    Préférences générales de l'utilisateur
    Remplace dashboard_config.json hardcodé - Compatible MySQL
    """
    
    @staticmethod
    def create_table():
        """Crée la table si elle n'existe pas"""
        query = """
        CREATE TABLE IF NOT EXISTS user_preferences (
            preference_key VARCHAR(255) PRIMARY KEY,
            preference_value JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        try:
            execute_update(query)
            logger.info("Table user_preferences créée/vérifiée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la création de la table user_preferences: {e}")
            raise
    
    @staticmethod
    def get_preference(key: str, default_value: Any = None) -> Any:
        """Récupère une préférence"""
        try:
            query = "SELECT preference_value FROM user_preferences WHERE preference_key = %s"
            result = execute_query(query, (key,), fetch_one=True)
            
            if result:
                return json.loads(result['preference_value']) if isinstance(result['preference_value'], str) else result['preference_value']
            
            # Retourner la valeur par défaut si elle existe
            if key in DEFAULT_USER_PREFERENCES:
                return DEFAULT_USER_PREFERENCES[key]
            
            return default_value
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la préférence {key}: {e}")
            return default_value
    
    @staticmethod
    def set_preference(key: str, value: Any) -> bool:
        """Définit une préférence"""
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            
            # Vérifier si existe
            check_query = "SELECT preference_key FROM user_preferences WHERE preference_key = %s"
            existing = execute_query(check_query, (key,), fetch_one=True)
            
            if existing:
                # Mettre à jour
                update_query = "UPDATE user_preferences SET preference_value = %s, updated_at = NOW() WHERE preference_key = %s"
                execute_update(update_query, (json_value, key))
            else:
                # Insérer
                insert_query = "INSERT INTO user_preferences (preference_key, preference_value) VALUES (%s, %s)"
                execute_update(insert_query, (key, json_value))
            
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la définition de la préférence {key}: {e}")
            return False
    
    @staticmethod
    def get_all_preferences() -> Dict[str, Any]:
        """Récupère toutes les préférences"""
        try:
            query = "SELECT preference_key, preference_value FROM user_preferences"
            results = execute_query(query)
            
            preferences = DEFAULT_USER_PREFERENCES.copy()
            for row in results:
                key = row['preference_key']
                value = json.loads(row['preference_value']) if isinstance(row['preference_value'], str) else row['preference_value']
                preferences[key] = value
            
            return preferences
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des préférences: {e}")
            return DEFAULT_USER_PREFERENCES.copy()

# Configuration par défaut moderne
DEFAULT_USER_PREFERENCES = {
    "dashboard_layout": {
        "columns": "auto",  # auto, 1, 2, 3
        "theme": "dark",
        "auto_refresh_interval": 120000,  # 2 minutes
        "show_agent_indicators": True
    },
    "build_display": {
        "show_build_details": True,
        "group_by_project": True,
        "show_status_icons": True,
        "extract_readable_names": True
    },
    "notifications": {
        "enable_browser_notifications": False,
        "notify_on_failure": True,
        "notify_on_success": False
    }
}
