let currentBuilds = [];
let currentAgents = [];

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

class SimpleDashboard {
    constructor() {
        this.config = {
            first: null,
            second: null
        };
        this.allBuilds = [];
        this.selectedBuilds = [];
        this.dynamicColumns = [];
        this.init();
        this.startStatsMonitoring();
    }

    async init() {
        try {
            const [configResponse, buildsResponse, agentsResponse] = await Promise.all([
                fetch('http://localhost:8000/api/config'),
                fetch('http://localhost:8000/api/builds/dashboard'),
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
            this.allBuilds = data.builds || [];
            this.organizedProjects = data.projects || {};
            currentBuilds = this.allBuilds;
            this.organizeAndDisplayBuilds();
            this.updateStats();
            
        } catch (error) {
            this.displayError();
        }
    }

    async loadAndDisplayBuilds() {
        try {
            const response = await fetch('http://localhost:8000/api/builds/dashboard');
            const data = await response.json();
            this.processBuilds(data);
        } catch (error) {
            this.displayError();
        }
    }

    organizeAndDisplayBuilds() {
        this.createDynamicColumns();
        this.displayDynamicColumns();
        this.updateDynamicStats();
    }

    createDynamicColumns() {
        const projectKeys = Object.keys(this.organizedProjects);
        this.dynamicColumns = [];

        projectKeys.forEach((projectKey, index) => {
            const project = this.organizedProjects[projectKey];
            const flattenedBuilds = this.flattenSubprojects(project.subprojects);
            
            const totalBuilds = Object.values(flattenedBuilds).reduce((sum, builds) => sum + builds.length, 0);
            
            if (totalBuilds > 0) {
                this.dynamicColumns.push({
                    id: `dynamic-column-${index}`,
                    title: project.name,
                    builds: flattenedBuilds,
                    totalCount: totalBuilds,
                    icon: this.getProjectIcon(project.name, index),
                    color: this.getProjectColor(index)
                });
            }
        });
    }

    getProjectIcon(projectName, index) {
        // Attribution automatique d'icônes selon l'index
        const iconLibrary = ['database', 'sparkles', 'git-branch', 'folder', 'cpu', 'layers', 'box', 'code', 'settings', 'server'];
        return iconLibrary[index % iconLibrary.length];
    }

    getProjectColor(index) {
        // Attribution automatique de couleurs selon l'index
        const colorPalette = ['#58a6ff', '#57f287', '#f59e0b', '#a855f7', '#06b6d4', '#f43f5e', '#10b981', '#8b5cf6', '#ef4444', '#06b6d4'];
        return colorPalette[index % colorPalette.length];
    }

    displayDynamicColumns() {
        const dashboardGrid = document.getElementById('dashboard-grid');
        if (!dashboardGrid) return;

        dashboardGrid.innerHTML = '';

        this.dynamicColumns.forEach((column, index) => {
            const columnElement = this.createColumnElement(column, index);
            dashboardGrid.appendChild(columnElement);
        });

        this.updateDynamicGridLayout();

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    createColumnElement(column, index) {
        const columnDiv = document.createElement('div');
        columnDiv.className = 'build-zone';
        columnDiv.id = column.id;

        columnDiv.innerHTML = `
            <div class="zone-header">
                <div class="zone-title">
                    <i data-lucide="${column.icon}" class="zone-icon" style="color: ${column.color}; width: 22px; height: 22px;"></i>
                    <span class="dynamic-title">${column.title}</span>
                </div>
                <div class="zone-badge dynamic-count">${column.totalCount}</div>
            </div>
            <div class="builds-grid dynamic-builds">
                ${this.generateProjectsHTML(column.builds)}
            </div>
        `;

        return columnDiv;
    }

    updateDynamicGridLayout() {
        const dashboardGrid = document.getElementById('dashboard-grid');
        if (!dashboardGrid) return;

        dashboardGrid.classList.remove('has-third-column', 'two-columns', 'one-column');

        const columnCount = this.dynamicColumns.length;
        
        if (columnCount === 1) {
            dashboardGrid.classList.add('one-column');
        } else if (columnCount === 2) {
            dashboardGrid.classList.add('two-columns');
        } else if (columnCount >= 3) {
            dashboardGrid.classList.add('has-third-column');
        }
    }

    updateDynamicStats() {
        this.updateStats();
    }

    flattenSubprojects(subprojects) {
        const flattened = {};
        
        for (const [subprojectName, subprojectData] of Object.entries(subprojects)) {
            flattened[subprojectName] = subprojectData.builds;
        }
        
        return flattened;
    }

    generateProjectsHTML(buildsByProject) {
        let html = '';
        
        Object.keys(buildsByProject).forEach(subprojectName => {
            const builds = buildsByProject[subprojectName];
            
            html += `
                <div class="project-group">
                    <div class="project-header">
                        <h3 class="project-title">${subprojectName}</h3>
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
        const statusClass = getStatusClass(build.status, build.state);
        const buildName = this.extractReadableBuildName(build);
        
        return `
            <div class="build-item ${statusClass}" onclick="window.open('${build.webUrl}', '_blank')">
                <div class="build-name">${buildName}</div>
            </div>
        `;
    }

    extractReadableBuildName(build) {
        const fullName = build.name || build.buildTypeId || 'Build';
        
        const parts = fullName.split('_');
        if (parts.length > 1) {
            const lastPart = parts[parts.length - 1];
            return lastPart.replace(/([A-Z])/g, ' $1').trim();
        }
        
        return fullName;
    }

    displayError() {
        const dashboardGrid = document.getElementById('dashboard-grid');
        if (dashboardGrid) {
            dashboardGrid.innerHTML = '<div class="loading">Erreur de chargement des projets</div>';
        }
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
        setInterval(async () => {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000);
                
                const [configResponse, buildsResponse, agentsResponse] = await Promise.all([
                    fetch('http://localhost:8000/api/config', { signal: controller.signal }),
                    fetch('http://localhost:8000/api/builds/dashboard', { signal: controller.signal }),
                    fetch('http://localhost:8000/api/agents', { signal: controller.signal })
                ]);
                
                clearTimeout(timeoutId);
                
                const [configData, buildsData, agentsData] = await Promise.all([
                    configResponse.json(),
                    buildsResponse.json(),
                    agentsResponse.json()
                ]);
                
                this.processConfiguration(configData);
                this.processBuilds(buildsData);
                this.processAgents(agentsData);
                
            } catch (error) {
                try {
                    await this.loadConfiguration();
                    await this.loadAndDisplayBuilds();
                    this.loadAndDisplayAgents();
                } catch (fallbackError) {
                    // Ignorer les erreurs de fallback
                }
            }
        }, 120000);
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
        if (state?.toLowerCase() === 'running' || state?.toLowerCase() === 'building') {
            return 'running';
        }
        
        const statusUpper = status?.toUpperCase();
        if (statusUpper === 'SUCCESS') {
            return 'success';
        } else if (statusUpper === 'FAILURE') {
            return 'failure';
        } else if (statusUpper === 'UNKNOWN') {
            return 'unknown';
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

window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
}

function openConfigPage() {
    window.location.href = 'config.html';
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        window.dashboardInstance = new SimpleDashboard();
    } catch (error) {
        console.error('Erreur lors du démarrage:', error);
        const dashboardGrid = document.getElementById('dashboard-grid');
        if (dashboardGrid) {
            dashboardGrid.innerHTML = '<div class="loading">Erreur de chargement</div>';
        }
    }
});
