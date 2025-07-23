let currentBuilds = [];
let currentAgents = [];

// === GESTION DES MODALS ===
function showModal(type) {
    const modal = document.getElementById(`modal-${type}`);
    modal.classList.add('show');
    
    switch(type) {
        case 'success':
            fillBuildModal('success-builds', currentBuilds.filter(b => b.status?.toUpperCase() === 'SUCCESS'));
            break;
        case 'failure':
            fillBuildModal('failure-builds', currentBuilds.filter(b => b.status?.toUpperCase() === 'FAILURE'));
            break;
        case 'running':
            fillBuildModal('running-builds', currentBuilds.filter(b => b.state?.toLowerCase() === 'running' || b.state?.toLowerCase() === 'building'));
            break;
        case 'agents':
            fillAgentsModal();
            break; 
        case 'overview':
            fillOverviewModal();
            break;
    }
}

function closeModal(type) {
    const modal = document.getElementById(`modal-${type}`);
    modal.classList.remove('show');
}

function fillBuildModal(containerId, builds) {
    const container = document.getElementById(containerId);
    
    if (builds.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #7d8590; padding: 20px;">Aucun build trouvé</div>';
        return;
    }
    
    container.innerHTML = builds.map(build => `
        <div class="build-item">
            <div class="build-info">
                <div class="build-name">${build.name}</div>
                <div class="build-project">${build.projectName || 'Projet non défini'}</div>
            </div>
            <span class="build-status ${getStatusClass(build.status, build.state)}">
                ${getStatusText(build.status, build.state)}
            </span>
        </div>
    `).join('');
}

function fillAgentsModal() {
    const container = document.getElementById('agents-list');
    
    if (currentAgents.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #7d8590; padding: 20px;">Aucun agent disponible</div>';
        return;
    }
    
    container.innerHTML = currentAgents.map(agent => `
        <div class="agent-card">
            <div class="agent-name">${agent.name}</div>
            <div class="agent-status ${agent.status}">
                <span>●</span>
                ${agent.status === 'online' ? 'En ligne' : agent.status === 'busy' ? 'Occupé' : 'Hors ligne'}
            </div>
            ${agent.currentBuild ? `<div style="font-size: 11px; color: #7d8590; margin-top: 4px;">Build: ${agent.currentBuild}</div>` : ''}
        </div>
    `).join('');
}

function fillOverviewModal() {

    const stats = getDetailedStats();
    
    // Mettre à jour les statistiques dans le modal
    document.getElementById('overview-success-count').textContent = stats.success;
    document.getElementById('overview-failure-count').textContent = stats.failure;
    document.getElementById('overview-running-count').textContent = stats.running;
    document.getElementById('overview-agents-count').textContent = currentAgents.length;
    
    // Afficher les agents détaillés
    const agents = document.getElementById('overview-agents');
    const limitedAgents = currentAgents.slice(0, 6);
    agents.innerHTML = limitedAgents.map(agent => `
        <div class="agent-card">
            <div class="agent-name">${agent.name}</div>
            <div class="agent-status ${agent.status}">
                <span>●</span>
                ${agent.status === 'online' ? 'En ligne' : agent.status === 'busy' ? 'Occupé' : 'Hors ligne'}
            </div>
        </div>
    `).join('');
}

// === UTILITAIRES STATUT ===
function getStatusClass(status, state) {
    if (state?.toLowerCase() === 'running' || state?.toLowerCase() === 'building') return 'running';
    switch (status?.toUpperCase()) {
        case 'SUCCESS': return 'success';
        case 'FAILURE': return 'failure';
        default: return '';
    }
}

function getStatusText(status, state) {
    if (state?.toLowerCase() === 'running' || state?.toLowerCase() === 'building') return 'En cours';
    switch (status?.toUpperCase()) {
        case 'SUCCESS': return 'Réussi';
        case 'FAILURE': return 'Échoué';
        default: return 'Inconnu';
    }
}

function getDetailedStats() {
    return currentBuilds.reduce((acc, build) => {
        const status = build.status?.toUpperCase();
        const state = build.state?.toLowerCase();
        
        if (status === 'SUCCESS') acc.success++;
        else if (status === 'FAILURE') acc.failure++;
        else if (state === 'running' || state === 'building') acc.running++;
        else acc.other++;
        
        return acc;
    }, { success: 0, failure: 0, running: 0, other: 0 });
}

// === CLASSE PRINCIPALE DASHBOARD ===
class SimpleDashboard {
    constructor() {
        this.config = {
            first: null,
            second: null
        };
        this.allBuilds = [];
        this.selectedBuilds = [];
        this.init();
        this.startStatsMonitoring();
    }

    async init() {
        try {
            const [configResponse, buildsResponse, agentsResponse] = await Promise.all([
                fetch('http://localhost:8000/api/config'),
                fetch('http://localhost:8000/api/builds'),
                fetch('http://localhost:8000/api/agents')
            ]);
            
            const [configData, buildsData, agentsData] = await Promise.all([
                configResponse.json(),
                buildsResponse.json(),
                agentsResponse.json()
            ]);
            
            this.processConfiguration(configData);
            this.processBuilds(buildsData);
            this.processAgents(agentsData);
            
        } catch (error) {
            await this.loadConfiguration();
            await this.loadAndDisplayBuilds();
            await this.loadAndDisplayAgents();
        }
        
        this.startAutoRefresh();
    }

    processConfiguration(data) {
        const selectedBuilds = data.config?.builds?.selectedBuilds || data.selectedBuilds || [];
        this.selectedBuilds = selectedBuilds;
    }

    async loadConfiguration() {
        try {
            const response = await fetch('http://localhost:8000/api/config');
            const data = await response.json();
            this.processConfiguration(data);
        } catch (error) {
            this.selectedBuilds = [];
        }
    }

    processBuilds(data) {
        try {
            this.allBuilds = this.extractAllBuildsFromTree(data);
            
            if (this.selectedBuilds && this.selectedBuilds.length > 0) {
                this.allBuilds = this.allBuilds.filter(build => 
                    this.selectedBuilds.includes(build.buildTypeId)
                );
            } else {
                this.allBuilds = [];
            }
            
            currentBuilds = this.allBuilds;
            this.organizeAndDisplayBuilds();
            this.updateStats();
            
        } catch (error) {
            this.displayError();
        }
    }

    async loadAndDisplayBuilds() {
        try {
            const response = await fetch('http://localhost:8000/api/builds');
            const data = await response.json();
            this.processBuilds(data);
        } catch (error) {
            this.displayError();
        }
    }

    extractAllBuildsFromTree(data) {
        const allBuilds = data.builds || [];
        return allBuilds;
    }

    organizeAndDisplayBuilds() {
        let filteredBuilds = this.allBuilds;
        if (this.selectedBuilds.length > 0) {
            const missingBuilds = this.selectedBuilds.filter(selectedBuildId => {
                return !this.allBuilds.some(build => build.buildTypeId === selectedBuildId);
            });
            
            if (missingBuilds.length > this.selectedBuilds.length / 2) {
                filteredBuilds = this.allBuilds;
            } else {
                filteredBuilds = this.allBuilds.filter(build => {
                    return this.selectedBuilds.some(selectedBuildId => {
                        return build.buildTypeId === selectedBuildId;
                    });
                });
            }
        }

        if (filteredBuilds.length === 0 && this.selectedBuilds.length > 0) {
            filteredBuilds = this.allBuilds;
        }

        const buildsByProject = this.organizeBySelectedProjects(filteredBuilds);
        this.displayProjectsInColumns(buildsByProject);
        
        const totalFirst = Object.values(buildsByProject.first).reduce((sum, builds) => sum + builds.length, 0);
        const totalSecond = Object.values(buildsByProject.second).reduce((sum, builds) => sum + builds.length, 0);
        const totalThird = Object.values(buildsByProject.third).reduce((sum, builds) => sum + builds.length, 0);
        
        const hasThirdColumn = totalThird > 0;
        
        this.updateColumnCounts([{length: totalFirst}], [{length: totalSecond}], hasThirdColumn ? [{length: totalThird}] : [{length: 0}]);
        
        if (!hasThirdColumn) {
            this.hideThirdColumn();
        }
    }

    organizeBySelectedProjects(builds) {
        if (builds.length === 0) {
            return {
                first: {},
                second: {},
                third: {},
                firstTitle: "Aucun projet sélectionné",
                secondTitle: "Aucun projet sélectionné",
                thirdTitle: "Aucun projet sélectionné"
            };
        }

        const versions = this.detectVersions(builds);
        const firstVersion = versions[0] || "612";
        const secondVersion = versions[1] || "New";
        const thirdVersion = versions[2] || "Autres";
        
        const { buildsFirst, buildsSecond, buildsThird } = this.separateBuildsByVersion(builds, firstVersion, secondVersion, thirdVersion);

        const firstProjects = this.groupBuildsByProject(buildsFirst);
        const secondProjects = this.groupBuildsByProject(buildsSecond);
        const thirdProjects = this.groupBuildsByProject(buildsThird);

        let thirdTitle = `GO2 Version ${thirdVersion}`;
        
        if (thirdVersion === "WebServices") {
            thirdTitle = "Web Services";
        } else if (thirdVersion === "Autres" && buildsThird.length > 0) {
            const sampleBuild = buildsThird[0];
            if (sampleBuild.buildTypeId) {
                const projectName = this.extractProjectFromBuildId(sampleBuild.buildTypeId);
                if (projectName !== 'Autres') {
                    thirdTitle = projectName;
                }
            }
        }
        
        const result = {
            first: firstProjects,
            second: secondProjects,
            third: thirdProjects,
            firstTitle: `GO2 Version ${firstVersion}`,
            secondTitle: `GO2 Version ${secondVersion}`,
            thirdTitle: thirdTitle
        };

        return result;
    }

    extractProjectFromBuildId(buildTypeId) {
        // UTILISER LES VRAIS NOMS TEAMCITY - NE PAS INVENTER !
        
        // EXTRACTION DES VRAIS NOMS DE PROJETS TEAMCITY
        // Format attendu : "Go2Version612_ProductInstall_Meca_InstallGO2cam"
        
        if (buildTypeId.includes('Go2Version612')) {
            // Extraire le vrai nom du projet depuis buildTypeId
            const parts = buildTypeId.split('_');
            
            if (parts.length >= 3) {
                // Reconstruire le vrai nom : "GO2 Version 612 / Product Install / Meca"
                const version = parts[0].replace('Go2Version', 'GO2 Version ');
                const category = parts[1].replace(/([A-Z])/g, ' $1').trim(); // "Product Install"
                const subcategory = parts[2].replace(/([A-Z])/g, ' $1').trim(); // "Meca"
                return `${version} / ${category} / ${subcategory}`;
            }
            return 'GO2 Version 612';
        } else if (buildTypeId.includes('Go2VersionNew') || buildTypeId.includes('InstalleursNew')) {
            // Extraire le vrai nom du projet depuis buildTypeId
            const parts = buildTypeId.split('_');
            
            if (parts.length >= 3) {
                // Reconstruire le vrai nom : "GO2 Version New / Product Install / Meca"
                const version = parts[0].replace('Go2VersionNew', 'GO2 Version New');
                const category = parts[1].replace(/([A-Z])/g, ' $1').trim(); // "Product Install"
                const subcategory = parts[2].replace(/([A-Z])/g, ' $1').trim(); // "Meca"
                return `${version} / ${category} / ${subcategory}`;
            }
            return 'GO2 Version New';
        } else if (buildTypeId.includes('InternalLibNew')) {
            return 'GO2 Version New / Internal Libraries / GO2DIls';
        } else if (buildTypeId.includes('GO2DentalNew')) {
            return 'GO2 Version New / Product Install / Dental';
        } else if (buildTypeId.includes('GO2camNew')) {
            return 'GO2 Version New / Product Compil / GO2cam';
        } else if (buildTypeId.includes('WebServices') || buildTypeId.includes('GO2Portal') || buildTypeId.includes('Web')) {
            // ORGANISER LES WEB SERVICES HIÉRARCHIQUEMENT
            const parts = buildTypeId.split('_');
            if (parts.length >= 2) {
                const service = parts[1].replace(/([A-Z])/g, ' $1').trim(); // "GO2Portal", "GObot", etc.
                return `Web Services / ${service}`;
            }
            return 'Web Services';
        } else if (buildTypeId.includes('Portal') || buildTypeId.includes('API')) {
            // ORGANISER LES LEGACY PORTAL HIÉRARCHIQUEMENT
            const parts = buildTypeId.split('_');
            if (parts.length >= 2) {
                const service = parts[1].replace(/([A-Z])/g, ' $1').trim(); // "SynchroServers", etc.
                return `Web Services / ${service}`;
            }
            return 'Web Services';
        } else {
            return 'Autres';
        }
    }

    displayProjectsInColumns(buildsByProject) {
        // Vérifier si la 3ème colonne a du contenu
        const hasThirdColumn = Object.keys(buildsByProject.third).length > 0;
        
        // Mettre à jour les en-têtes avec les vrais noms de projets
        this.updateColumnHeaders(buildsByProject.firstTitle, buildsByProject.secondTitle, hasThirdColumn ? buildsByProject.thirdTitle : null);
        
        // Afficher colonne 1 avec les projets groupés
        this.displayBuildsInColumn('builds-612', buildsByProject.first);
        
        // Afficher colonne 2 avec les projets groupés
        this.displayBuildsInColumn('builds-new', buildsByProject.second);
        
        // Afficher colonne 3 seulement si elle a du contenu
        if (hasThirdColumn) {
            this.displayBuildsInColumn('builds-project3', buildsByProject.third);
            this.showThirdColumn();
        } else {
            this.hideThirdColumn();
        }
    }

    updateColumnHeaders(firstTitle = null, secondTitle = null, thirdTitle = null) {
        const title612 = document.getElementById('title-612');
        const titleNew = document.getElementById('title-new');
        const titleProject3 = document.getElementById('title-project3');
        
        if (title612) title612.textContent = firstTitle || 'Aucun projet';
        if (titleNew) titleNew.textContent = secondTitle || 'Aucun projet';
        if (titleProject3) titleProject3.textContent = thirdTitle || 'Aucun projet';
    }

    showThirdColumn() {
        const dashboardGrid = document.querySelector('.dashboard-grid');
        if (dashboardGrid) {
            dashboardGrid.classList.add('has-third-column');
        }
    }

    hideThirdColumn() {
        const dashboardGrid = document.querySelector('.dashboard-grid');
        if (dashboardGrid) {
            dashboardGrid.classList.remove('has-third-column');
        }
    }

    detectVersions(builds) {
        const versionCounts = {};
        
        builds.forEach(build => {
            if (build.buildTypeId) {
                // Chercher des patterns de version dans buildTypeId
                const patterns = [
                    /(\d{3,4})/g,  // 612, 613, etc.
                    /(New|NEW)/g,  // New
                    /(v\d+\.\d+)/g, // v2.1, etc.
                    /(\d+\.\d+)/g,  // 2.1, etc.
                ];
                
                for (const pattern of patterns) {
                    const matches = build.buildTypeId.match(pattern);
                    if (matches) {
                        matches.forEach(match => {
                            versionCounts[match] = (versionCounts[match] || 0) + 1;
                        });
                    }
                }
                
                // DÉTECTER LES WEB SERVICES
                if (build.buildTypeId.includes('WebServices') || build.buildTypeId.includes('GO2Portal') || 
                    build.buildTypeId.includes('Web') || build.buildTypeId.includes('Portal') || 
                    build.buildTypeId.includes('API')) {
                    versionCounts['WebServices'] = (versionCounts['WebServices'] || 0) + 1;
                }
            }
        });

        // Trier par nombre d'occurrences (décroissant)
        return Object.keys(versionCounts)
            .sort((a, b) => versionCounts[b] - versionCounts[a])
            .slice(0, 3); // Prendre les 3 plus fréquentes
    }



    separateBuildsByVersion(builds, firstVersion, secondVersion, thirdVersion) {
        const buildsFirst = [];
        const buildsSecond = [];
        const buildsThird = [];
        
        builds.forEach(build => {
            if (!build.buildTypeId) {
                return;
            }
            
            const buildTypeId = build.buildTypeId;
            let assigned = false;
            
            if (this.matchesVersion(buildTypeId, firstVersion)) {
                buildsFirst.push(build);
                assigned = true;
            } else if (this.matchesVersion(buildTypeId, secondVersion)) {
                buildsSecond.push(build);
                assigned = true;
            } else if (this.matchesVersion(buildTypeId, thirdVersion)) {
                buildsThird.push(build);
                assigned = true;
            }
            
            if (!assigned) {
                if (thirdVersion === "Autres") {
                    buildsThird.push(build);
                } else if (firstVersion === "Tous") {
                    buildsFirst.push(build);
                }
            }
        });
        
        return { buildsFirst, buildsSecond, buildsThird };
    }

    matchesVersion(buildTypeId, version) {
        if (version === "Aucun") return false;
        if (version === "Tous") return true;
        if (version === "Autres") return false;
        
        let result = false;
        
        if (version.match(/^\d{3,4}$/)) {
            result = buildTypeId.includes(version);
        } else if (version.toLowerCase() === "new") {
            result = buildTypeId.toLowerCase().includes("new");
        } else if (version === "WebServices") {
            result = buildTypeId.includes('WebServices') || buildTypeId.includes('GO2Portal') || 
                     buildTypeId.includes('Web') || buildTypeId.includes('Portal') || 
                     buildTypeId.includes('API');
        } else {
            result = buildTypeId.includes(version);
        }
        
        return result;
    }

    filterBuildsByVersion(builds, version) {
        if (version === "Aucun" || version === "Autres") {
            return [];
        }
        
        if (version === "Tous") {
            return builds;
        }
        
        return builds.filter(build => {
            if (!build.buildTypeId) return false;
            
            // Recherche exacte ou partielle du terme de version
            return build.buildTypeId.includes(version);
        });
    }

    displayBuildsInColumn(containerId, projectsByGroup) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        if (!projectsByGroup || Object.keys(projectsByGroup).length === 0) {
            container.innerHTML = '<div class="loading">Aucun build disponible</div>';
            return;
        }
        
        // Générer le HTML directement depuis les projets groupés
        const html = this.generateProjectsHTML(projectsByGroup);
        container.innerHTML = html;
    }

    groupBuildsByProject(builds) {
        const projects = {};
        
        builds.forEach(build => {
            // UTILISER LES TITRES COMPACTS ici aussi !
            const projectName = this.extractProjectFromBuildId(build.buildTypeId);
            if (!projects[projectName]) {
                projects[projectName] = [];
            }
            projects[projectName].push(build);
        });
        
        return projects;
    }

    generateProjectsHTML(buildsByProject) {
        let html = '';
        
        Object.keys(buildsByProject).forEach(projectName => {
            const builds = buildsByProject[projectName];
            
            html += `
                <div class="project-group">
                    <div class="project-header">
                        <h3 class="project-title">${projectName}</h3>
                        <span class="build-count">${builds.length}</span>
                    </div>
                    <div class="project-builds">
                        ${builds.map(build => this.generateBuildHTML(build)).join('')}
                    </div>
                </div>
            `;
        });
        
        return html;
    }

    generateBuildHTML(build) {
        const statusClass = this.getStatusClass(build.status, build.state);
        
        // UTILISER LE VRAI NOM DU BUILD
        let buildName = build.name || build.buildTypeId || 'Build';
        
        return `
            <div class="build-item ${statusClass}" onclick="window.open('${build.webUrl}', '_blank')">
                <div class="build-name">${buildName}</div>
            </div>
        `;
    }

    updateColumnCounts(builds612, buildsNew, buildsProject3) {
        const count612 = document.getElementById('count-612');
        const countNew = document.getElementById('count-new');
        const countProject3 = document.getElementById('count-project3');
        
        const count1 = Array.isArray(builds612) ? builds612.length : (builds612[0]?.length || 0);
        const count2 = Array.isArray(buildsNew) ? buildsNew.length : (buildsNew[0]?.length || 0);
        const count3 = Array.isArray(buildsProject3) ? buildsProject3.length : (buildsProject3[0]?.length || 0);
        
        if (count612) count612.textContent = count1;
        if (countNew) countNew.textContent = count2;
        if (countProject3) countProject3.textContent = count3;
        
        // Masquer le compteur de la colonne 3 si pas de builds
        if (countProject3) {
            countProject3.style.display = count3 > 0 ? 'block' : 'none';
        }
    }

    displayError() {
        const builds612 = document.getElementById('builds-612');
        const buildsNew = document.getElementById('builds-new');
        
        if (builds612) builds612.innerHTML = '<div class="loading">Erreur de chargement</div>';
        if (buildsNew) buildsNew.innerHTML = '<div class="loading">Erreur de chargement</div>';
        
        // Masquer la colonne 3 en cas d'erreur
        this.hideThirdColumn();
    }

    processAgents(data) {
        try {
            currentAgents = data.agents || [];
        } catch (error) {
            currentAgents = [];
        }
    }

    async loadAndDisplayAgents() {
        try {
            const response = await fetch('http://localhost:8000/api/agents');
            const data = await response.json();
            this.processAgents(data);
        } catch (error) {
            console.error('Erreur chargement agents:', error);
            currentAgents = [];
        }
    }

    startAutoRefresh() {
        // ⚡ OPTIMISATION : Rafraîchissement parallèle toutes les 120 secondes
        setInterval(async () => {
            try {
                // Charger TOUT en parallèle avec timeout
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
                
                const [configResponse, buildsResponse, agentsResponse] = await Promise.all([
                    fetch('http://localhost:8000/api/config', { signal: controller.signal }),
                    fetch('http://localhost:8000/api/builds', { signal: controller.signal }),
                    fetch('http://localhost:8000/api/agents', { signal: controller.signal })
                ]);
                
                clearTimeout(timeoutId);
                
                const [configData, buildsData, agentsData] = await Promise.all([
                    configResponse.json(),
                    buildsResponse.json(),
                    agentsResponse.json()
                ]);
                
                // Traiter les données
                this.processConfiguration(configData);
                this.processBuilds(buildsData);
                this.processAgents(agentsData);
                
            } catch (error) {
                // Fallback séquentiel silencieux
                try {
                    await this.loadConfiguration();
                    await this.loadAndDisplayBuilds();
                    this.loadAndDisplayAgents();
                } catch (fallbackError) {
                    // Ignorer les erreurs de fallback
                }
            }
        }, 120000); // 2 minutes
    }

    startStatsMonitoring() {
        setInterval(() => {
            this.updateStats();
        }, 5000);
    }

    updateStats() {
        const stats = this.getDetailedStats();
        
        document.getElementById('navbar-success-count').textContent = stats.success;
        document.getElementById('navbar-failure-count').textContent = stats.failure;
        document.getElementById('navbar-running-count').textContent = stats.running;
        document.getElementById('navbar-agents-count').textContent = currentAgents.length;
        
        this.updateAgentIndicators();
    }

    updateAgentIndicators() {
        const indicatorsContainer = document.getElementById('agent-indicators');
        if (!indicatorsContainer) return;
        
        // Vider les indicateurs existants
        indicatorsContainer.innerHTML = '';
        
        // Générer un point voyant pour chaque agent
        currentAgents.forEach(agent => {
            const indicator = document.createElement('div');
            indicator.className = `agent-indicator ${agent.status}`;
            indicator.setAttribute('data-agent-name', agent.name);
            indicator.title = `${agent.name} - ${this.getAgentStatusText(agent.status)}`;
            
            // Ajouter un événement de clic pour afficher les détails
            indicator.onclick = () => this.showAgentDetails(agent);
            
            indicatorsContainer.appendChild(indicator);
        });
    }

    getAgentStatusText(status) {
        switch (status) {
            case 'online': return 'En ligne';
            case 'offline': return 'Hors ligne';
            case 'busy': return 'Occupé';
            default: return 'Inconnu';
        }
    }

    showAgentDetails(agent) {
        // TODO: Implémenter une modal pour les détails de l'agent
    }

    getDetailedStats() {
        return this.allBuilds.reduce((acc, build) => {
            const status = build.status?.toUpperCase();
            const state = build.state?.toLowerCase();
            
            if (status === 'SUCCESS') acc.success++;
            else if (status === 'FAILURE') acc.failure++;
            else if (state === 'running' || state === 'building') acc.running++;
            else acc.other++;
            
            return acc;
        }, { success: 0, failure: 0, running: 0, other: 0 });
    }

    getStatusClass(status, state) {
        // Vérifier si des builds sont en cours
        if (state?.toLowerCase() === 'running' || state?.toLowerCase() === 'building') {
            console.log(`🔥 ANIMATION ! Build EN COURS: status="${status}", state="${state}"`);
            return 'running';
        }
        
        // Gérer les différents statuts
        const statusUpper = status?.toUpperCase();
        if (statusUpper === 'SUCCESS') {
            return 'success';
        } else if (statusUpper === 'FAILURE') {
            return 'failure';
        } else if (statusUpper === 'UNKNOWN') {
            return 'unknown'; // Affiché en bleu (builds non exécutés récemment)
        } else {
            return 'unknown';
        }
    }

    getStatusText(status, state) {
        if (state?.toLowerCase() === 'running' || state?.toLowerCase() === 'building') return 'En cours';
        switch (status?.toUpperCase()) {
            case 'SUCCESS': return 'Réussi';
            case 'FAILURE': return 'Échoué';
            default: return 'Inconnu';
        }
    }

    showRefreshIndicator() {
        const indicator = document.getElementById('refresh-indicator');
        indicator.classList.add('active');
        setTimeout(() => {
            indicator.classList.remove('active');
        }, 2000);
    }
}

// === ÉVÉNEMENTS ===
// Fermer modal en cliquant à l'extérieur
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
}

// === CONFIGURATION ===
function openConfigPage() {
    window.location.href = 'config.html';
}

// === DEBUG COMPLET ANIMATION ===
function debugAnimationComplete() {
    console.log('� === DEBUG ANIMATION ULTRA-COMPLET ===');
    console.log('Timestamp:', new Date().toLocaleString());
    
    // 1. VÉRIFIER LES DONNÉES BRUTES
    console.log('\n📊 === DONNÉES BRUTES ===');
    console.log('currentBuilds.length:', currentBuilds.length);
    console.log('currentBuilds array:', currentBuilds);
    
    // 2. ANALYSER CHAQUE BUILD INDIVIDUELLEMENT
    console.log('\n🔍 === ANALYSE DÉTAILLÉE DE CHAQUE BUILD ===');
    let runningBuildsDetected = 0;
    currentBuilds.forEach((build, index) => {
        const status = build.status;
        const state = build.state;
        const isRunning = state?.toLowerCase() === 'running' || state?.toLowerCase() === 'building';
        
        console.log(`\nBuild ${index + 1}/${currentBuilds.length}:`);
        console.log(`  📝 BuildTypeId: "${build.buildTypeId}"`);
        console.log(`  📝 Name: "${build.name}"`);
        console.log(`  🟢 Status: "${status}" (type: ${typeof status})`);
        console.log(`  🔄 State: "${state}" (type: ${typeof state})`);
        console.log(`  ⚡ IsRunning: ${isRunning}`);
        console.log(`  🔗 WebUrl: "${build.webUrl}"`);
        
        if (isRunning) {
            runningBuildsDetected++;
            console.log(`  🔥 *** BUILD EN COURS DÉTECTÉ ! ***`);
        }
    });
    
    console.log(`\n📈 RÉSUMÉ: ${runningBuildsDetected} builds en cours détectés`);
    
    // 3. VÉRIFIER LES STATISTIQUES
    console.log('\n📊 === VÉRIFICATION STATISTIQUES ===');
    const stats = getDetailedStats();
    console.log('Stats calculées:', stats);
    console.log('Stat running affiché dans header:', document.getElementById('running-count')?.textContent);
    
    // 4. VÉRIFIER LE DOM
    console.log('\n🏗️ === VÉRIFICATION DOM ===');
    const buildItems = document.querySelectorAll('.build-item');
    console.log(`Éléments .build-item trouvés: ${buildItems.length}`);
    
    let runningClassCount = 0;
    buildItems.forEach((item, index) => {
        const classes = item.className;
        const hasRunning = classes.includes('running');
        const buildName = item.querySelector('.build-name')?.textContent || 'N/A';
        
        console.log(`\nDOM Build ${index + 1}:`);
        console.log(`  📝 Nom: "${buildName}"`);
        console.log(`  🎨 Classes: "${classes}"`);
        console.log(`  ⚡ Has .running: ${hasRunning}`);
        
        if (hasRunning) {
            runningClassCount++;
            console.log(`  🔥 *** CLASSE RUNNING TROUVÉE DANS LE DOM ! ***`);
            
            // Vérifier l'animation CSS
            const computedStyle = window.getComputedStyle(item);
            console.log(`  🎭 Animation computed: "${computedStyle.animation}"`);
            console.log(`  🎭 Border: "${computedStyle.border}"`);
            console.log(`  🎭 Box-shadow: "${computedStyle.boxShadow}"`);
        }
    });
    
    console.log(`\n📈 RÉSUMÉ DOM: ${runningClassCount} éléments avec classe .running`);
    
    // 5. VÉRIFIER LE CSS D'ANIMATION
    console.log('\n🎨 === VÉRIFICATION CSS ===');
    let cssRuleFound = false;
    let keyframesFound = false;
    
    try {
        const styleSheets = document.styleSheets;
        console.log(`Nombre de feuilles de style: ${styleSheets.length}`);
        
        for (let i = 0; i < styleSheets.length; i++) {
            const sheet = styleSheets[i];
            console.log(`\nFeuille ${i + 1}: ${sheet.href || 'inline'}`);
            
            try {
                const rules = sheet.cssRules || sheet.rules;
                if (rules) {
                    for (let j = 0; j < rules.length; j++) {
                        const rule = rules[j];
                        
                        // Chercher .build-item.running
                        if (rule.selectorText && rule.selectorText.includes('.build-item.running')) {
                            cssRuleFound = true;
                            console.log(`  ✅ CSS Rule trouvée: ${rule.cssText}`);
                        }
                        
                        // Chercher @keyframes buildPulse
                        if (rule.type === CSSRule.KEYFRAMES_RULE && rule.name === 'buildPulse') {
                            keyframesFound = true;
                            console.log(`  ✅ Keyframes buildPulse trouvées: ${rule.cssText}`);
                        }
                    }
                }
            } catch (e) {
                console.log(`  ⚠️ Impossible d'accéder aux règles: ${e.message}`);
            }
        }
    } catch (e) {
        console.log(`❌ Erreur lors de la vérification CSS: ${e.message}`);
    }
    
    console.log(`\n📈 RÉSUMÉ CSS:`);
    console.log(`  - Règle .build-item.running: ${cssRuleFound ? '✅' : '❌'}`);
    console.log(`  - Keyframes buildPulse: ${keyframesFound ? '✅' : '❌'}`);
    
    // 6. TEST FORCÉ AVEC ANIMATION
    console.log('\n🧪 === TEST FORCÉ D\'ANIMATION ===');
    if (buildItems.length > 0) {
        const testElement = buildItems[0];
        console.log('Ajout de la classe .running au premier élément...');
        
        // Capturer l'état avant
        const beforeClasses = testElement.className;
        const beforeAnimation = window.getComputedStyle(testElement).animation;
        
        // Ajouter la classe
        testElement.classList.add('running');
        
        // Forcer un reflow
        testElement.offsetHeight;
        
        // Capturer l'état après
        const afterClasses = testElement.className;
        const afterAnimation = window.getComputedStyle(testElement).animation;
        
        console.log(`  🔄 Classes AVANT: "${beforeClasses}"`);
        console.log(`  🔄 Classes APRÈS: "${afterClasses}"`);
        console.log(`  🎭 Animation AVANT: "${beforeAnimation}"`);
        console.log(`  🎭 Animation APRÈS: "${afterAnimation}"`);
        
        // Vérifier si l'animation a changé
        if (beforeAnimation !== afterAnimation) {
            console.log(`  ✅ ANIMATION ACTIVÉE ! Différence détectée.`);
        } else {
            console.log(`  ❌ PROBLÈME: Animation inchangée !`);
        }
        
        // Retirer après 5 secondes
        setTimeout(() => {
            testElement.classList.remove('running');
            console.log('🧹 Classe .running supprimée du test');
        }, 5000);
    }
    
    // 7. DIAGNOSTIC FINAL
    console.log('\n🎯 === DIAGNOSTIC FINAL ===');
    console.log(`  - Builds en cours détectés dans les données: ${runningBuildsDetected}`);
    console.log(`  - Éléments DOM avec classe .running: ${runningClassCount}`);
    console.log(`  - CSS d'animation présent: ${cssRuleFound && keyframesFound}`);
    console.log(`  - Statistiques header running: ${document.getElementById('running-count')?.textContent}`);
    
    if (runningBuildsDetected > 0 && runningClassCount === 0) {
        console.log('🚨 PROBLÈME IDENTIFIÉ: Les données ont des builds en cours mais le DOM n\'a pas la classe .running !');
        console.log('👉 Le problème est dans generateBuildHTML() ou getStatusClass()');
    } else if (runningBuildsDetected === 0) {
        console.log('🚨 PROBLÈME IDENTIFIÉ: Aucun build n\'est actuellement en cours selon les données !');
        console.log('👉 Le problème vient du backend ou des données TeamCity');
    } else if (runningClassCount > 0 && !cssRuleFound) {
        console.log('🚨 PROBLÈME IDENTIFIÉ: La classe .running est présente mais le CSS d\'animation est manquant !');
        console.log('👉 Le problème vient du fichier Dashboard.css');
    }
    
    console.log('\n✨ === FIN DU DEBUG ===\n');
}

// Exposer pour utilisation dans la console
window.debugAnimationComplete = debugAnimationComplete;

// === FONCTION DE TEST FORCÉ ===
function forceRunningBuilds() {
    console.log('🔧 === FORÇAGE DE BUILDS EN COURS ===');
    
    if (currentBuilds.length === 0) {
        console.log('❌ Aucun build disponible pour le test');
        return;
    }
    
    // Modifier temporairement les 3 premiers builds pour qu'ils soient "running"
    const originalStates = [];
    const numToModify = Math.min(3, currentBuilds.length);
    
    for (let i = 0; i < numToModify; i++) {
        // Sauvegarder l'état original
        originalStates.push({
            status: currentBuilds[i].status,
            state: currentBuilds[i].state
        });
        
        // Forcer le state à "running"
        currentBuilds[i].state = 'running';
        currentBuilds[i].status = 'SUCCESS'; // Status peut rester SUCCESS
        
        console.log(`✅ Build ${i + 1} forcé en mode running: ${currentBuilds[i].buildTypeId}`);
    }
    
    // Déclencher un rafraîchissement de l'affichage
    console.log('🔄 Rafraîchissement de l\'affichage...');
    const dashboard = window.dashboardInstance || new SimpleDashboard();
    dashboard.organizeAndDisplayBuilds();
    dashboard.updateStats();
    
    console.log('✅ Affichage mis à jour avec builds forcés');
    console.log('👀 Vérifiez maintenant si l\'animation apparaît !');
    
    // Restaurer les états originaux après 30 secondes
    setTimeout(() => {
        console.log('🔄 Restauration des états originaux...');
        for (let i = 0; i < numToModify; i++) {
            currentBuilds[i].status = originalStates[i].status;
            currentBuilds[i].state = originalStates[i].state;
        }
        
        // Rafraîchir à nouveau
        dashboard.organizeAndDisplayBuilds();
        dashboard.updateStats();
        console.log('✅ États restaurés');
    }, 30000);
}

// Exposer pour utilisation dans la console
window.forceRunningBuilds = forceRunningBuilds;

// === FONCTION DE DEBUG SIMPLE ===
function checkBuilds() {
    console.log('=== DIAGNOSTIC BUILDS ===');
    console.log('Total:', currentBuilds.length);
    
    const statusCount = {};
    const stateCount = {};
    
    currentBuilds.forEach(build => {
        // Compter les status
        const status = build.status || 'undefined';
        statusCount[status] = (statusCount[status] || 0) + 1;
        
        // Compter les states
        const state = build.state || 'undefined';
        stateCount[state] = (stateCount[state] || 0) + 1;
    });
    
    console.log('Status:', statusCount);
    console.log('States:', stateCount);
    
    // Montrer quelques exemples
    console.log('Exemples:');
    currentBuilds.slice(0, 3).forEach((build, i) => {
        console.log(`${i+1}. ${build.buildTypeId}: ${build.status}/${build.state}`);
    });
}

window.checkBuilds = checkBuilds;

// === DÉMARRAGE DE L'APPLICATION ===
document.addEventListener('DOMContentLoaded', () => {
    try {
        new SimpleDashboard();
    } catch (error) {
        console.error('Erreur lors du démarrage:', error);
        // Fallback simple
        document.getElementById('builds-612').innerHTML = '<div class="loading">Erreur de chargement</div>';
        document.getElementById('builds-new').innerHTML = '<div class="loading">Erreur de chargement</div>';
    }
});

// === CONFIGURATION ===
function openConfigPage() {
    window.location.href = 'config.html';
}

// === DÉMARRAGE DE L'APPLICATION ===
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Créer une instance globale pour les tests
        window.dashboardInstance = new SimpleDashboard();
    } catch (error) {
        console.error('Erreur lors du démarrage:', error);
        // Fallback simple
        document.getElementById('builds-612').innerHTML = '<div class="loading">Erreur de chargement</div>';
        document.getElementById('builds-new').innerHTML = '<div class="loading">Erreur de chargement</div>';
    }
});
