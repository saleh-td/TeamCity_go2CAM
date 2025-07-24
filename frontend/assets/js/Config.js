const defaultConfig = {
    builds: {
        selectedBuilds: []
    }
};

let buildsTree = null;
let selectedBuilds = [];
let expandedNodes = new Set();
let searchTerm = '';
let autoSaveTimeout = null;

function goBackToDashboard() {
    window.location.href = 'index.html';
}

async function loadBuildsTree() {
    try {
        const response = await fetch('/api/builds/tree');
        if (response.ok) {
            const result = await response.json();
            buildsTree = result;
            selectedBuilds = result.selected_builds || [];
            
            const filteredProjects = {};
            Object.keys(buildsTree.projects || {}).forEach(projectName => {
                if (projectName && projectName !== '<Root project>' && projectName !== 'Root project') {
                    filteredProjects[projectName] = buildsTree.projects[projectName];
                }
            });
            buildsTree.projects = filteredProjects;
            
            expandedNodes.clear();
            
            renderBuildsTree();
            updateBuildsSummary();
            
            return true;
        } else {
            console.error('Erreur lors du chargement de l\'arborescence:', response.status);
        }
    } catch (error) {
        console.error('Erreur lors du chargement de l\'arborescence:', error);
    }
    
    return false;
}


function expandAllNodes(tree) {
    if (tree.projects) {
        Object.keys(tree.projects).forEach(projectName => {
            expandedNodes.add(`project_${projectName}`);
            expandAllSubprojects(tree.projects[projectName], projectName);
        });
    }
}

function expandAllSubprojects(project, projectPath) {
    if (project.subprojects) {
        Object.keys(project.subprojects).forEach(subprojectName => {
            const subprojectPath = `${projectPath}_${subprojectName}`;
            expandedNodes.add(`subproject_${subprojectPath}`);
            expandAllSubprojects(project.subprojects[subprojectName], subprojectPath);
        });
    }
}

function collapseAllNodes() {
    expandedNodes.clear();
    renderBuildsTree();
}

function getBuildStatus(build) {
    const status = build.status?.toLowerCase();
    if (status === 'success') return 'success';
    if (status === 'failure') return 'failure';
    if (build.state?.toLowerCase() === 'running') return 'running';
    return 'success';
}


function renderBuildsTree() {
    const container = document.getElementById('builds-tree');
    
    if (!buildsTree || !buildsTree.projects) {
        container.innerHTML = '<div class="loading-builds"><i data-lucide="loader-2"></i>Chargement de l\'arborescence...</div>';
        return;
    }
    
    const filteredTree = applySearchFilter(buildsTree);
    const html = renderProjectsHTML(filteredTree.projects);
    
    container.innerHTML = html;
    
    // Réinitialiser les icônes Lucide
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function applySearchFilter(tree) {
    if (!searchTerm) return tree;
    
    const filteredTree = { projects: {} };
    
    Object.keys(tree.projects).forEach(projectName => {
        const filteredProject = filterProject(tree.projects[projectName], searchTerm);
        if (filteredProject) {
            filteredTree.projects[projectName] = filteredProject;
        }
    });
    
    return filteredTree;
}

function filterProject(project, searchTerm) {
    const term = searchTerm.toLowerCase();
    let hasMatch = false;
    
    const filteredProject = {
        name: project.name,
        subprojects: {},
        builds: []
    };
    
    // Filtrer les builds directs
    if (project.builds) {
        project.builds.forEach(build => {
            if (build.name.toLowerCase().includes(term)) {
                filteredProject.builds.push(build);
                hasMatch = true;
            }
        });
    }
    
    // Filtrer les sous-projets
    if (project.subprojects) {
        Object.keys(project.subprojects).forEach(subprojectName => {
            const filteredSubproject = filterProject(project.subprojects[subprojectName], searchTerm);
            if (filteredSubproject) {
                filteredProject.subprojects[subprojectName] = filteredSubproject;
                hasMatch = true;
            }
        });
    }
    
    return hasMatch ? filteredProject : null;
}

function renderProjectsHTML(projects) {
    return Object.keys(projects).map(projectName => {
        const project = projects[projectName];
        const isExpanded = expandedNodes.has(`project_${projectName}`);
        const checkboxState = getProjectCheckboxState(project);
        
        return `
            <div class="tree-project">
                <div class="tree-project-header ${isExpanded ? 'expanded' : 'collapsed'}" 
                     onclick="toggleProject('${projectName}')">
                    <i data-lucide="chevron-right" class="tree-expand-icon ${isExpanded ? 'expanded' : ''}"></i>
                    <i data-lucide="folder" class="tree-folder-icon" style="color: #3fb950;"></i>
                    <div class="tree-project-checkbox ${checkboxState}" 
                         onclick="event.stopPropagation(); toggleProjectSelection('${projectName}')"></div>
                    <span class="tree-project-name">${project.name}</span>
                </div>
                <div class="tree-project-content ${isExpanded ? 'expanded' : ''}">
                    ${renderSubprojectsHTML(project.subprojects || {}, projectName)}
                    ${renderBuildsHTML(project.builds || [])}
                </div>
            </div>
        `;
    }).join('');
}

function renderSubprojectsHTML(subprojects, projectPath) {
    return Object.keys(subprojects).map(subprojectName => {
        const subproject = subprojects[subprojectName];
        const subprojectPath = `${projectPath}_${subprojectName}`;
        const isExpanded = expandedNodes.has(`subproject_${subprojectPath}`);
        const checkboxState = getProjectCheckboxState(subproject);
        
        return `
            <div class="tree-subproject">
                <div class="tree-subproject-header ${isExpanded ? 'expanded' : 'collapsed'}" 
                     onclick="toggleSubproject('${subprojectPath}')">
                    <i data-lucide="chevron-right" class="tree-expand-icon ${isExpanded ? 'expanded' : ''}"></i>
                    <i data-lucide="folder" class="tree-folder-icon" style="color: #3fb950;"></i>
                    <div class="tree-subproject-checkbox ${checkboxState}" 
                         onclick="event.stopPropagation(); toggleSubprojectSelection('${subprojectPath}')"></div>
                    <span class="tree-subproject-name">${subproject.name}</span>
                </div>
                <div class="tree-subproject-content ${isExpanded ? 'expanded' : ''}">
                    ${renderSubprojectsHTML(subproject.subprojects || {}, subprojectPath)}
                    ${renderBuildsHTML(subproject.builds || [])}
                </div>
            </div>
        `;
    }).join('');
}

function renderBuildsHTML(builds) {
    return builds.map(build => {
        const isSelected = selectedBuilds.includes(build.buildTypeId);
        const statusClass = getBuildStatus(build);
        
        return `
            <div class="tree-build" onclick="toggleBuildSelection('${build.buildTypeId}')">
                <i data-lucide="diamond" class="tree-build-icon" style="color: #3fb950;"></i>
                <div class="tree-build-checkbox ${isSelected ? 'checked' : ''}"></div>
                <span class="tree-build-name">${build.name}</span>
                <div class="tree-build-status ${statusClass}"></div>
            </div>
        `;
    }).join('');
}

function getProjectCheckboxState(project) {
    const projectBuilds = getAllBuildsFromProject(project);
    const selectedCount = projectBuilds.filter(build => selectedBuilds.includes(build.buildTypeId)).length;
    
    if (selectedCount === 0) return '';
    if (selectedCount === projectBuilds.length) return 'checked';
    return 'indeterminate';
}

function getAllBuildsFromProject(project) {
    let builds = [...(project.builds || [])];
    
    if (project.subprojects) {
        Object.values(project.subprojects).forEach(subproject => {
            builds = builds.concat(getAllBuildsFromProject(subproject));
        });
    }
    
    return builds;
}

// === INTERACTIONS AVEC L'ARBORESCENCE ===
function setupBuildsSearch() {
    const searchInput = document.getElementById('builds-search');
    
    searchInput.addEventListener('input', function() {
        searchTerm = this.value.trim();
        renderBuildsTree();
    });
    
    // Gérer les touches clavier
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            this.value = '';
            searchTerm = '';
            renderBuildsTree();
            this.blur();
        }
    });
}

// === FONCTIONS DE CONTRÔLE DE L'ARBORESCENCE ===
function expandAllBuilds() {
    expandedNodes.clear();
    expandAllNodes(buildsTree);
    renderBuildsTree();
}

function collapseAllBuilds() {
    collapseAllNodes();
}

function selectAllBuilds() {
    if (buildsTree && buildsTree.projects) {
        selectedBuilds = [];
        Object.values(buildsTree.projects).forEach(project => {
            const projectBuilds = getAllBuildsFromProject(project);
            projectBuilds.forEach(build => {
                if (!selectedBuilds.includes(build.buildTypeId)) {
                    selectedBuilds.push(build.buildTypeId);
                }
            });
        });
        renderBuildsTree();
        updateBuildsSummary();
        // triggerAutoSave(); // Désactivé - utiliser le bouton "Sauvegarder" manuellement
    }
}

function deselectAllBuilds() {
    selectedBuilds = [];
    renderBuildsTree();
    updateBuildsSummary();
    triggerAutoSave();
}

// === TOGGLE EXPAND/COLLAPSE ===
function toggleProject(projectName) {
    const nodeId = `project_${projectName}`;
    if (expandedNodes.has(nodeId)) {
        expandedNodes.delete(nodeId);
    } else {
        expandedNodes.add(nodeId);
    }
    renderBuildsTree();
}

function toggleSubproject(subprojectPath) {
    const nodeId = `subproject_${subprojectPath}`;
    if (expandedNodes.has(nodeId)) {
        expandedNodes.delete(nodeId);
    } else {
        expandedNodes.add(nodeId);
    }
    renderBuildsTree();
}

// === TOGGLE SÉLECTION ===
function toggleProjectSelection(projectName) {
    const project = buildsTree.projects[projectName];
    if (!project) return;
    
    const projectBuilds = getAllBuildsFromProject(project);
    const selectedCount = projectBuilds.filter(build => selectedBuilds.includes(build.buildTypeId)).length;
    
    if (selectedCount === projectBuilds.length) {
        // Tout désélectionner
        projectBuilds.forEach(build => {
            const index = selectedBuilds.indexOf(build.buildTypeId);
            if (index > -1) {
                selectedBuilds.splice(index, 1);
            }
        });
    } else {
        // Tout sélectionner
        projectBuilds.forEach(build => {
            if (!selectedBuilds.includes(build.buildTypeId)) {
                selectedBuilds.push(build.buildTypeId);
            }
        });
    }
    
    renderBuildsTree();
    updateBuildsSummary();
    triggerAutoSave();
}

function toggleSubprojectSelection(subprojectPath) {
    const pathParts = subprojectPath.split('_');
    let current = buildsTree.projects[pathParts[0]];
    
    for (let i = 1; i < pathParts.length; i++) {
        current = current.subprojects[pathParts[i]];
        if (!current) return;
    }
    
    const subprojectBuilds = getAllBuildsFromProject(current);
    const selectedCount = subprojectBuilds.filter(build => selectedBuilds.includes(build.buildTypeId)).length;
    
    if (selectedCount === subprojectBuilds.length) {
        // Tout désélectionner
        subprojectBuilds.forEach(build => {
            const index = selectedBuilds.indexOf(build.buildTypeId);
            if (index > -1) {
                selectedBuilds.splice(index, 1);
            }
        });
            } else {
        // Tout sélectionner
        subprojectBuilds.forEach(build => {
            if (!selectedBuilds.includes(build.buildTypeId)) {
                selectedBuilds.push(build.buildTypeId);
            }
        });
    }
    
    renderBuildsTree();
    updateBuildsSummary();
    triggerAutoSave();
}

function toggleBuildSelection(buildTypeId) {
    const index = selectedBuilds.indexOf(buildTypeId);
    if (index > -1) {
        selectedBuilds.splice(index, 1);
    } else {
        selectedBuilds.push(buildTypeId);
    }
    
    renderBuildsTree();
    updateBuildsSummary();
    triggerAutoSave();
}

// === MISE À JOUR DU RÉSUMÉ ===
function updateBuildsSummary() {
    const totalBuilds = buildsTree ? buildsTree.total_builds : 0;
    const selectedCount = selectedBuilds.length;
    
    const selectedElement = document.getElementById('selected-builds-count');
    const totalElement = document.getElementById('total-builds-count');
    
    if (selectedElement) {
        selectedElement.textContent = selectedCount;
    }
    if (totalElement) {
        totalElement.textContent = totalBuilds;
    }
    
    // Mettre à jour les noms des colonnes selon les projets sélectionnés
    updateColumnNames();
}

function updateColumnNames() {
    // Remplir les menus déroulants avec les projets disponibles
    populateProjectDropdowns();
}

function populateProjectDropdowns() {
    const availableProjects = getAvailableProjects();
    
    // Remplir les 3 menus déroulants
    const selects = ['nameFirstColumn', 'nameSecondColumn', 'nameThirdColumn'];
    
    selects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            // Garder l'option par défaut
            const defaultOption = select.querySelector('option[value=""]');
            select.innerHTML = '';
            if (defaultOption) {
                select.appendChild(defaultOption);
            }
            
            // Ajouter les projets disponibles
            availableProjects.forEach(project => {
                const option = document.createElement('option');
                option.value = project;
                option.textContent = project;
                select.appendChild(option);
            });
        }
    });
}

function getAvailableProjects() {
    const projects = [];
    
    if (buildsTree && buildsTree.projects) {
        Object.keys(buildsTree.projects).forEach(projectName => {
            if (projectName && projectName !== '<Root project>' && projectName !== 'Root project') {
                projects.push(projectName);
            }
        });
    }
    
    return projects.sort();
}

function getSelectedProjects() {
    const projects = [];
    
    // Analyser les builds sélectionnés pour détecter les projets
    if (selectedBuilds && selectedBuilds.length > 0) {
        const projectMap = new Map();
        
        selectedBuilds.forEach(buildId => {
            // Extraire le vrai nom du projet depuis buildId
            // Ex: "Go2Version612_..." -> "GO2 Version 612"
            const parts = buildId.split('_');
            if (parts.length > 0) {
                let projectName = parts[0];
                
                // Mapping correct des noms de projets
                if (projectName.includes('Go2Version612')) {
                    projectName = 'GO2 Version 612';
                } else if (projectName.includes('Go2VersionNew') || projectName.includes('InstalleursNew')) {
                    projectName = 'GO2 Version New';
                } else if (projectName.includes('WebServices')) {
                    projectName = 'Web Services';
                } else {
                    // Pour les autres projets, utiliser le nom original
                    projectName = projectName.replace(/([A-Z])/g, ' $1').trim();
                    projectName = projectName.replace(/^Go2/, 'GO2');
                }
                
                if (!projectMap.has(projectName)) {
                    projectMap.set(projectName, projectName);
                }
            }
        });
        
        // Convertir en tableau et trier
        projects.push(...Array.from(projectMap.values()).sort());
    }
    
    console.log('Projets détectés:', projects);
    return projects;
}

// === SAUVEGARDE MANUELLE ===
function saveConfiguration() {
    console.log('Sauvegarde manuelle en cours...');
    
    // Désactiver le bouton pendant la sauvegarde
    const saveBtn = document.querySelector('.save-btn');
    const originalText = saveBtn.innerHTML;
    
    saveBtn.innerHTML = `
        <i data-lucide="loader-2" style="width: 14px; height: 14px; animation: spin 1s linear infinite;"></i>
        Sauvegarde...
    `;
    saveBtn.disabled = true;
    
    // Réinitialiser les icônes Lucide
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    // Effectuer la sauvegarde
    autoSaveConfiguration().then(() => {
        // Restaurer le bouton après succès
        saveBtn.innerHTML = `
            <i data-lucide="check" style="width: 14px; height: 14px; color: #3fb950;"></i>
            Sauvegardé !
        `;
        
        // Réinitialiser les icônes Lucide
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
        
        // Restaurer le bouton original après 2 secondes
        setTimeout(() => {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
            
            // Réinitialiser les icônes Lucide
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }, 2000);
    }).catch((error) => {
        console.error('Erreur lors de la sauvegarde:', error);
        
        // Restaurer le bouton en cas d'erreur
        saveBtn.innerHTML = `
            <i data-lucide="alert-circle" style="width: 14px; height: 14px; color: #f85149;"></i>
            Erreur !
        `;
        
        // Réinitialiser les icônes Lucide
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
        
        // Restaurer le bouton original après 3 secondes
        setTimeout(() => {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
            
            // Réinitialiser les icônes Lucide
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }, 3000);
    });
}

// === SAUVEGARDE AUTOMATIQUE ===
function triggerAutoSave() {
    // SAUVEGARDE AUTOMATIQUE ACTIVÉE pour synchronisation temps réel
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }
    
    autoSaveTimeout = setTimeout(() => {
        autoSaveConfiguration();
    }, 1000); // Délai de 1 seconde pour éviter trop de requêtes
}

async function autoSaveConfiguration() {
    try {
        console.log('Sauvegarde automatique en cours...');
        console.log('Builds à sauvegarder:', selectedBuilds);
        
        // Log spécifique pour DentalLongTest
        selectedBuilds.forEach(buildId => {
            if (buildId.includes('DentalLongTest')) {
                console.log('🔍 DENTALLONGTEST DANS LA SAUVEGARDE:', buildId);
            }
        });
        
        const response = await fetch('http://localhost:8000/api/builds/tree/selection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ selectedBuilds })
        });
        
        if (response.ok) {
            console.log('✅ Sauvegarde automatique réussie');
        } else {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        // Aussi sauvegarder en localStorage comme backup
        localStorage.setItem('teamcity-monitor-builds', JSON.stringify(selectedBuilds));
        
    } catch (error) {
        console.error('❌ Erreur lors de la sauvegarde automatique:', error);
        
        // Fallback: sauvegarder au moins en localStorage
        try {
            localStorage.setItem('teamcity-monitor-builds', JSON.stringify(selectedBuilds));
            console.log('Sauvegarde de secours en localStorage');
        } catch (fallbackError) {
            console.error('Erreur de sauvegarde de secours:', fallbackError);
        }
    }
}

function showAutoSaveIndicator() {
    // Créer un indicateur visuel temporaire
    const summary = document.getElementById('builds-summary');
    if (!summary) return;
    
    const originalText = summary.innerHTML;
    
    summary.innerHTML = `
        <span class="summary-text">
            <i data-lucide="check" style="width: 14px; height: 14px; color: #57f287;"></i>
            Sauvegardé automatiquement
        </span>
    `;
    
    // Réinitialiser les icônes Lucide
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    // Restaurer le texte original après 2 secondes
    setTimeout(() => {
        if (summary) {
            summary.innerHTML = originalText;
            updateBuildsSummary();
        }
    }, 2000);
}

// === CHARGEMENT DE LA CONFIGURATION ===
async function loadConfiguration() {
    try {
        // Charger la sélection des builds depuis l'API backend
        const response = await fetch('http://localhost:8000/api/builds/tree');
        if (response.ok) {
            const result = await response.json();
            
            // Charger les builds sélectionnés
            selectedBuilds = result.selected_builds || [];
            console.log('Builds sélectionnés chargés depuis backend:', selectedBuilds);
            return;
        }
    } catch (error) {
        console.error('Erreur lors du chargement depuis le backend:', error);
    }
    
    // Fallback: charger depuis localStorage
    try {
        const saved = localStorage.getItem('teamcity-monitor-builds');
        if (saved) {
            selectedBuilds = JSON.parse(saved);
            console.log('Builds sélectionnés chargés depuis localStorage:', selectedBuilds);
        } else {
            // AUCUN BUILD SÉLECTIONNÉ PAR DÉFAUT - L'UTILISATEUR DOIT FAIRE SES CHOIX
            selectedBuilds = [];
            console.log('Aucune configuration trouvée - aucun build sélectionné par défaut');
        }
    } catch (error) {
        console.error('Erreur lors du chargement de la configuration:', error);
        selectedBuilds = [];
    }
}

// === RACCOURCIS CLAVIER ===
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Escape pour retourner au dashboard
        if (e.key === 'Escape') {
            goBackToDashboard();
        }
    });
}

// === INITIALISATION ===
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Configuration des builds - page chargée');
    
    // Afficher le loading
    const buildsContainer = document.getElementById('builds-tree');
    buildsContainer.innerHTML = `
        <div class="loading-builds">
            <i data-lucide="loader-2" style="width: 16px; height: 16px;"></i>
            Chargement de l'arborescence des builds...
        </div>
    `;
    
    // Initialiser les icônes Lucide
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    // Charger la configuration actuelle AVANT l'arborescence
    await loadConfiguration();
    
    // Charger l'arborescence des builds depuis l'API
    const buildsLoaded = await loadBuildsTree();
    
    if (buildsLoaded) {
        // Configurer la recherche
        setupBuildsSearch();
        
        // Mettre à jour le résumé après que tout soit chargé
        updateBuildsSummary();
        
        console.log('Arborescence chargée avec succès:', buildsTree);
        console.log('Builds sélectionnés:', selectedBuilds);
    } else {
        buildsContainer.innerHTML = '<div class="loading-builds">Erreur lors du chargement de l\'arborescence des builds</div>';
    }
    
    // Configurer les raccourcis clavier
    setupKeyboardShortcuts();
    
    // Réinitialiser les icônes Lucide après tout chargement
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
});

