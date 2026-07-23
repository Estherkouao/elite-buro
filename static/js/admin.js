/*
 * EliteBuro Admin Dashboard
 * JavaScript Functions for Admin Management
 */

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initializeSidebar();
    initializeNavigation();
    initializeSearch();
    initializeNotifications();
    initializeDataTables();
    initializeFilters();
    loadDashboardData();
});

// ============================================
// SIDEBAR MANAGEMENT
// ============================================

function initializeSidebar() {
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');

    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768) {
            if (!e.target.closest('.sidebar') && !e.target.closest('.menu-toggle')) {
                sidebar.classList.remove('active');
            }
        }
    });
}

// ============================================
// NAVIGATION
// ============================================

function initializeNavigation() {
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            // Ne pas e.preventDefault() : on laisse la navigation href Django fonctionner.
            // Le switching single-page n'est pas prévu/fiable ici, et bloquait les clics.

            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');

            const sectionId = this.getAttribute('data-section');
            if (sectionId) {
                showSection(sectionId);
                updatePageTitle(sectionId);
            }

            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                document.querySelector('.sidebar')?.classList.remove('active');
            }
        });
    });
}

function showSection(sectionId) {
    if (!sectionId) return;

    // Only attempt switching if sections exist in current DOM
    const sections = document.querySelectorAll('.content-section');
    if (!sections.length) return;

    sections.forEach(section => section.classList.remove('active'));

    const selectedSection = document.getElementById(sectionId);
    if (selectedSection) {
        selectedSection.classList.add('active');
    }
}

function updatePageTitle(sectionId) {
    const pageTitle = document.querySelector('.page-title');
    const titles = {
        'dashboard': 'Dashboard',
        'reservations': 'Réservations',
        'espaces': 'Espaces',
        'membres': 'Membres',
        'paiements': 'Paiements',
        'reclamations': 'Réclamations',
        'domiciliation': 'Domiciliation',
        'formations': 'Formations',
        'rapports': 'Rapports',
        'parametres': 'Paramètres'
    };

    if (pageTitle) {
        pageTitle.textContent = titles[sectionId] || 'Dashboard';
    }
}

// ============================================
// SEARCH FUNCTIONALITY
// ============================================

function initializeSearch() {
    const searchBtn = document.querySelector('.search-btn');
    const searchInput = document.querySelector('.search-input');

    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }

    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleSearch();
            }
        });
    }
}

function handleSearch() {
    const searchInput = document.querySelector('.search-input');
    const searchTerm = searchInput ? searchInput.value : '';

    if (!searchTerm.trim()) {
        showNotification('Veuillez entrer un terme de recherche', 'warning');
        return;
    }

    console.log('Searching for:', searchTerm);
    showNotification(`Recherche en cours pour "${searchTerm}"...`, 'info');

    // Simulate search
    setTimeout(() => {
        showNotification(`${5} résultats trouvés pour "${searchTerm}"`, 'success');
    }, 1500);
}

// ============================================
// NOTIFICATIONS
// ============================================

function initializeNotifications() {
    const notificationBtn = document.querySelector('.notification-btn');

    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            showNotificationPanel();
        });
    }
}

function showNotificationPanel() {
    showNotification('Vous avez 5 notifications', 'info');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 6px;
        font-weight: 600;
        z-index: 3000;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
    `;

    // Set type-specific styles
    const colors = {
        'success': { bg: '#27ae60', color: 'white' },
        'error': { bg: '#e74c3c', color: 'white' },
        'info': { bg: '#3498db', color: 'white' },
        'warning': { bg: '#f39c12', color: 'white' },
    };

    const typeStyle = colors[type] || colors['info'];
    notification.style.backgroundColor = typeStyle.bg;
    notification.style.color = typeStyle.color;

    // Add to page
    document.body.appendChild(notification);

    // Remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 4000);
}

// ============================================
// DATA TABLES
// ============================================

function initializeDataTables() {

    const actionButtons = document.querySelectorAll('.btn-action');


    actionButtons.forEach(btn => {

        btn.addEventListener('click', function(e) {


            const action = this.textContent.trim();


            // Laisser Django gérer les liens
            if(this.tagName === "A"){
                return;
            }


            // Gestion JS uniquement des boutons
            if(this.tagName === "BUTTON"){

                e.preventDefault();

                const row = this.closest('tr');

                const reference = row?.querySelector('td:first-child')?.textContent || '';

                handleTableAction(action, reference);

            }


        });

    });

}

function handleTableAction(action, reference) {
    const actions = {
        'Voir': () => showNotification(`Affichage des détails de ${reference}`, 'info'),
        'Modifier': () => showNotification(`Modification de ${reference}`, 'info'),
        'Supprimer': () => confirmDelete(reference),
        'Facture': () => downloadInvoice(reference),
        'Détails': () => showNotification(`Affichage des détails de ${reference}`, 'info'),
        'Reçu': () => downloadReceipt(reference),
        'Confirmer': () => confirmPayment(reference),
        'Renouveler': () => showNotification(`Renouvellement de ${reference}`, 'info'),
    };

    if (actions[action]) {
        actions[action]();
    }
}

function confirmDelete(reference) {
    if (confirm(`Êtes-vous sûr de vouloir supprimer ${reference} ?`)) {
        showNotification(`${reference} a été supprimé avec succès`, 'success');
    }
}

function downloadInvoice(reference) {
    showNotification(`Téléchargement de la facture pour ${reference}...`, 'info');
    setTimeout(() => {
        showNotification(`Facture téléchargée avec succès`, 'success');
    }, 1500);
}

function downloadReceipt(reference) {
    showNotification(`Téléchargement du reçu pour ${reference}...`, 'info');
    setTimeout(() => {
        showNotification(`Reçu téléchargé avec succès`, 'success');
    }, 1500);
}

function confirmPayment(reference) {
    if (confirm(`Confirmer le paiement pour ${reference} ?`)) {
        showNotification(`Paiement confirmé pour ${reference}`, 'success');
    }
}

// ============================================
// FILTERS
// ============================================

function initializeFilters() {
    const filterSelects = document.querySelectorAll('.filter-select');
    const filterInputs = document.querySelectorAll('.filter-input');
    const filterBtn = document.querySelector('.btn-filter');

    filterSelects.forEach(select => {
        select.addEventListener('change', applyFilters);
    });

    filterInputs.forEach(input => {
        input.addEventListener('input', applyFilters);
    });

    if (filterBtn) {
        filterBtn.addEventListener('click', applyFilters);
    }
}

function applyFilters() {
    showNotification('Filtres appliqués', 'info');
    console.log('Filters applied');
}

// ============================================
// DASHBOARD DATA
// ============================================

function loadDashboardData() {
    console.log('Loading dashboard data...');

    // Update KPI cards with animation
    animateKPICards();

    // Load charts
    loadCharts();

    // Load activity
    loadActivity();
}

function animateKPICards() {
    const kpiCards = document.querySelectorAll('.kpi-card');

    kpiCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';

        setTimeout(() => {
            card.style.transition = 'all 0.5s ease-out';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

function loadCharts() {
    const chartCards = document.querySelectorAll('.chart-card');

    chartCards.forEach(card => {
        const chartBars = card.querySelectorAll('.chart-bar');

        chartBars.forEach((bar, index) => {
            const height = bar.style.height;
            bar.style.height = '0';

            setTimeout(() => {
                bar.style.transition = 'height 0.5s ease-out';
                bar.style.height = height;
            }, index * 100);
        });
    });
}

function loadActivity() {
    const activityItems = document.querySelectorAll('.activity-item');

    activityItems.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';

        setTimeout(() => {
            item.style.transition = 'all 0.5s ease-out';
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, index * 100);
    });
}

// ============================================
// SPACE MANAGEMENT
// ============================================

function initializeSpaceActions() {
    const spaceActionButtons = document.querySelectorAll('.space-actions button');

    spaceActionButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.textContent.trim();
            const spaceName = this.closest('.space-card-admin')?.querySelector('h3')?.textContent || '';

            handleSpaceAction(action, spaceName);
        });
    });
}

function handleSpaceAction(action, spaceName) {
    const actions = {
        'Modifier': () => showNotification(`Modification de ${spaceName}`, 'info'),
        'Disponibilité': () => showNotification(`Gestion de la disponibilité de ${spaceName}`, 'info'),
        'Supprimer': () => confirmDeleteSpace(spaceName),
        'Détails': () => showNotification(`Détails de ${spaceName}`, 'info'),
        'Libérer': () => confirmFreeSpace(spaceName),
    };

    if (actions[action]) {
        actions[action]();
    }
}

function confirmDeleteSpace(spaceName) {
    if (confirm(`Êtes-vous sûr de vouloir supprimer ${spaceName} ?`)) {
        showNotification(`${spaceName} a été supprimé`, 'success');
    }
}

function confirmFreeSpace(spaceName) {
    if (confirm(`Êtes-vous sûr de vouloir libérer ${spaceName} ?`)) {
        showNotification(`${spaceName} a été libéré`, 'success');
    }
}

// ============================================
// COMPLAINT MANAGEMENT
// ============================================

function initializeComplaintActions() {
    const complaintButtons = document.querySelectorAll('.complaint-actions button');

    complaintButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.textContent.trim();
            const complaintRef = this.closest('.complaint-card')?.querySelector('.complaint-ref')?.textContent || '';

            handleComplaintAction(action, complaintRef);
        });
    });
}

function handleComplaintAction(action, complaintRef) {
    if (action === 'Voir Détails') {
        showNotification(`Affichage des détails de ${complaintRef}`, 'info');
    } else if (action === 'Marquer comme Résolue') {
        if (confirm(`Marquer ${complaintRef} comme résolue ?`)) {
            showNotification(`${complaintRef} a été marquée comme résolue`, 'success');
        }
    }
}

// ============================================
// SETTINGS
// ============================================

function initializeSettings() {
    const settingsForms = document.querySelectorAll('.settings-form');

    settingsForms.forEach(form => {
        const buttons = form.querySelectorAll('button');

        buttons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                if (this.textContent.includes('Enregistrer')) {
                    e.preventDefault();
                    showNotification('Paramètres enregistrés avec succès', 'success');
                } else if (this.textContent.includes('Modifier')) {
                    e.preventDefault();
                    showNotification('Cliquez pour modifier les paramètres', 'info');
                } else if (this.textContent.includes('Changer')) {
                    e.preventDefault();
                    showNotification('Redirection vers le changement de mot de passe...', 'info');
                } else if (this.textContent.includes('2FA')) {
                    e.preventDefault();
                    showNotification('Activation de l\'authentification à deux facteurs...', 'info');
                } else if (this.textContent.includes('Sessions')) {
                    e.preventDefault();
                    showNotification('Affichage des sessions actives...', 'info');
                }
            });
        });
    });
}

// ============================================
// DATE RANGE FILTER
// ============================================

function initializeDateRangeFilter() {
    const filterBtn = document.querySelector('.btn-filter');

    if (filterBtn) {
        filterBtn.addEventListener('click', function() {
            const dateFrom = document.getElementById('date-from')?.value;
            const dateTo = document.getElementById('date-to')?.value;

            if (dateFrom && dateTo) {
                showNotification(`Données filtrées du ${dateFrom} au ${dateTo}`, 'success');
            }
        });
    }
}

// ============================================
// ANIMATIONS
// ============================================

const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
`;
document.head.appendChild(style);

// ============================================
// RESPONSIVE HANDLING
// ============================================

window.addEventListener('resize', function() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar && window.innerWidth > 768) {
        sidebar.classList.remove('active');
    }
});

// ============================================
// EXPORT FUNCTIONS
// ============================================

window.showSection = showSection;
window.updatePageTitle = updatePageTitle;
window.handleSearch = handleSearch;
window.showNotification = showNotification;
window.handleTableAction = handleTableAction;
window.applyFilters = applyFilters;
window.loadDashboardData = loadDashboardData;
window.initializeSpaceActions = initializeSpaceActions;
window.initializeComplaintActions = initializeComplaintActions;
window.initializeSettings = initializeSettings;
window.initializeDateRangeFilter = initializeDateRangeFilter;

// ============================================
// CALL ADDITIONAL INITIALIZERS
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initializeSpaceActions();
    initializeComplaintActions();
    initializeSettings();
    initializeDateRangeFilter();
});

