// dog_details.js

(function() {
  if (window.dogDetailsJSLoaded) return;
  window.dogDetailsJSLoaded = true;

  document.addEventListener('DOMContentLoaded', function () {
    // --- Add Appointment Modal ---
    var addAppointmentModal = document.getElementById('addAppointmentModal');
    if (addAppointmentModal) {
      addAppointmentModal.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        var dogId = button ? button.getAttribute('data-dog-id') : null;
        var form = addAppointmentModal.querySelector('form');
        if (dogId && window.appointmentUrls) {
          form.setAttribute('action', window.appointmentUrls.add);
          form.setAttribute('hx-post', window.appointmentUrls.add);
        }
        form.reset();
      });
    }

    // --- Edit Appointment Modal ---
    var editAppointmentModal = document.getElementById('editAppointmentModal');
    if (editAppointmentModal) {
      editAppointmentModal.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        var apptId = button ? button.getAttribute('data-id') : null;
        var dogId = button ? button.getAttribute('data-dog-id') : null;
        var form = editAppointmentModal.querySelector('form');
        console.log('Edit Appointment Modal opened. dogId:', dogId, 'apptId:', apptId, 'form:', form);
        if (dogId && apptId && window.appointmentUrls) {
          const editUrl = window.appointmentUrls.editTemplate + apptId;
          form.setAttribute('action', editUrl);
          form.setAttribute('hx-post', editUrl);
          form.querySelector('#editApptId').value = apptId;
          console.log('Setting edit form action:', editUrl);
          // Remove and re-add the form to force HTMX to re-initialize
          const parent = form.parentNode;
          const next = form.nextSibling;
          parent.removeChild(form);
          if (next) {
            parent.insertBefore(form, next);
          } else {
            parent.appendChild(form);
          }
          // Fetch appointment data and fill fields
          const apiUrl = window.appointmentUrls.apiGetTemplate + apptId;
          fetch(apiUrl)
            .then(res => res.json())
            .then(data => {
              // Fill select options for type
              var typeSelect = form.querySelector('#editApptType');
              typeSelect.innerHTML = '';
              (window.appointmentTypes || []).forEach(function(type) {
                var opt = document.createElement('option');
                opt.value = type.id;
                opt.textContent = type.name;
                if (type.id == data.type_id) opt.selected = true;
                typeSelect.appendChild(opt);
              });
              form.querySelector('#editApptTitle').value = data.title || '';
              form.querySelector('#editApptStart').value = data.start_datetime ? data.start_datetime.slice(0, 16) : '';
              form.querySelector('#editApptEnd').value = data.end_datetime ? data.end_datetime.slice(0, 16) : '';
              form.querySelector('#editApptStatus').value = data.status || 'scheduled';
              form.querySelector('#editApptNotes').value = data.description || '';
            });
        }
      });
    }

    // --- Add Medicine Modal ---
    var addMedicineModal = document.getElementById('addMedicineModal');
    if (addMedicineModal) {
      addMedicineModal.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        var dogId = button ? button.getAttribute('data-dog-id') : null;
        var form = addMedicineModal.querySelector('form');
        if (dogId && window.medicineUrls) {
          form.setAttribute('action', window.medicineUrls.add);
          form.setAttribute('hx-post', window.medicineUrls.add);
        }
        form.reset();
      });
    }

    // --- Edit Medicine Modal ---
    var editMedicineModal = document.getElementById('editMedicineModal');
    if (editMedicineModal) {
      editMedicineModal.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        var medId = button ? button.getAttribute('data-id') : null;
        var dogId = button ? button.getAttribute('data-dog-id') : null;
        var form = editMedicineModal.querySelector('form');
        if (dogId && medId && window.medicineUrls) {
          const editUrl = window.medicineUrls.editTemplate + medId;
          form.setAttribute('action', editUrl);
          form.setAttribute('hx-post', editUrl);
          form.querySelector('#editMedId').value = medId;
          // Fetch medicine data and fill fields
          fetch(window.medicineUrls.apiGetTemplate + medId)
            .then(res => res.json())
            .then(data => {
              // Fill select options for preset
              var presetSelect = form.querySelector('#editMedPreset');
              presetSelect.innerHTML = '';
              (window.medicinePresets || []).forEach(function(preset) {
                var opt = document.createElement('option');
                opt.value = preset.id;
                opt.textContent = preset.name;
                if (preset.id == data.medicine_id) opt.selected = true;
                presetSelect.appendChild(opt);
              });
              form.querySelector('#editMedDosage').value = data.dosage || '';
              form.querySelector('#editMedUnit').value = data.unit || '';
              form.querySelector('#editMedFrequency').value = data.frequency || 'daily';
              form.querySelector('#editMedStart').value = data.start_date ? data.start_date.slice(0, 10) : '';
              form.querySelector('#editMedEnd').value = data.end_date ? data.end_date.slice(0, 10) : '';
              form.querySelector('#editMedStatus').value = data.status || 'active';
              form.querySelector('#editMedNotes').value = data.notes || '';
            });
        }
      });
    }
  });

  // Auto-close modals after successful add/edit
  document.body.addEventListener('htmx:afterSwap', function(evt) {
    // Only run if appointments-list was swapped
    if (evt.detail && evt.detail.target && evt.detail.target.id === 'appointments-list') {
      setTimeout(function() {
        document.body.classList.remove('modal-open');
        document.querySelectorAll('.modal-backdrop').forEach(function(el) {
          el.parentNode.removeChild(el);
        });
        document.querySelectorAll('.modal.show').forEach(function(modal) {
          var instance = bootstrap.Modal.getInstance(modal);
          if (instance) instance.hide();
        });
        // Re-initialize all modals in the new appointments-list
        document.querySelectorAll('#appointments-list .modal').forEach(function(modalEl) {
          new bootstrap.Modal(modalEl);
        });
      }, 100);
    }
  });

  // Improved modal backdrop cleanup: listen for both events and add a delay
  function cleanupModalBackdrop() {
    setTimeout(function() {
      if (document.querySelectorAll('.modal.show').length === 0) {
        document.querySelectorAll('.modal-backdrop').forEach(function(el) {
          el.parentNode.removeChild(el);
        });
        document.body.classList.remove('modal-open');
      }
    }, 100); // 100ms delay to let Bootstrap finish
  }
  document.body.addEventListener('htmx:afterSwap', cleanupModalBackdrop);
  document.body.addEventListener('htmx:afterRequest', cleanupModalBackdrop);
})(); 