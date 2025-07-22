import json
import traceback
from typing import Dict, List
import logging
from ..database.config import execute_query
from ..models.schemas import BuildResponse, Project, Category, BuildsResponse


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BuildService:
    @staticmethod
    def get_control_panel() -> BuildsResponse:
        """Lit la table control_panel, parse le JSON de la colonne build, et retourne la liste des builds."""
        try:
            logger.info("Lecture de la table control_panel (mode compatibilité)")
            query = "SELECT * FROM control_panel"
            results = execute_query(query)
            builds = []
            for row in results:
                build_json = row['build']
                try:
                    build_data = json.loads(build_json)
                    attributes = build_data.get('@attributes', {})
                    builds.append(BuildResponse(
                        id=attributes.get('id', ''),
                        name=attributes.get('name', ''),
                        projectName=attributes.get('projectName', ''),
                        webUrl=attributes.get('webUrl', ''),
                        status=attributes.get('status', ''),
                        state=attributes.get('state', '')
                    ))
                except Exception as e:
                    logger.error(f"Erreur lors du parsing JSON pour la ligne id_build={row.get('id_build')}: {e}")
            # On retourne tout dans une seule catégorie "Legacy"
            return BuildsResponse(categories={
                "Legacy": {
                    "name": "Legacy",
                    "projects": [
                        {
                            "name": "All builds",
                            "builds": builds
                        }
                    ]
                }
            })
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des builds : {e}")
            traceback.print_exc()  # Affiche la stacktrace complète dans la console
            raise

    @staticmethod
    def get_parameters() -> Dict:
        """Récupère les paramètres de configuration."""
        try:
            logger.info("Tentative de récupération des paramètres")
            query = "SELECT * FROM parameters ORDER BY id DESC LIMIT 1"
            result = execute_query(query, fetch_one=True)
            logger.info("Paramètres récupérés avec succès")
            return result if result else {}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des paramètres : {str(e)}")
            return {
                "time": 60,
                "nameFirstColumn": "Projets 612",
                "nameSecondColumn": "Projets NEW",
                "nameThirdColumn": "Autres",
                "successColor": "#28a745",
                "failureColor": "#dc3545"
            } 