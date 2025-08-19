/**
 * Configuration centralisée pour les URLs API
 * Évite le hardcodage des URLs dans tous les fichiers
 */

// Configuration de base
const API_CONFIG = {
    // URL de base de l'API
    BASE_URL: 'http://localhost:8000',
    
    // Endpoints disponibles
    ENDPOINTS: {
        CONFIG: '/api/config',
        BUILDS_DASHBOARD: '/api/builds/dashboard',
        BUILDS_TREE: '/api/builds/tree',
        BUILDS_SELECTION: '/api/builds/tree/selection',
        AGENTS: '/api/agents'
    },
    
    // Configuration des requêtes
    REQUEST_TIMEOUT: 10000,  // 10 secondes
    RETRY_ATTEMPTS: 3
};

/**
 * Construit une URL complète pour un endpoint
 * @param {string} endpoint - L'endpoint à utiliser
 * @returns {string} - L'URL complète
 */
function buildApiUrl(endpoint) {
    if (!API_CONFIG.ENDPOINTS[endpoint]) {
        console.warn(`Endpoint ${endpoint} non trouvé dans la configuration`);
        return API_CONFIG.BASE_URL + endpoint;
    }
    return API_CONFIG.BASE_URL + API_CONFIG.ENDPOINTS[endpoint];
}

/**
 * Fonction utilitaire pour les requêtes fetch avec timeout
 * @param {string} url - L'URL à appeler
 * @param {object} options - Options de fetch
 * @returns {Promise} - Promise de la réponse
 */
async function apiRequest(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.REQUEST_TIMEOUT);
    
    try {
        const response = await fetch(url, {
            signal: controller.signal,
            ...options
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

// Export global pour utilisation dans tous les fichiers
window.API_CONFIG = API_CONFIG;
window.buildApiUrl = buildApiUrl;
window.apiRequest = apiRequest;
