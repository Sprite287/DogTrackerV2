/**
 * Simplified Animation Handling
 */

// Simple loading states for buttons
document.body.addEventListener('htmx:beforeRequest', function(event) {
    const target = event.target;
    
    if (target.tagName === 'BUTTON' || target.classList.contains('btn')) {
        target.classList.add('btn-loading');
        target.disabled = true;
        
        const originalText = target.textContent;
        target.setAttribute('data-original-text', originalText);
        target.textContent = originalText + '...';
    }
});

document.body.addEventListener('htmx:afterRequest', function(event) {
    const target = event.target;
    
    if (target.classList.contains('btn-loading')) {
        target.classList.remove('btn-loading');
        target.disabled = false;
        
        const originalText = target.getAttribute('data-original-text');
        if (originalText) {
            target.textContent = originalText;
            target.removeAttribute('data-original-text');
        }
    }
});

// Add grow-in animation to new elements
document.addEventListener('htmx:afterSwap', function() {
    const newElements = document.querySelectorAll('.card, .alert');
    newElements.forEach(el => {
        if (!el.classList.contains('grow-in')) {
            el.classList.add('grow-in');
        }
    });
});

// Initialize animations on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add gentle animations to existing elements
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.add('caring-hover');
    });
    
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.classList.add('caring-hover');
    });
});