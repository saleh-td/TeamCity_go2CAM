from typing import Dict
import mysql.connector
from mysql.connector import pooling
import os
from dotenv import load_dotenv
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
logger.info(f"Tentative de chargement du fichier .env depuis : {env_path}")
load_dotenv(env_path)


db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')

logger.info("Variables d'environnement chargées :")
logger.info(f"DB_HOST: {db_host}")
logger.info(f"DB_PORT: {db_port}")
logger.info(f"DB_USER: {db_user}")
# Ne jamais logger le mot de passe
logger.info(f"DB_NAME: {db_name}")


DB_CONFIG: Dict[str, any] = {
    'host': db_host or 'localhost',
    'port': int(db_port or '3306'),
    'database': db_name or 'sentinel',
    'user': db_user or 'root',
    'password': db_password or 'Lpmdlp123',
    'pool_name': 'mypool',
    'pool_size': 5
}

logger.info(f"Configuration de la base de données : {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")


connection_pool = None
try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
    logger.info("Pool de connexions créé avec succès")
except Exception as e:
    logger.error(f"Erreur lors de la création du pool de connexions : {str(e)}")
    # Ne pas lever l'exception pour permettre un fonctionnement dégradé sans DB
    connection_pool = None

def get_db_connection():
    """Obtient une connexion depuis le pool. Retourne None si indisponible."""
    if connection_pool is None:
        logger.warning("Pool de connexions indisponible (mode dégradé)")
        return None
    try:
        return connection_pool.get_connection()
    except Exception as e:
        logger.error(f"Erreur lors de l'obtention d'une connexion : {str(e)}")
        return None

def execute_query(query: str, params: tuple = None, fetch_one: bool = False):
    """Exécute une requête SQL et retourne les résultats. Retourne des valeurs par défaut si la DB est indisponible."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            # Mode dégradé sans base de données
            return {} if fetch_one else []
        cursor = conn.cursor(dictionary=True)
        logger.debug(f"Exécution de la requête : {query}")
        cursor.execute(query, params or ())
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        return result
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête : {str(e)}")
        # En mode dégradé, retourner des valeurs sûres
        return {} if fetch_one else []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def execute_update(query: str, params: tuple = None):
    """Exécute une requête de mise à jour et retourne le nombre de lignes affectées. Retourne 0 si la DB est indisponible."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            # Mode dégradé sans base de données
            return 0
        cursor = conn.cursor()
        logger.debug(f"Exécution de la requête de mise à jour : {query}")
        cursor.execute(query, params or ())
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la mise à jour : {str(e)}")
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()