from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, abort, make_response
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import bleach
import json

from blueprints.core.decorators import roles_required
from blueprints.core.audit_helpers import log_audit_event
from models import db, MedicinePreset, RescueMedicineActivation, Rescue, Dog, DogMedicine, Reminder
from blueprints.core.utils import get_first_user_id, parse_medicine_frequency, generate_daily_medicine_reminders

medicines_bp = Blueprint('medicines', __name__, url_prefix='')

# Phase R4C-1: Medicine Preset Management Routes

@medicines_bp.route('/rescue/medicines/manage')
@roles_required(['admin', 'owner', 'superadmin'])
@login_required
def manage_rescue_medicines():
    # Get all global presets
    global_presets = MedicinePreset.query.filter(MedicinePreset.rescue_id == None).order_by(MedicinePreset.category, MedicinePreset.name).all()
    # Get all rescue-specific presets for this rescue
    rescue_presets = MedicinePreset.query.filter(MedicinePreset.rescue_id == current_user.rescue_id).order_by(MedicinePreset.category, MedicinePreset.name).all()
    # Get all activations for this rescue
    activations = RescueMedicineActivation.query.filter_by(rescue_id=current_user.rescue_id, is_active=True).all()
    active_global_ids = {a.medicine_preset_id for a in activations}
    return render_template('manage_rescue_medicines.html',
        global_presets=global_presets,
        rescue_presets=rescue_presets,
        active_global_ids=active_global_ids
    )

@medicines_bp.route('/rescue/medicines/toggle_activation', methods=['POST'])
@roles_required(['admin', 'owner'])
@login_required
def toggle_medicine_activation():
    if not current_user.rescue_id:
        abort(403)
    preset_id = request.form.get('preset_id', type=int)
    activate = request.form.get('activate', type=str) == 'true'
    if not preset_id:
        return jsonify({'success': False, 'error': 'Missing preset_id'}), 400
    preset = MedicinePreset.query.get_or_404(preset_id)
    # Only allow toggling global or own rescue's presets
    if not (preset.rescue_id is None or preset.rescue_id == current_user.rescue_id):
        abort(403)
    activation = RescueMedicineActivation.query.filter_by(rescue_id=current_user.rescue_id, medicine_preset_id=preset_id).first()
    action = None
    if not activate:
        if not activation:
            activation = RescueMedicineActivation(rescue_id=current_user.rescue_id, medicine_preset_id=preset_id, is_active=False)
            db.session.add(activation)
        else:
            activation.is_active = False
        action = 'deactivate_preset'
    else:
        if activation:
            db.session.delete(activation)
        action = 'activate_preset'
    db.session.commit()
    # Audit log
    rescue = Rescue.query.get(current_user.rescue_id)
    log_audit_event(
        user_id=current_user.id,
        rescue_id=current_user.rescue_id,
        action=action,
        resource_type='MedicinePreset',
        resource_id=preset_id,
        details={
            'preset_name': preset.name,
            'preset_category': preset.category,
            'rescue_name': rescue.name if rescue else None,
            'activated': activate
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    return jsonify({'success': True, 'active': activate})

@medicines_bp.route('/rescue/medicines/add', methods=['GET', 'POST'])
@roles_required(['admin', 'owner', 'superadmin'])
@login_required
def add_rescue_medicine_preset():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        default_dosage_instructions = request.form.get('default_dosage_instructions', '').strip()
        suggested_units = request.form.get('suggested_units', '').strip()
        default_unit = request.form.get('default_unit', '').strip()
        notes = request.form.get('notes', '').strip()

        # Validation
        if not name:
            flash('Name is required.', 'danger')
            return redirect(url_for('medicines.add_rescue_medicine_preset'))
        if len(name) > 120:
            flash('Name must be 120 characters or less.', 'danger')
            return redirect(url_for('medicines.add_rescue_medicine_preset'))
        if category and len(category) > 100:
            flash('Category must be 100 characters or less.', 'danger')
            return redirect(url_for('medicines.add_rescue_medicine_preset'))
        if suggested_units and len(suggested_units) > 255:
            flash('Suggested units must be 255 characters or less.', 'danger')
            return redirect(url_for('medicines.add_rescue_medicine_preset'))
        if default_unit and len(default_unit) > 20:
            flash('Default unit must be 20 characters or less.', 'danger')
            return redirect(url_for('medicines.add_rescue_medicine_preset'))
        if notes and len(notes) > 2000:
            flash('Notes must be 2000 characters or less.', 'danger')
            return redirect(url_for('medicines.add_rescue_medicine_preset'))
        if default_dosage_instructions and len(default_dosage_instructions) > 2000:
            flash('Dosage instructions must be 2000 characters or less.', 'danger')
            return redirect(url_for('medicines.add_rescue_medicine_preset'))
        # Sanitize notes and instructions
        notes = bleach.clean(notes)
        default_dosage_instructions = bleach.clean(default_dosage_instructions)

        # Validate rescue_id for superadmins
        rescue_id = current_user.rescue_id if current_user.role != 'superadmin' else request.form.get('rescue_id')
        if current_user.role == 'superadmin' and not rescue_id:
            flash('Please select a rescue for this medicine preset.', 'danger')
            return redirect(url_for('medicines.add_rescue_medicine_preset'))

        preset = MedicinePreset(
            rescue_id=rescue_id,
            name=name,
            category=category,
            default_dosage_instructions=default_dosage_instructions,
            suggested_units=suggested_units,
            default_unit=default_unit,
            notes=notes
        )
        db.session.add(preset)
        db.session.commit()
        # Activate for this rescue
        activation = RescueMedicineActivation(rescue_id=rescue_id, medicine_preset_id=preset.id, is_active=True)
        db.session.add(activation)
        db.session.commit()
        flash('Preset created and activated!', 'success')
        return redirect(url_for('medicines.manage_rescue_medicines'))
    
    # For GET requests, pass rescues data if superadmin
    if current_user.role == 'superadmin':
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        return render_template('add_edit_rescue_medicine_preset.html', preset=None, rescues=rescues)
    else:
        return render_template('add_edit_rescue_medicine_preset.html', preset=None)

@medicines_bp.route('/rescue/medicines/edit/<int:preset_id>', methods=['GET', 'POST'])
@roles_required(['admin', 'owner', 'superadmin'])
@login_required
def edit_rescue_medicine_preset(preset_id):
    preset = MedicinePreset.query.get_or_404(preset_id)
    if not (current_user.role == 'superadmin' or (preset.rescue_id == current_user.rescue_id and preset.rescue_id is not None)):
        abort(403)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        default_dosage_instructions = request.form.get('default_dosage_instructions', '').strip()
        suggested_units = request.form.get('suggested_units', '').strip()
        default_unit = request.form.get('default_unit', '').strip()
        notes = request.form.get('notes', '').strip()
        # Validation
        if not name:
            flash('Name is required.', 'danger')
            return redirect(url_for('medicines.edit_rescue_medicine_preset', preset_id=preset_id))
        if len(name) > 120:
            flash('Name must be 120 characters or less.', 'danger')
            return redirect(url_for('medicines.edit_rescue_medicine_preset', preset_id=preset_id))
        if category and len(category) > 100:
            flash('Category must be 100 characters or less.', 'danger')
            return redirect(url_for('medicines.edit_rescue_medicine_preset', preset_id=preset_id))
        if suggested_units and len(suggested_units) > 255:
            flash('Suggested units must be 255 characters or less.', 'danger')
            return redirect(url_for('medicines.edit_rescue_medicine_preset', preset_id=preset_id))
        if default_unit and len(default_unit) > 20:
            flash('Default unit must be 20 characters or less.', 'danger')
            return redirect(url_for('medicines.edit_rescue_medicine_preset', preset_id=preset_id))
        if notes and len(notes) > 2000:
            flash('Notes must be 2000 characters or less.', 'danger')
            return redirect(url_for('medicines.edit_rescue_medicine_preset', preset_id=preset_id))
        if default_dosage_instructions and len(default_dosage_instructions) > 2000:
            flash('Dosage instructions must be 2000 characters or less.', 'danger')
            return redirect(url_for('medicines.edit_rescue_medicine_preset', preset_id=preset_id))
        # Sanitize notes and instructions
        notes = bleach.clean(notes)
        default_dosage_instructions = bleach.clean(default_dosage_instructions)
        preset.name = name
        preset.category = category
        preset.default_dosage_instructions = default_dosage_instructions
        preset.suggested_units = suggested_units
        preset.default_unit = default_unit
        preset.notes = notes
        db.session.commit()
        flash('Preset updated!', 'success')
        return redirect(url_for('medicines.manage_rescue_medicines'))
    return render_template('add_edit_rescue_medicine_preset.html', preset=preset)

@medicines_bp.route('/rescue/medicines/delete/<int:preset_id>', methods=['POST'])
@roles_required(['admin', 'owner', 'superadmin'])
@login_required
def delete_rescue_medicine_preset(preset_id):
    preset = MedicinePreset.query.get_or_404(preset_id)
    if not (current_user.role == 'superadmin' or (preset.rescue_id == current_user.rescue_id and preset.rescue_id is not None)):
        abort(403)
    # Deactivate before delete
    RescueMedicineActivation.query.filter_by(rescue_id=current_user.rescue_id, medicine_preset_id=preset_id).delete()
    db.session.delete(preset)
    db.session.commit()
    flash('Preset deleted!', 'success')
    return redirect(url_for('medicines.manage_rescue_medicines'))

# Phase R4C-2: Dog Medicine Assignment Routes

@medicines_bp.route('/dog/<int:dog_id>/medicine/add', methods=['POST'])
@login_required
def add_medicine(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    if current_user.role != 'superadmin' and dog.rescue_id != current_user.rescue_id:
        abort(403)
    med_preset_id_str = request.form.get('med_preset_id')
    med_dosage = request.form.get('med_dosage', '').strip()
    med_unit = request.form.get('med_unit', '').strip()
    med_form = request.form.get('med_form', '').strip()
    med_frequency = request.form.get('med_frequency', '').strip()
    med_start_date_str = request.form.get('med_start_date')
    med_end_date_str = request.form.get('med_end_date')
    med_status = request.form.get('med_status', '').strip()
    med_notes = request.form.get('med_notes', '').strip()

    error_message = None
    start_date = None
    end_date = None

    # Validation
    if med_dosage and len(med_dosage) > 50:
        error_message = 'Dosage must be 50 characters or less.'
    elif med_unit and len(med_unit) > 50:
        error_message = 'Unit must be 50 characters or less.'
    elif med_frequency and len(med_frequency) > 100:
        error_message = 'Frequency must be 100 characters or less.'
    elif med_notes and len(med_notes) > 2000:
        error_message = 'Notes must be 2000 characters or less.'

    if not error_message and not med_start_date_str:
        error_message = 'Start Date is required.'
    else:
        try:
            start_date = datetime.strptime(med_start_date_str, '%Y-%m-%d').date()
        except ValueError:
            error_message = 'Invalid start date format.'
    if not error_message and med_end_date_str:
        try:
            end_date = datetime.strptime(med_end_date_str, '%Y-%m-%d').date()
        except ValueError:
            error_message = 'Invalid end date format.'
    if not error_message and not med_preset_id_str:
        error_message = 'Medicine preset is required.'
    if not error_message and not med_dosage:
        error_message = 'Dosage is required.'
    if not error_message and not med_unit:
        error_message = 'Unit is required.'
    if not error_message and not med_frequency:
        error_message = 'Frequency is required.'
    if not error_message and not med_status:
        error_message = 'Status is required.'

    if error_message:
        response = make_response(render_template('partials/modal_form_error.html', message=error_message))
        response.status_code = 200
        response.headers['HX-Retarget'] = '#addMedicineModalError'
        response.headers['HX-Reswap'] = 'innerHTML'
        return response

    # Sanitize notes
    med_notes = bleach.clean(med_notes)

    temp_user_id = get_first_user_id()
    if temp_user_id is None:
        flash('Cannot add medicine: No users found in the system.', 'danger')
        if request.headers.get('HX-Request'):
            alert_resp = make_response('')
            alert_resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Cannot add medicine: No users found.", "category": "danger"}})
            return alert_resp, 200
        return redirect(url_for('dogs.dog_details', dog_id=dog_id))

    final_preset_id = None
    try:
        final_preset_id = int(med_preset_id_str)
    except ValueError:
        error_message = 'Invalid Medicine Preset ID.' 
        response = make_response(render_template('partials/modal_form_error.html', message=error_message))
        response.status_code = 200
        response.headers['HX-Retarget'] = '#addMedicineModalError'
        response.headers['HX-Reswap'] = 'innerHTML'
        return response

    med = DogMedicine(
        dog_id=dog.id,
        rescue_id=dog.rescue_id,
        medicine_id=final_preset_id,
        custom_name=None,
        dosage=med_dosage,
        unit=med_unit,
        form=med_form,
        frequency=med_frequency,
        start_date=start_date,
        end_date=end_date,
        status=med_status,
        notes=med_notes,
        created_by=temp_user_id
    )
    db.session.add(med)
    db.session.commit()
    # --- AUDIT LOG ---
    log_audit_event(
        user_id=temp_user_id,
        rescue_id=dog.rescue_id,
        action='create',
        resource_type='DogMedicine',
        resource_id=med.id,
        details={
            'dog_id': dog.id,
            'medicine_id': med.medicine_id,
            'custom_name': med.custom_name,
            'dosage': med.dosage,
            'unit': med.unit,
            'form': med.form,
            'frequency': med.frequency,
            'start_date': str(med.start_date) if med.start_date else None,
            'end_date': str(med.end_date) if med.end_date else None,
            'status': med.status
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )

    # Phase R4C-3: Enhanced Reminder Generation with Frequency Interpretation
    if med.start_date:
        try:
            # Create start date reminder (one-time)
            reminder_due_dt = datetime.combine(med.start_date, datetime.min.time()) + timedelta(hours=9)
            
            medicine_name = med.custom_name
            if not medicine_name and med.medicine_id:
                preset = MedicinePreset.query.get(med.medicine_id)
                if preset:
                    medicine_name = preset.name
            if not medicine_name:
                medicine_name = "Medicine"

            # Parse frequency for display
            frequency_data = parse_medicine_frequency(med.frequency)
            
            start_reminder_message = f"{dog.name}'s prescription for '{medicine_name}' is scheduled to start on {med.start_date.strftime('%Y-%m-%d')} - {frequency_data['display_name']}."
            
            start_reminder = Reminder(
                message=start_reminder_message,
                due_datetime=reminder_due_dt,
                status='pending',
                reminder_type='medicine_start',
                dog_id=dog.id,
                dog_medicine_id=med.id,
                user_id=temp_user_id
            )
            db.session.add(start_reminder)
            
            # Generate daily recurring reminders based on frequency
            daily_reminders = generate_daily_medicine_reminders(med, temp_user_id)
            for daily_reminder in daily_reminders:
                db.session.add(daily_reminder)
            
            db.session.commit()
            
            print(f"Created {len(daily_reminders) + 1} reminders for medicine: 1 start + {len(daily_reminders)} daily")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating reminders for medicine: {e}")

    dog = Dog.query.get_or_404(dog_id)
    medicine_presets_data = MedicinePreset.query.filter(
        (MedicinePreset.rescue_id == dog.rescue_id) | (MedicinePreset.rescue_id == None)
    ).all()
    return render_template('partials/medicines_list.html', dog=dog, medicine_presets=medicine_presets_data)

@medicines_bp.route('/dog/<int:dog_id>/medicine/edit/<int:medicine_id>', methods=['POST'])
@login_required
def edit_medicine(dog_id, medicine_id):
    print('--- Edit Medicine Debug ---')
    print('dog_id:', dog_id)
    print('medicine_id:', medicine_id)
    print('Form data:', dict(request.form))
    
    dog = Dog.query.get_or_404(dog_id)
    if current_user.role != 'superadmin' and dog.rescue_id != current_user.rescue_id:
        abort(403)
    med = DogMedicine.query.get_or_404(medicine_id)
    if current_user.role != 'superadmin' and med.rescue_id != current_user.rescue_id:
        abort(403)

    old_start_date = med.start_date

    # Get data from form
    med_preset_id_str = request.form.get('med_preset_id')
    med_dosage = request.form.get('med_dosage', '').strip()
    med_unit = request.form.get('med_unit', '').strip()
    med_form = request.form.get('med_form', '').strip()
    med_frequency = request.form.get('med_frequency', '').strip()
    med_start_date_str = request.form.get('med_start_date')
    med_end_date_str = request.form.get('med_end_date')
    med_status = request.form.get('med_status', '').strip()
    med_notes = request.form.get('med_notes', '').strip()

    error_message = None
    start_date = None
    end_date = None

    # Validation
    print('Starting validation...')
    print(f'med_preset_id_str: "{med_preset_id_str}"')
    print(f'med_dosage: "{med_dosage}"')
    print(f'med_unit: "{med_unit}"')
    print(f'med_frequency: "{med_frequency}"')
    print(f'med_status: "{med_status}"')
    if med_dosage and len(med_dosage) > 50:
        error_message = 'Dosage must be 50 characters or less.'
    elif med_unit and len(med_unit) > 50:
        error_message = 'Unit must be 50 characters or less.'
    elif med_frequency and len(med_frequency) > 100:
        error_message = 'Frequency must be 100 characters or less.'
    elif med_notes and len(med_notes) > 2000:
        error_message = 'Notes must be 2000 characters or less.'

    if not error_message and not med_start_date_str:
        error_message = 'Start Date is required.'
    else:
        try:
            start_date = datetime.strptime(med_start_date_str, '%Y-%m-%d').date()
        except ValueError:
            error_message = 'Invalid start date format.'
    if not error_message and med_end_date_str:
        try:
            end_date = datetime.strptime(med_end_date_str, '%Y-%m-%d').date()
        except ValueError:
            error_message = 'Invalid end date format.'
    if not error_message and not med_preset_id_str:
        error_message = 'Medicine preset is required.'
    if not error_message and not med_dosage:
        error_message = 'Dosage is required.'
    if not error_message and not med_unit:
        error_message = 'Unit is required.'
    if not error_message and not med_frequency:
        error_message = 'Frequency is required.'
    if not error_message and not med_status:
        error_message = 'Status is required.'

    if error_message:
        print(f'Validation failed: {error_message}')
        response = make_response(render_template('partials/modal_form_error.html', message=error_message))
        response.status_code = 200 # Keep 200 for HTMX to process swap
        response.headers['HX-Retarget'] = '#editMedicineModalError'
        response.headers['HX-Reswap'] = 'innerHTML'
        return response

    # Sanitize notes
    med_notes = bleach.clean(med_notes)

    temp_user_id = get_first_user_id()
    if temp_user_id is None:
        flash('Cannot edit medicine: No users found in the system.', 'danger')
        return redirect(url_for('dogs.dog_details', dog_id=dog_id))

    # Update medicine object properties
    med.medicine_id = int(med_preset_id_str) if med_preset_id_str else None
    med.custom_name = None
    med.dosage = med_dosage
    med.unit = med_unit
    med.form = med_form
    med.frequency = med_frequency
    med.start_date = start_date
    med.end_date = end_date
    med.status = med_status
    med.notes = med_notes
    print('Medicine updated successfully, committing to database...')
    db.session.commit()
    print('Database commit successful')
    # --- AUDIT LOG ---
    log_audit_event(
        user_id=temp_user_id,
        rescue_id=dog.rescue_id,
        action='edit',
        resource_type='DogMedicine',
        resource_id=med.id,
        details={
            'dog_id': dog.id,
            'medicine_id': med.medicine_id,
            'custom_name': med.custom_name,
            'dosage': med.dosage,
            'unit': med.unit,
            'form': med.form,
            'frequency': med.frequency,
            'start_date': str(med.start_date) if med.start_date else None,
            'end_date': str(med.end_date) if med.end_date else None,
            'status': med.status
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )

    # Phase R4C-3: Enhanced Reminder Generation/Update Logic with Frequency Interpretation
    # Regenerate if start_date changed or for simplicity, always (current condition `or True`)
    if med.start_date and (med.start_date != old_start_date or True):
        try:
            # Delete existing reminders for this medicine instance
            Reminder.query.filter_by(dog_medicine_id=med.id).delete()

            # Create new start date reminder
            reminder_due_dt = datetime.combine(med.start_date, datetime.min.time()) + timedelta(hours=9)
            
            medicine_name = med.custom_name # Will be None if preset was chosen above
            if not medicine_name and med.medicine_id:
                preset = MedicinePreset.query.get(med.medicine_id)
                if preset:
                    medicine_name = preset.name
            if not medicine_name: # Fallback if still no name
                medicine_name = "Medicine"

            # Parse frequency for display
            frequency_data = parse_medicine_frequency(med.frequency)
            
            start_reminder_message = f"{dog.name}'s prescription for '{medicine_name}' is scheduled to start on {med.start_date.strftime('%Y-%m-%d')} - {frequency_data['display_name']}."
            
            updated_start_reminder = Reminder(
                message=start_reminder_message,
                due_datetime=reminder_due_dt,
                status='pending',
                reminder_type='medicine_start',
                dog_id=dog.id,
                dog_medicine_id=med.id,
                user_id=temp_user_id
            )
            db.session.add(updated_start_reminder)
            
            # Generate daily recurring reminders based on frequency
            daily_reminders = generate_daily_medicine_reminders(med, temp_user_id)
            for daily_reminder in daily_reminders:
                db.session.add(daily_reminder)
            
            db.session.commit() # Commit reminder changes
            
            print(f"Updated reminders for medicine: 1 start + {len(daily_reminders)} daily")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating/creating reminders for edited medicine: {e}")

    dog = Dog.query.get_or_404(dog_id)
    medicine_presets_data = MedicinePreset.query.filter(
        (MedicinePreset.rescue_id == dog.rescue_id) | (MedicinePreset.rescue_id == None)
    ).all()
    print('Returning medicines_list.html template...')
    print(f'Dog has {len(dog.medicines)} medicines')
    for med_item in dog.medicines:
        print(f'  Medicine ID: {med_item.id}, Dosage: {med_item.dosage}, Status: {med_item.status}')
    return render_template('partials/medicines_list.html', dog=dog, medicine_presets=medicine_presets_data)

@medicines_bp.route('/dog/<int:dog_id>/medicine/delete/<int:medicine_id>', methods=['POST'])
@login_required
def delete_medicine(dog_id, medicine_id):
    dog = Dog.query.get_or_404(dog_id)
    if current_user.role != 'superadmin' and dog.rescue_id != current_user.rescue_id:
        abort(403)
    med = DogMedicine.query.get_or_404(medicine_id)
    if current_user.role != 'superadmin' and med.rescue_id != current_user.rescue_id:
        abort(403)
    db.session.delete(med)
    db.session.commit()
    # --- AUDIT LOG ---
    temp_user_id = get_first_user_id()
    log_audit_event(
        user_id=temp_user_id,
        rescue_id=dog.rescue_id,
        action='delete',
        resource_type='DogMedicine',
        resource_id=med.id,
        details={
            'dog_id': dog.id,
            'medicine_id': med.medicine_id,
            'custom_name': med.custom_name,
            'dosage': med.dosage,
            'unit': med.unit,
            'form': med.form,
            'frequency': med.frequency,
            'start_date': str(med.start_date) if med.start_date else None,
            'end_date': str(med.end_date) if med.end_date else None,
            'status': med.status
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    dog = Dog.query.get_or_404(dog_id)  # Refresh
    medicine_presets_data = MedicinePreset.query.filter(
        (MedicinePreset.rescue_id == dog.rescue_id) | (MedicinePreset.rescue_id == None)
    ).all()
    return render_template('partials/medicines_list.html', dog=dog, medicine_presets=medicine_presets_data)

@medicines_bp.route('/api/medicine/<int:medicine_id>')
def api_get_medicine(medicine_id):
    med = DogMedicine.query.get_or_404(medicine_id)
    print(f'API: Medicine {medicine_id} frequency: "{med.frequency}"')
    return jsonify({
        'id': med.id,
        'medicine_id': med.medicine_id,
        'dosage': med.dosage,
        'unit': med.unit,
        'form': med.form,
        'frequency': med.frequency,
        'start_date': med.start_date.isoformat() if med.start_date else '',
        'end_date': med.end_date.isoformat() if med.end_date else '',
        'status': med.status,
        'notes': med.notes
    })