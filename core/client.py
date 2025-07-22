"""Client API pour TeamCity."""
import requests
import logging
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from teamcity_monitor.api.models.schemas import BuildResponse, Project, Category, BuildsResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class ApiClient:
    """Client pour l'API TeamCity Monitor."""

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or os.getenv("API_URL", "http://localhost:8000/api/v1")
        self.headers = {
            'Accept': 'application/json'
        }

    def get_builds(self) -> List[BuildResponse]:
        """Récupère la liste des builds depuis l'API TeamCity (endpoint /teamcity/builds)."""
        try:
            logger.debug(f"Récupération des builds depuis {self.api_url}/teamcity/builds")
            response = requests.get(
                f"{self.api_url}/teamcity/builds",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            builds = []
            builds_list = data["builds"] if isinstance(data, dict) and "builds" in data else data
            for build_data in builds_list:
                build = BuildResponse(
                    id=build_data.get("id", ""),
                    name=build_data.get("name", ""),
                    projectName=build_data.get("projectName", ""),
                    webUrl=build_data.get("webUrl", ""),
                    status=build_data.get("status", ""),
                    state=build_data.get("state", "")
                )
                builds.append(build)
            logger.info(f"Récupération réussie de {len(builds)} builds (TeamCity)")
            return builds
        except requests.RequestException as e:
            logger.error(f"Erreur lors de la récupération des builds : {e}")
            raise RuntimeError(f"Erreur lors de la récupération des builds : {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue : {e}")
            raise RuntimeError(f"Erreur lors du traitement des données : {e}")

    def get_parameters(self) -> Dict:
        """Récupère les paramètres de configuration depuis notre API."""
        try:
            response = requests.get(
                f"{self.api_url}/parameters",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Récupération réussie des paramètres")
            return data
        except requests.RequestException as e:
            logger.error(f"Erreur lors de la récupération des paramètres : {e}")
            return {
                "time": 60,
                "nameFirstColumn": "Projets 612",
                "nameSecondColumn": "Projets NEW",
                "nameThirdColumn": "Autres",
                "successColor": "#28a745",
                "failureColor": "#dc3545"
            }
        except Exception as e:
            logger.error(f"Erreur inattendue : {e}")
            return {
                "time": 60,
                "nameFirstColumn": "Projets 612",
                "nameSecondColumn": "Projets NEW",
                "nameThirdColumn": "Autres",
                "successColor": "#28a745",
                "failureColor": "#dc3545"
            }

