/**
 * Simplified Form Handling
 */

// Simple form validation
function validateForm(form) {
    if (!form) return false;
    
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('is-invalid');
            
            // Show simple error
            let feedback = field.parentNode.querySelector('.invalid-feedback');
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                field.parentNode.appendChild(feedback);
            }
            feedback.textContent = 'This field is required.';
        } else {
            field.classList.remove('is-invalid');
            const feedback = field.parentNode.querySelector('.invalid-feedback');
            if (feedback) feedback.remove();
        }
    });
    
    return isValid;
}

// Clear validation errors
function clearFormErrors(form) {
    if (!form) return;
    
    form.querySelectorAll('.is-invalid').forEach(field => {
        field.classList.remove('is-invalid');
    });
    
    form.querySelectorAll('.invalid-feedback').forEach(feedback => {
        feedback.remove();
    });
}

// Form submission handling
document.addEventListener('submit', function(event) {
    const form = event.target;
    
    // Skip validation for certain forms
    if (form.hasAttribute('data-skip-validation')) return;
    
    if (!validateForm(form)) {
        event.preventDefault();
        showAlert('Please fill in all required fields.', 'warning');
    }
});

// Clear errors when typing
document.addEventListener('input', function(event) {
    const field = event.target;
    if (field.classList.contains('is-invalid')) {
        field.classList.remove('is-invalid');
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) feedback.remove();
    }
});

// Modal form reset
document.addEventListener('show.bs.modal', function(event) {
    const modal = event.target;
    const form = modal.querySelector('form');
    if (form) {
        clearFormErrors(form);
    }
});