/**
 * EliteBuro Footer Component
 * Gestion des interactions du footer
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeFooter();
});

/**
 * Initialiser le footer
 */
function initializeFooter() {
    // Gestion de la newsletter
    const newsletterForm = document.querySelector('.newsletter-form');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', handleNewsletterSubmit);
    }

    // Gestion des liens sociaux
    const socialLinks = document.querySelectorAll('.social-link');
    socialLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            if (url && url !== '#') {
                window.open(url, '_blank');
            }
        });
    });

    // Gestion des liens du footer
    const footerLinks = document.querySelectorAll('.footer-link');
    footerLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') {
                e.preventDefault();
                console.log('Lien non configuré:', this.textContent);
            }
        });
    });

    // Scroll to top button (optionnel)
    addScrollToTopButton();
}

/**
 * Gérer la soumission du formulaire newsletter
 * @param {Event} event - L'événement de soumission
 */
function handleNewsletterSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const input = form.querySelector('input[type="email"]');
    const email = input.value.trim();

    if (!email) {
        showNotification('Veuillez entrer une adresse email valide.', 'error');
        return;
    }

    // Validation email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showNotification('Veuillez entrer une adresse email valide.', 'error');
        return;
    }

    // Simuler l'envoi
    const button = form.querySelector('button');
    const originalText = button.textContent;
    button.textContent = 'Envoi en cours...';
    button.disabled = true;

    // Simuler un délai d'envoi
    setTimeout(() => {
        showNotification('Merci de votre inscription! Vérifiez votre email.', 'success');
        input.value = '';
        button.textContent = originalText;
        button.disabled = false;
    }, 1500);
}

/**
 * Afficher une notification
 * @param {string} message - Le message à afficher
 * @param {string} type - Le type de notification (success, error, info)
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Ajouter les styles si nécessaire
    if (!document.querySelector('style[data-notification]')) {
        const style = document.createElement('style');
        style.setAttribute('data-notification', 'true');
        style.textContent = `
            .notification {
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 16px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                z-index: 9999;
                animation: slideInRight 0.3s ease-out;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }

            .notification-success {
                background: #0B6B39;
                color: white;
            }

            .notification-error {
                background: #C0392B;
                color: white;
            }

            .notification-info {
                background: #0D2B55;
                color: white;
            }

            @keyframes slideInRight {
                from {
                    opacity: 0;
                    transform: translateX(100px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            @keyframes slideOutRight {
                from {
                    opacity: 1;
                    transform: translateX(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(100px);
                }
            }
        `;
        document.head.appendChild(style);
    }

    document.body.appendChild(notification);

    // Supprimer la notification après 4 secondes
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 4000);
}

/**
 * Ajouter un bouton "Retour en haut"
 */
function addScrollToTopButton() {
    // Créer le bouton
    const scrollTopBtn = document.createElement('button');
    scrollTopBtn.className = 'scroll-to-top';
    scrollTopBtn.innerHTML = '↑';
    scrollTopBtn.title = 'Retour en haut';

    // Ajouter les styles
    if (!document.querySelector('style[data-scroll-top]')) {
        const style = document.createElement('style');
        style.setAttribute('data-scroll-top', 'true');
        style.textContent = `
            .scroll-to-top {
                position: fixed;
                bottom: 100px;
                right: 20px;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: #C9A02C;
                color: #0D2B55;
                border: none;
                font-size: 20px;
                font-weight: bold;
                cursor: pointer;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                z-index: 999;
                box-shadow: 0 4px 12px rgba(201, 160, 44, 0.3);
            }

            .scroll-to-top.show {
                opacity: 1;
                visibility: visible;
            }

            .scroll-to-top:hover {
                background: #E8C547;
                transform: translateY(-4px);
                box-shadow: 0 8px 16px rgba(201, 160, 44, 0.4);
            }

            .scroll-to-top:active {
                transform: translateY(0);
            }
        `;
        document.head.appendChild(style);
    }

    document.body.appendChild(scrollTopBtn);

    // Gérer le scroll
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollTopBtn.classList.add('show');
        } else {
            scrollTopBtn.classList.remove('show');
        }
    });

    // Gérer le clic
    scrollTopBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

/**
 * Exporter les fonctions pour utilisation externe
 */
window.FooterComponent = {
    handleNewsletterSubmit: handleNewsletterSubmit,
    showNotification: showNotification,
    addScrollToTopButton: addScrollToTopButton
};
