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
    const overview = document.getElementById('overview-content');
    const agents = document.getElementById('overview-agents');
    
    const stats = getDetailedStats();
    overview.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 20px;">
            <div style="background: rgba(63, 185, 80, 0.1); border: 1px solid rgba(63, 185, 80, 0.3); border-radius: 8px; padding: 16px; text-align: center;">
                <div style="color: #3fb950; font-size: 24px; font-weight: bold;">${stats.success}</div>
                <div style="color: #7d8590; font-size: 12px;">Réussis</div>
            </div>
            <div style="background: rgba(248, 81, 73, 0.1); border: 1px solid rgba(248, 81, 73, 0.3); border-radius: 8px; padding: 16px; text-align: center;">
                <div style="color: #f85149; font-size: 24px; font-weight: bold;">${stats.failure}</div>
                <div style="color: #7d8590; font-size: 12px;">Échoués</div>
            </div>
            <div style="background: rgba(255, 166, 87, 0.1); border: 1px solid rgba(255, 166, 87, 0.3); border-radius: 8px; padding: 16px; text-align: center;">
                <div style="color: #ffa657; font-size: 24px; font-weight: bold;">${stats.running}</div>
                <div style="color: #7d8590; font-size: 12px;">En cours</div>
            </div>
            <div style="background: rgba(154, 99, 212, 0.1); border: 1px solid rgba(154, 99, 212, 0.3); border-radius: 8px; padding: 16px; text-align: center;">
                <div style="color: #9a63d4; font-size: 24px; font-weight: bold;">${currentAgents.length}</div>
                <div style="color: #7d8590; font-size: 12px;">Agents</div>
            </div>
        </div>
    `;
    
    // Afficher agents
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
        console.log('Dashboard initialisé');
        
        // ⚡ OPTIMISATION : Charger TOUT en PARALLÈLE pour plus de rapidité
        console.log('🚀 Chargement parallèle des données...');
        
        try {
            // Charger configuration, builds et agents EN MÊME TEMPS
            const [configResponse, buildsResponse, agentsResponse] = await Promise.all([
                fetch('http://localhost:8000/api/config'),
                fetch('http://localhost:8000/api/builds'),
                fetch('http://localhost:8000/api/agents')
            ]);
            
            // Traiter les réponses
            const [configData, buildsData, agentsData] = await Promise.all([
                configResponse.json(),
                buildsResponse.json(),
                agentsResponse.json()
            ]);
            
            console.log('✅ Toutes les données chargées en parallèle !');
            
            // Traiter la configuration
            this.processConfiguration(configData);
            
            // Traiter les builds
            this.processBuilds(buildsData);
            
            // Traiter les agents
            this.processAgents(agentsData);
            
        } catch (error) {
            console.error('❌ Erreur lors du chargement parallèle:', error);
            // Fallback : chargement séquentiel en cas d'erreur
            await this.loadConfiguration();
            await this.loadAndDisplayBuilds();
            await this.loadAndDisplayAgents();
        }
        
        // Démarrer le rafraîchissement automatique
        this.startAutoRefresh();
    }

    processConfiguration(data) {
        console.log('=== CONFIGURATION DETAILLEE ===');
        console.log('Données de configuration reçues:', data);
        console.log('Structure builds:', data.config?.builds);
        
        // Extraire les builds sélectionnés depuis la structure de config
        const selectedBuilds = data.config?.builds?.selectedBuilds || data.selectedBuilds || [];
        
        console.log('=== BUILDS EXTRAITS ===');
        console.log('Type de selectedBuilds:', typeof selectedBuilds);
        console.log('Array.isArray(selectedBuilds):', Array.isArray(selectedBuilds));
        console.log('selectedBuilds brut:', selectedBuilds);
        
        if (selectedBuilds.length > 0) {
            this.selectedBuilds = selectedBuilds;
            console.log('✅ Builds sélectionnés assignés:', this.selectedBuilds.length);
            console.log('✅ Tous les builds sélectionnés:', this.selectedBuilds);
            console.log('✅ Premier build sélectionné:', this.selectedBuilds[0]);
            console.log('✅ Dernier build sélectionné:', this.selectedBuilds[this.selectedBuilds.length - 1]);
        } else {
            console.log('❌ Aucune configuration trouvée, chargement de tous les builds');
            this.selectedBuilds = [];
        }
    }

    async loadConfiguration() {
        try {
            // Récupérer la configuration depuis le backend
            const response = await fetch('http://localhost:8000/api/config');
            const data = await response.json();
            this.processConfiguration(data);
        } catch (error) {
            console.error('❌ Erreur lors du chargement de la configuration:', error);
            this.selectedBuilds = [];
        }
    }

    processBuilds(data) {
        try {
            // Extraire tous les builds de la structure arborescente
            this.allBuilds = this.extractAllBuildsFromTree(data);
            
            // Filtrer selon les builds sélectionnés dans la configuration
            if (this.selectedBuilds && this.selectedBuilds.length > 0) {
                this.allBuilds = this.allBuilds.filter(build => 
                    this.selectedBuilds.includes(build.buildTypeId)
                );
                console.log(`Builds filtrés: ${this.allBuilds.length}/${this.extractAllBuildsFromTree(data).length} (selon config)`);
            } else {
                console.log('Aucun build sélectionné - dashboard vide');
                this.allBuilds = [];
            }
            
            currentBuilds = this.allBuilds;
            
            // Organiser les builds par version automatiquement
            this.organizeAndDisplayBuilds();
            
            // Mettre à jour les statistiques
            this.updateStats();
            
        } catch (error) {
            console.error('Erreur traitement builds:', error);
            this.displayError();
        }
    }

    async loadAndDisplayBuilds() {
        try {
            // Utiliser l'endpoint builds qui contient TOUS les builds TeamCity
            const response = await fetch('http://localhost:8000/api/builds');
            const data = await response.json();
            this.processBuilds(data);
        } catch (error) {
            console.error('Erreur chargement builds:', error);
            this.displayError();
        }
    }

    extractAllBuildsFromTree(data) {
        // L'API /api/builds renvoie directement un tableau de builds
        const allBuilds = data.builds || [];
        
        console.log(`Builds extraits de l'API: ${allBuilds.length}`);
        return allBuilds;
    }

    organizeAndDisplayBuilds() {
        console.log('=== DEBUT ORGANISATION ===');
        console.log('Total builds chargés:', this.allBuilds.length);
        console.log('Builds sélectionnés configurés:', this.selectedBuilds.length);
        
        // Filtrer selon la configuration des builds sélectionnés
        let filteredBuilds = this.allBuilds;
        if (this.selectedBuilds.length > 0) {
            console.log('Premier build de l\'API:', this.allBuilds[0]?.buildTypeId);
            console.log('Premier build sélectionné:', this.selectedBuilds[0]?.buildTypeId || this.selectedBuilds[0]?.name || this.selectedBuilds[0]);
            
            // DIAGNOSTIC COMPLET - Lister tous les builds de l'API
            console.log('=== TOUS LES BUILDS DE L\'API ===');
            const apiBuilds = this.allBuilds.map(b => b.buildTypeId);
            apiBuilds.forEach((buildId, index) => {
                console.log(`${(index + 1).toString().padStart(2, '0')}. ${buildId}`);
            });
            
            // DIAGNOSTIC - Builds sélectionnés manquants
            console.log('=== BUILDS SÉLECTIONNÉS MANQUANTS ===');
            const missingBuilds = this.selectedBuilds.filter(selectedBuildId => {
                return !this.allBuilds.some(build => build.buildTypeId === selectedBuildId);
            });
            console.log(`Builds manquants dans l'API: ${missingBuilds.length}/${this.selectedBuilds.length}`);
            missingBuilds.forEach((buildId, index) => {
                console.log(`❌ ${(index + 1).toString().padStart(2, '0')}. ${buildId}`);
            });
            
            // DÉCISION INTELLIGENTE : Si beaucoup de builds manquants, afficher tous les builds disponibles
            if (missingBuilds.length > this.selectedBuilds.length / 2) {
                console.log('⚠️ Plus de 50% des builds sélectionnés sont manquants dans l\'API');
                console.log('→ Affichage de TOUS les builds disponibles pour éviter un dashboard vide');
                filteredBuilds = this.allBuilds; // Afficher tous les builds disponibles
            } else {
                // Filtrage normal si la plupart des builds sont disponibles
                filteredBuilds = this.allBuilds.filter(build => {
                    const found = this.selectedBuilds.some(selectedBuildId => {
                        const match = build.buildTypeId === selectedBuildId;
                        if (match) {
                            console.log('✓ Build trouvé:', build.buildTypeId);
                        }
                        return match;
                    });
                    return found;
                });
            }
            console.log(`Builds filtrés selon configuration: ${filteredBuilds.length}`);
        } else {
            console.log('Aucun filtre, affichage de tous les builds');
        }

        // Si aucun build filtré, afficher tous les builds pour déboguer
        if (filteredBuilds.length === 0 && this.selectedBuilds.length > 0) {
            console.log('⚠️ Aucun build filtré trouvé, affichage de tous pour débogage');
            filteredBuilds = this.allBuilds;
        }

        // Organiser les builds par PROJET sélectionné, pas par version automatique
        const buildsByProject = this.organizeBySelectedProjects(filteredBuilds);
        
        // Afficher les projets dans les colonnes
        this.displayProjectsInColumns(buildsByProject);
        
        // Mettre à jour les compteurs
        const totalFirst = Object.values(buildsByProject.first).reduce((sum, builds) => sum + builds.length, 0);
        const totalSecond = Object.values(buildsByProject.second).reduce((sum, builds) => sum + builds.length, 0);
        this.updateColumnCounts([{length: totalFirst}], [{length: totalSecond}]);
    }

    organizeBySelectedProjects(builds) {
        // Si aucun build sélectionné, n'afficher rien
        if (builds.length === 0) {
            console.log('Aucun build sélectionné - dashboard vide');
            return {
                first: {},
                second: {},
                firstTitle: "Aucun projet sélectionné",
                secondTitle: "Aucun projet sélectionné"
            };
        }

        // DÉTECTER LES VERSIONS AUTOMATIQUEMENT
        console.log('=== DÉTECTION AUTOMATIQUE DES VERSIONS ===');
        const versions = this.detectVersions(builds);
        console.log('Versions détectées:', versions);

        // SÉPARER LES BUILDS PAR VERSION
        const firstVersion = versions[0] || "612";
        const secondVersion = versions[1] || "New";
        
        const { buildsFirst, buildsSecond } = this.separateBuildsByVersion(builds, firstVersion, secondVersion);
        
        console.log(`Builds séparés: ${buildsFirst.length} (${firstVersion}) + ${buildsSecond.length} (${secondVersion})`);

        // ORGANISER PAR PROJET DANS CHAQUE VERSION
        const firstProjects = this.groupBuildsByProject(buildsFirst);
        const secondProjects = this.groupBuildsByProject(buildsSecond);

        const result = {
            first: firstProjects,
            second: secondProjects,
            firstTitle: `GO2 Version ${firstVersion}`,
            secondTitle: `GO2 Version ${secondVersion}`
        };



        console.log('Projets organisés (Système complet):', {
            'Version 1': firstVersion,
            'Version 2': secondVersion,
            'Projets version 1': Object.keys(firstProjects),
            'Projets version 2': Object.keys(secondProjects),
            'Builds version 1': Object.values(result.first).reduce((sum, builds) => sum + builds.length, 0),
            'Builds version 2': Object.values(result.second).reduce((sum, builds) => sum + builds.length, 0)
        });

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
        } else if (buildTypeId.includes('WebServices') || buildTypeId.includes('GO2Portal')) {
            return 'Web Services';
        } else {
            return 'Autres';
        }
    }

    displayProjectsInColumns(buildsByProject) {
        // Mettre à jour les en-têtes avec les vrais noms de projets
        this.updateColumnHeaders(buildsByProject.firstTitle, buildsByProject.secondTitle);
        
        // Afficher colonne 1 avec les projets groupés
        this.displayBuildsInColumn('builds-612', buildsByProject.first);
        
        // Afficher colonne 2 avec les projets groupés
        this.displayBuildsInColumn('builds-new', buildsByProject.second);
    }

    updateColumnHeaders(firstTitle = null, secondTitle = null) {
        const title612 = document.getElementById('title-612');
        const titleNew = document.getElementById('title-new');
        
        if (title612) title612.textContent = firstTitle || 'Aucun projet';
        if (titleNew) titleNew.textContent = secondTitle || 'Aucun projet';
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
            }
        });

        // Trier par nombre d'occurrences (décroissant)
        return Object.keys(versionCounts)
            .sort((a, b) => versionCounts[b] - versionCounts[a])
            .slice(0, 2); // Prendre les 2 plus fréquentes
    }



    separateBuildsByVersion(builds, firstVersion, secondVersion) {
        const buildsFirst = [];
        const buildsSecond = [];
        
        console.log(`=== SEPARATION DES BUILDS ===`);
        console.log(`Version 1: "${firstVersion}", Version 2: "${secondVersion}"`);
        
        builds.forEach(build => {
            if (!build.buildTypeId) {
                return; // Ignorer les builds sans buildTypeId
            }
            
            const buildTypeId = build.buildTypeId;
            let assigned = false;
            
            // Priorité à la première version (généralement la plus récente)
            if (this.matchesVersion(buildTypeId, firstVersion)) {
                buildsFirst.push(build);
                assigned = true;
                console.log(`✓ "${buildTypeId}" → Colonne 1 (${firstVersion})`);
            } else if (this.matchesVersion(buildTypeId, secondVersion)) {
                buildsSecond.push(build);
                assigned = true;
                console.log(`✓ "${buildTypeId}" → Colonne 2 (${secondVersion})`);
            }
            
            // Si pas assigné et qu'on a des versions "Autres" ou "Tous"
            if (!assigned) {
                if (secondVersion === "Autres") {
                    buildsSecond.push(build);
                    console.log(`✓ "${buildTypeId}" → Colonne 2 (Autres)`);
                } else if (firstVersion === "Tous") {
                    buildsFirst.push(build);
                    console.log(`✓ "${buildTypeId}" → Colonne 1 (Tous)`);
                } else {
                    console.log(`✗ "${buildTypeId}" → Non assigné`);
                }
            }
        });
        
        console.log(`Résultat: ${buildsFirst.length} builds en colonne 1, ${buildsSecond.length} builds en colonne 2`);
        return { buildsFirst, buildsSecond };
    }

    matchesVersion(buildTypeId, version) {
        if (version === "Aucun") return false;
        if (version === "Tous") return true;
        if (version === "Autres") return false; // Géré séparément
        
        let result = false;
        
        // Recherche plus précise pour éviter les faux positifs
        if (version.match(/^\d{3,4}$/)) {
            // Pour les versions numériques (612, 613, etc.)
            result = buildTypeId.includes(version);
            console.log(`  Test numérique "${buildTypeId}" contains "${version}": ${result}`);
        } else if (version.toLowerCase() === "new") {
            // Pour la version "New"
            result = buildTypeId.toLowerCase().includes("new");
            console.log(`  Test NEW "${buildTypeId}" contains "new": ${result}`);
        } else {
            // Pour les autres patterns
            result = buildTypeId.includes(version);
            console.log(`  Test autre "${buildTypeId}" contains "${version}": ${result}`);
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
        
        // Ajouter un indicateur visuel pour les builds en cours
        const runningIndicator = (build.state?.toLowerCase() === 'running' || build.state?.toLowerCase() === 'building') 
            ? '<div class="running-indicator">▶</div>' 
            : '';
        
        return `
            <div class="build-item ${statusClass}" onclick="window.open('${build.webUrl}', '_blank')">
                <div class="build-name">${buildName}</div>
                ${runningIndicator}
            </div>
        `;
    }

    updateColumnCounts(builds612, buildsNew) {
        const count612 = document.getElementById('count-612');
        const countNew = document.getElementById('count-new');
        
        const count1 = Array.isArray(builds612) ? builds612.length : (builds612[0]?.length || 0);
        const count2 = Array.isArray(buildsNew) ? buildsNew.length : (buildsNew[0]?.length || 0);
        
        if (count612) count612.textContent = count1;
        if (countNew) countNew.textContent = count2;
    }

    displayError() {
        const builds612 = document.getElementById('builds-612');
        const buildsNew = document.getElementById('builds-new');
        
        if (builds612) builds612.innerHTML = '<div class="loading">Erreur de chargement</div>';
        if (buildsNew) buildsNew.innerHTML = '<div class="loading">Erreur de chargement</div>';
    }

    processAgents(data) {
        try {
            currentAgents = data.agents || [];
            console.log(`✅ Agents traités: ${currentAgents.length} agents`);
        } catch (error) {
            console.error('Erreur traitement agents:', error);
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
        // ⚡ OPTIMISATION : Rafraîchissement parallèle toutes les 60 secondes
        setInterval(async () => {
            try {
                console.log('🔄 Rafraîchissement automatique en cours...');
                
                // Charger TOUT en parallèle
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
                
                // Traiter les données
                this.processConfiguration(configData);
                this.processBuilds(buildsData);
                this.processAgents(agentsData);
                
                console.log('✅ Rafraîchissement terminé !');
                
            } catch (error) {
                console.error('❌ Erreur rafraîchissement:', error);
                // Fallback séquentiel
                await this.loadConfiguration();
                await this.loadAndDisplayBuilds();
                this.loadAndDisplayAgents();
            }
        }, 60000);
    }

    startStatsMonitoring() {
        setInterval(() => {
            this.updateStats();
        }, 5000);
    }

    updateStats() {
        const stats = this.getDetailedStats();
        
        document.getElementById('success-count').textContent = stats.success;
        document.getElementById('failure-count').textContent = stats.failure;
        document.getElementById('running-count').textContent = stats.running;
        document.getElementById('agents-count').textContent = currentAgents.length;
        document.getElementById('total-count').textContent = `${this.allBuilds.length}/${this.allBuilds.length}`;
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
