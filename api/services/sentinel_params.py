import os
import logging
from typing import Dict, List, Any, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

SENTINEL_DATABASE_URL = "mysql+pymysql://root:Lpmdlp123@localhost:3306/sentinel"

def get_sentinel_parameters() -> Dict[str, str]:
    """
    Récupère les paramètres depuis la base sentinel (ancien système).
    Retourne les noms de colonnes dynamiques configurés par l'utilisateur.
    """
    try:
        engine = create_engine(SENTINEL_DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM parameters LIMIT 1"))
            row = result.fetchone()
            
            if row:
                first_col = row.nameFirstColumn or '612'
                third_col = row.nameThirdColumn or 'New'
                if first_col == '610':
                    first_col = '612'
                if third_col == '611':
                    third_col = 'New'
                
                return {
                    'nameFirstColumn': first_col,
                    'nameSecondColumn': row.nameSecondColumn or '10', 
                    'nameThirdColumn': third_col,
                    'time': str(row.time or 60),
                    'successColor': row.successColor or '#28a745',
                    'failureColor': row.failureColor or '#dc3545'
                }
            else:
                return {
                    'nameFirstColumn': '612',
                    'nameSecondColumn': '10',
                    'nameThirdColumn': 'New', 
                    'time': '60',
                    'successColor': '#28a745',
                    'failureColor': '#dc3545'
                }
                
    except Exception as e:
        logger.error(f"Erreur récupération paramètres sentinel: {e}")
        return {
            'nameFirstColumn': '612',
            'nameSecondColumn': '10',
            'nameThirdColumn': 'New',
            'time': '60', 
            'successColor': '#28a745',
            'failureColor': '#dc3545'
        }

def group_builds_by_project_all(builds: List[Dict[str, Any]]) -> dict:
    """
    Regroupe tous les builds par projet (projectName ou chemin), retourne {nom_du_projet: [builds]}.
    """
    projects = {}
    for build in builds:
        project_name = build.get('projectName', '')
        parts = project_name.split(' / ')
        path_title = '/'.join(parts[1:]) if len(parts) > 1 else project_name
        if path_title not in projects:
            projects[path_title] = []
        projects[path_title].append(build)
    return projects


def classify_builds_by_sentinel_logic(builds: List[Dict[str, Any]], params: Dict[str, str]) -> Dict[str, dict]:
    """
    Classe les builds dans les colonnes, puis regroupe par projet (tous les builds du projet).
    Retourne {colonne: {nom_du_projet: [builds]}}
    """
    first_column = params['nameFirstColumn']
    second_column = params['nameSecondColumn'] 
    third_column = params['nameThirdColumn']
    
    # Initialiser les colonnes
    columns = {
        first_column: [],
        second_column: [],
        third_column: [],
        'other': []
    }
    
    for build in builds:
        build_type_id = build.get('buildTypeId', '') 
        parts = build_type_id.split('_')
        first_element = parts[0] if parts else build_type_id
        if first_column in first_element:
            columns[first_column].append(build)
        elif second_column in first_element:
            columns[second_column].append(build)
        elif third_column in first_element:
            columns[third_column].append(build)
        else:
            columns['other'].append(build)
    
    # Regrouper par projet (tous les builds du projet)
    for col in columns:
        columns[col] = group_builds_by_project_all(columns[col])
    
    logger.info(f"Classification terminée (groupe complet par projet):")
    logger.info(f"  {first_column}: {len(columns[first_column])} projets")
    logger.info(f"  {second_column}: {len(columns[second_column])} projets") 
    logger.info(f"  {third_column}: {len(columns[third_column])} projets")
    logger.info(f"  other: {len(columns['other'])} projets")
    
    return columns

def get_dynamic_build_classification(builds: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, List[Dict[str, Any]]]]:
    """
    Fonction principale qui :
    1. Récupère les paramètres dynamiques depuis sentinel
    2. Classe les builds selon ces paramètres
    3. Retourne les paramètres et la classification
    """
    params = get_sentinel_parameters()
    
    classified_builds = classify_builds_by_sentinel_logic(builds, params)
    
    return params, classified_builds 