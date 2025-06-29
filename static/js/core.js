/**
 * Simplified Core JavaScript - Essential functionality only
 */

// CSRF Support for HTMX
document.body.addEventListener('htmx:configRequest', function(event) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (csrfToken) {
        event.detail.headers['X-CSRFToken'] = csrfToken;
    }
});

// Simple modal management
document.addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.successful && evt.target) {
        // Close modals after successful form submission
        if (evt.target.id === 'addDogForm' || evt.target.id === 'editDogForm') {
            const modalEl = evt.target.closest('.modal');
            if (modalEl) {
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();
                const form = modalEl.querySelector('form');
                if (form) form.reset();
            }
        }
    }
});

// Simple error handling
htmx.on('htmx:responseError', function(evt) {
    showAlert('Something went wrong. Please try again.', 'warning');
});

htmx.on('htmx:sendError', function(evt) {
    showAlert('Connection issue. Please check your network.', 'warning');
});

// Unified alert system - replacing showAlert, showSuccessMessage, showErrorMessage
function showAlert(message, type = 'info') {
    // Remove any existing alerts
    document.querySelectorAll('.alert.position-fixed').forEach(alert => alert.remove());
    
    // Check for alerts div first (for page-level alerts)
    const alertsDiv = document.getElementById('alerts');
    if (alertsDiv) {
        const alertHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        alertsDiv.innerHTML = alertHTML;
        return;
    }
    
    // Otherwise create floating alert (replacing showSuccessMessage/showErrorMessage)
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    
    setTimeout(() => alert.remove(), 5000);
}

// Dark mode toggle
document.addEventListener('DOMContentLoaded', function() {
    // Mark page as loaded
    document.body.classList.add('loaded');
    
    // Initialize dark mode
    const themeToggle = document.getElementById('theme-toggle-checkbox');
    if (!themeToggle) return;
    
    // Check saved preference
    const savedTheme = localStorage.getItem('darkMode');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDarkMode = savedTheme === 'true' || (savedTheme === null && prefersDark);
    
    // Apply theme
    if (isDarkMode) {
        document.documentElement.classList.add('dark-mode');
        document.body.classList.add('dark-mode');
        themeToggle.checked = true;
    }
    
    // Toggle event
    themeToggle.addEventListener('change', function() {
        if (this.checked) {
            document.documentElement.classList.add('dark-mode');
            document.body.classList.add('dark-mode');
            localStorage.setItem('darkMode', 'true');
        } else {
            document.documentElement.classList.remove('dark-mode');
            document.body.classList.remove('dark-mode');
            localStorage.setItem('darkMode', 'false');
        }
    });
});

// Clear forms when modals open
document.addEventListener('show.bs.modal', function(event) {
    const modal = event.target;
    const form = modal.querySelector('form');
    if (form && modal.id.includes('add')) {
        form.reset();
    }
});

// Initialize popovers after HTMX swaps
document.addEventListener('htmx:afterSwap', function() {
    const popoverElements = document.querySelectorAll('[data-bs-toggle="popover"]');
    popoverElements.forEach(el => new bootstrap.Popover(el));
});

// Shared utility functions
function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// Convenience wrappers for backward compatibility
function showSuccessMessage(message) {
    showAlert(message, 'success');
}

function showErrorMessage(message) {
    showAlert(message, 'danger');
}

// Event icon mapping for calendars
const eventIconMap = {
    'medication': 'bi-capsule',
    'appointment': 'bi-calendar-check',
    'monitoring': 'bi-heart-pulse',
    'reminder': 'bi-bell',
    'other': 'bi-calendar-event'
};

// Get event icon by type
function getEventIcon(eventType) {
    return eventIconMap[eventType] || eventIconMap['other'];
}

// Dog Search Filter Functionality
function attachDogSearchFilter() {
    const searchInput = document.getElementById('dogSearch');
    const dogCards = document.getElementById('dogCards');
    
    if (!searchInput || !dogCards) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        const allCards = dogCards.querySelectorAll('[id^="dog-card-"]');
        
        allCards.forEach(card => {
            if (!searchTerm) {
                // Show all cards if search is empty
                card.style.display = '';
                return;
            }
            
            // Get dog information from the card
            const dogName = card.querySelector('.card-title')?.textContent?.toLowerCase() || '';
            const dogBreed = card.querySelector('.info-item .fw-medium')?.textContent?.toLowerCase() || '';
            const personalityText = card.querySelector('.personality-preview p')?.textContent?.toLowerCase() || '';
            const temperamentTags = Array.from(card.querySelectorAll('.temperament-tag'))
                .map(tag => tag.textContent.toLowerCase()).join(' ');
            
            // Search in multiple fields
            const searchableText = `${dogName} ${dogBreed} ${personalityText} ${temperamentTags}`;
            
            if (searchableText.includes(searchTerm)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
        
        // Show/hide "no results" message
        const visibleCards = dogCards.querySelectorAll('[id^="dog-card-"]:not([style*="display: none"])');
        let noResultsMsg = dogCards.querySelector('.no-search-results');
        
        if (visibleCards.length === 0 && searchTerm) {
            if (!noResultsMsg) {
                noResultsMsg = document.createElement('div');
                noResultsMsg.className = 'no-search-results col-12 text-center py-5';
                noResultsMsg.innerHTML = `
                    <div class="text-muted">
                        <i class="bi bi-search mb-3" style="font-size: 3rem;"></i>
                        <h4>No dogs found</h4>
                        <p>Try adjusting your search terms</p>
                    </div>
                `;
                dogCards.appendChild(noResultsMsg);
            }
            noResultsMsg.style.display = '';
        } else if (noResultsMsg) {
            noResultsMsg.style.display = 'none';
        }
    });
}