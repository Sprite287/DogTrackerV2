/**
 * Simplified Modal Management
 */

// Edit Dog Modal Population
function fillEditDogModal(btn) {
    const form = document.getElementById('editDogForm');
    if (!form) return false;
    
    // Simple field mapping
    const fields = [
        'name', 'adoption_status', 'age', 'breed', 
        'intake_date', 'microchip_id', 'notes', 
        'medical_info', 'dog_id'
    ];
    
    fields.forEach(fieldName => {
        const input = form.querySelector(`[name="${fieldName}"]`);
        const value = btn.getAttribute(`data-dog-${fieldName.replace('_', '-')}`);
        if (input && value) {
            input.value = value;
        }
    });
    
    // Set form action
    const dogId = btn.getAttribute('data-dog-id');
    const isFromDetails = btn.getAttribute('data-from-details') === 'true';
    
    if (dogId) {
        form.setAttribute('hx-post', `/dogs/${dogId}/edit`);
        form.querySelector('[name="dog_id"]').value = dogId;
        form.querySelector('[name="from_details"]').value = isFromDetails ? 'details' : '';
    }
    
    return true;
}

// Personality Modal Population
function fillPersonalityModal(btn) {
    const form = document.getElementById('editPersonalityForm');
    if (!form) return false;
    
    const dogId = btn.getAttribute('data-dog-id');
    const dogName = btn.getAttribute('data-dog-name');
    
    if (dogId) {
        form.setAttribute('hx-post', `/dogs/${dogId}/edit-personality`);
        form.querySelector('[name="dog_id"]').value = dogId;
        
        // Update modal title
        const nameSpan = document.getElementById('personalityDogName');
        if (nameSpan && dogName) {
            nameSpan.textContent = dogName;
        }
        
        // Populate fields
        const fields = ['energy_level', 'personality_notes', 'social_notes', 'special_story', 'temperament_tags'];
        fields.forEach(fieldName => {
            const input = form.querySelector(`[name="${fieldName}"]`);
            const value = btn.getAttribute(`data-${fieldName.replace('_', '-')}`);
            if (input && value && value !== 'None') {
                input.value = value;
            }
        });
    }
    
    return true;
}

// Confirmation Modal
function showEmpathicConfirm(title, message, confirmText, confirmCallback) {
    const modal = document.getElementById('empathicConfirmModal');
    if (!modal) return;
    
    // Set content
    document.getElementById('empathicConfirmTitle').textContent = title;
    document.getElementById('empathicConfirmMessage').textContent = message;
    document.getElementById('empathicConfirmButton').textContent = confirmText;
    
    // Set callback
    const confirmBtn = document.getElementById('empathicConfirmButton');
    confirmBtn.onclick = function() {
        if (confirmCallback) confirmCallback();
        bootstrap.Modal.getInstance(modal).hide();
    };
    
    // Show modal
    new bootstrap.Modal(modal).show();
}

// Global event handlers
document.addEventListener('click', function(event) {
    const target = event.target;
    
    // Edit dog button
    if (target.classList.contains('edit-dog-btn') || target.closest('.edit-dog-btn')) {
        const btn = target.classList.contains('edit-dog-btn') ? target : target.closest('.edit-dog-btn');
        fillEditDogModal(btn);
    }
    
    // Personality edit button
    if (target.classList.contains('edit-personality-btn') || target.closest('.edit-personality-btn')) {
        const btn = target.classList.contains('edit-personality-btn') ? target : target.closest('.edit-personality-btn');
        fillPersonalityModal(btn);
    }
    
    // Delete confirmation
    if (target.hasAttribute('data-confirm-delete')) {
        event.preventDefault();
        const message = target.getAttribute('data-confirm-delete') || 'Are you sure?';
        showEmpathicConfirm('Confirm Deletion', message, 'Delete', function() {
            if (target.href) {
                window.location.href = target.href;
            } else if (target.form) {
                target.form.submit();
            }
        });
    }
});