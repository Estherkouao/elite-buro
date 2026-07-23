/*
 * EliteBuro Member Dashboard
 * JavaScript Functions for Member Management
 */

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    initializeNavigation();
    initializeTabs();
    initializeComplaintForm();
    initializeActions();
    loadMemberData();
});

// ============================================
// NAVIGATION
// ============================================

function initializeNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            // Remove active class from all links
            navLinks.forEach(l => l.classList.remove('active'));

            // Add active class to clicked link
            this.classList.add('active');

            // Get section ID
            const sectionId = this.getAttribute('data-section');

            // Show corresponding section
            goToSection(sectionId);
        });
    });
}

function goToSection(sectionId) {
    // Hide all sections
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => section.classList.remove('active'));

    // Show selected section
    const selectedSection = document.getElementById(sectionId);
    if (selectedSection) {
        selectedSection.classList.add('active');
    }

    // Update active nav link
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('data-section') === sectionId) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================
// TABS
// ============================================

function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all tabs
            tabButtons.forEach(b => b.classList.remove('active'));

            // Add active class to clicked tab
            this.classList.add('active');

            const tabName = this.getAttribute('data-tab');
            filterReservations(tabName);
        });
    });
}

function filterReservations(tabName) {
    console.log('Filtering reservations by:', tabName);
    showNotification(`Affichage des réservations: ${tabName}`, 'info');
}


// ============================================
// COMPLAINT FORM
// ============================================

function initializeComplaintForm() {
    const complaintForm = document.getElementById('complaint-form');

    if (complaintForm) {
        const form = complaintForm.querySelector('form');
        if (form) {
            form.addEventListener('submit', submitComplaint);
        }
    }
}

function openComplaintForm() {
    const form = document.getElementById('complaint-form');
    if (form) {
        form.classList.remove('hidden');
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function closeComplaintForm() {
    const form = document.getElementById('complaint-form');
    if (form) {
        form.classList.add('hidden');
        const f = form.querySelector('form');
        if (f) f.reset();
    }
}

function submitComplaint(event) {
    event.preventDefault();

    const form = event.target;
    const category = form.querySelector('select[required]')?.value;
    const description = form.querySelector('textarea')?.value;

    if (!category || !description) {
        showNotification('Veuillez remplir tous les champs obligatoires', 'error');
        return;
    }

    // Simulate submission
    showNotification('Réclamation en cours de création...', 'info');

    setTimeout(() => {
        const refNumber = generateComplaintReference();
        showNotification(`Réclamation créée avec succès! Référence: ${refNumber}`, 'success');
        closeComplaintForm();
        form.reset();
    }, 1500);
}

function generateComplaintReference() {
    const year = new Date().getFullYear();
    const random = Math.floor(Math.random() * 10000);
    return `REF-${year}-${String(random).padStart(4, '0')}`;
}

// ============================================
// ACTIONS
// ============================================

function initializeActions() {
    // Initialize all action buttons
    const actionButtons = document.querySelectorAll('.btn-action, .btn-primary, .btn-secondary, .btn-small, .btn-qr');

    actionButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            const text = this.textContent.trim();

            // Payment
            if (text.includes('Payer')) {
                e.preventDefault();
                handlePayment(this);
            }

            // Download
            if (text.includes('Télécharger')) {
                e.preventDefault();
                downloadFile(this);
            }

            // Cancellation
            if (text.includes('Annuler')) {
                e.preventDefault();
                handleCancellation(this);
            }
        });
    });
}

// ============================================
// PAYMENT HANDLING
// ============================================

function handlePayment(button) {
    const reference =
        button.closest('tr')?.querySelector('td:first-child')?.textContent ||
        button.closest('.invoice-card')?.querySelector('h4')?.textContent ||
        'Paiement';

    if (confirm(`Procéder au paiement pour ${reference}?`)) {
        showNotification('Redirection vers le paiement...', 'info');

        setTimeout(() => {
            showNotification('Paiement traité avec succès!', 'success');
        }, 2000);
    }
}

function payInvoice(invoiceRef) {
    handlePayment({
        closest: () => ({
            querySelector: () => ({ textContent: invoiceRef })
        })
    });
}

// ============================================
// FILE DOWNLOADS
// ============================================

function downloadFile(button) {
    const fileName = button.textContent.trim();
    showNotification(`Téléchargement de ${fileName}...`, 'info');

    setTimeout(() => {
        showNotification(`${fileName} téléchargé avec succès!`, 'success');
    }, 1500);
}

function downloadInvoice(invoiceRef) {
    showNotification(`Téléchargement de la facture ${invoiceRef}...`, 'info');

    setTimeout(() => {
        showNotification(`Facture ${invoiceRef} téléchargée avec succès!`, 'success');
    }, 1500);
}

function downloadDocument(docType) {
    const docNames = {
        'contrat': 'Contrat de Domiciliation',
        'attestation': 'Attestation de Domiciliation'
    };

    showNotification(`Téléchargement du ${docNames[docType]}...`, 'info');

    setTimeout(() => {
        showNotification(`${docNames[docType]} téléchargé avec succès!`, 'success');
    }, 1500);
}

function viewDocument(docType) {
    const docNames = {
        'contrat': 'Contrat de Domiciliation',
        'attestation': 'Attestation de Domiciliation',
        'courrier': 'Historique Courrier'
    };

    showNotification(`Affichage du ${docNames[docType]}...`, 'info');
}

// ============================================
// CANCELLATION
// ============================================

function handleCancellation(button) {
    const row = button.closest('tr');
    const reference = row?.querySelector('td:first-child')?.textContent || 'cette réservation';

    if (confirm(`Êtes-vous sûr de vouloir annuler ${reference}?`)) {
        showNotification('Annulation en cours...', 'info');

        setTimeout(() => {
            showNotification(`${reference} a été annulée avec succès!`, 'success');
        }, 1500);
    }
}

// ============================================
// DOMICILIATION
// ============================================

function renewDomiciliation() {
    if (confirm('Renouveler votre abonnement de domiciliation?')) {
        showNotification('Renouvellement en cours...', 'info');

        setTimeout(() => {
            showNotification('Abonnement renouvelé avec succès!', 'success');
        }, 1500);
    }
}

function changePlan() {
    showNotification('Redirection vers le changement de plan...', 'info');

    setTimeout(() => {
        goToSection('domiciliation');
    }, 1000);
}

// ============================================
// PROFILE
// ============================================

function editProfile() {
    // Toggle disabled inputs
    const inputs = document.querySelectorAll('.profile-form input');
    if (!inputs.length) return;

    const isDisabled = inputs[0].disabled;

    inputs.forEach(input => {
        input.disabled = !isDisabled;
    });

    const btn = document.querySelector('.profile-form button');
    if (btn) {
        btn.textContent = isDisabled ? 'Annuler' : 'Modifier';
        btn.className = isDisabled ? 'btn-secondary' : 'btn-primary';
    }

    if (!isDisabled) {
        showNotification('Mode édition activé', 'info');
    }
}

function changePassword() {
    showNotification('Redirection vers le changement de mot de passe...', 'info');
}

function enable2FA() {
    showNotification('Activation de l\'authentification à deux facteurs...', 'info');

    setTimeout(() => {
        showNotification('2FA activée avec succès!', 'success');
    }, 2000);
}

function viewSessions() {
    showNotification('Affichage des sessions actives...', 'info');
}

function savePreferences() {
    showNotification('Préférences enregistrées avec succès!', 'success');
}

// ============================================
// RESERVATION HANDLING
// ============================================

function goToReservation() {
    goToSection('reservations');
    showNotification('Redirection vers les réservations...', 'info');
}

// ============================================
// NOTIFICATIONS
// ============================================

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
        'warning': { bg: '#f39c12', color: 'white' }
    };

    const typeStyle = colors[type] || colors['info'];
    notification.style.backgroundColor = typeStyle.bg;
    notification.style.color = typeStyle.color;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// ============================================
// DATA LOADING & ANIMATIONS
// ============================================

function loadMemberData() {
    animateStatusCards();
    animateReservationCards();
    animateUpcomingItems();
    animateAlerts();
}

function animateStatusCards() {
    const cards = document.querySelectorAll('.status-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease-out';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

function animateReservationCards() {
    const cards = document.querySelectorAll('.reservation-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease-out';
            card.style.opacity = '1';
            card.style.transform = 'translateX(0)';
        }, index * 100);
    });
}

function animateUpcomingItems() {
    const items = document.querySelectorAll('.upcoming-item');
    items.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(20px)';
        setTimeout(() => {
            item.style.transition = 'all 0.5s ease-out';
            item.style.opacity = '1';
        item.style.transform = 'translateX(0)';
        }, index * 100);
    });
}

function animateAlerts() {
    const alerts = document.querySelectorAll('.alert-item');
    alerts.forEach((alert, index) => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(10px)';
        setTimeout(() => {
            alert.style.transition = 'all 0.5s ease-out';
            alert.style.opacity = '1';
            alert.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// Animations injected
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
// EXPORT FUNCTIONS (global)
// ============================================

window.goToSection = goToSection;
window.openComplaintForm = openComplaintForm;
window.closeComplaintForm = closeComplaintForm;
window.submitComplaint = submitComplaint;
window.handlePayment = handlePayment;
window.payInvoice = payInvoice;
window.downloadInvoice = downloadInvoice;
window.downloadDocument = downloadDocument;
window.viewDocument = viewDocument;
window.handleCancellation = handleCancellation;
window.renewDomiciliation = renewDomiciliation;
window.changePlan = changePlan;
window.editProfile = editProfile;
window.changePassword = changePassword;
window.enable2FA = enable2FA;
window.viewSessions = viewSessions;
window.savePreferences = savePreferences;
window.goToReservation = goToReservation;
window.showNotification = showNotification;
window.filterReservations = filterReservations;

