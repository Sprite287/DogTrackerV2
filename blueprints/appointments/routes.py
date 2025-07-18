# Standard library imports
from datetime import datetime, timedelta

# Third-party imports
import bleach
from flask import (abort, flash, jsonify, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_required

# Local application imports
from . import appointments_bp
from blueprints.core.audit_helpers import log_audit_event
from blueprints.core.decorators import rescue_access_required, roles_required
from blueprints.core.utils import (check_rescue_access, get_first_user_id,
                                   get_rescue_appointments, htmx_error_response)
from models import Appointment, AppointmentType, Dog, Reminder, db

# --- Dog-specific Appointment CRUD ---

@appointments_bp.route('/dog/<int:dog_id>/appointment/add', methods=['POST'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def add_appointment(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
    print(f"[ADD APPT DEBUG] Form data: {request.form}") # Debug form data

    appt_type_id = request.form.get('appt_type_id')
    appt_start_datetime = request.form.get('appt_start_datetime')
    appt_end_datetime = request.form.get('appt_end_datetime')
    appt_title = request.form.get('appt_title', '').strip()
    appt_notes = request.form.get('appt_notes', '').strip()
    appt_status = request.form.get('appt_status', '').strip()

    # Validation
    if not appt_type_id:
        error_message = 'Appointment type is required.'
        print(f"[ADD APPT DEBUG] Validation Error: {error_message}")
        return htmx_error_response(error_message, '#addAppointmentModalError')
    if not appt_start_datetime:
        error_message = 'Start date/time is required.'
        print(f"[ADD APPT DEBUG] Validation Error: {error_message}")
        return htmx_error_response(error_message, '#addAppointmentModalError')
    if appt_title and len(appt_title) > 100:
        error_message = 'Title must be 100 characters or less.'
        return htmx_error_response(error_message, '#addAppointmentModalError')
    if appt_notes and len(appt_notes) > 2000:
        error_message = 'Notes must be 2000 characters or less.'
        return htmx_error_response(error_message, '#addAppointmentModalError')
    # Sanitize notes
    appt_notes = bleach.clean(appt_notes)

    try:
        start_dt = datetime.strptime(appt_start_datetime, '%Y-%m-%dT%H:%M')
    except ValueError:
        error_message = 'Invalid start date/time format.'
        print(f"[ADD APPT DEBUG] Validation Error: {error_message}")
        return htmx_error_response(error_message, '#addAppointmentModalError')

    end_dt = None
    if appt_end_datetime:
        try:
            end_dt = datetime.strptime(appt_end_datetime, '%Y-%m-%dT%H:%M')
        except ValueError:
            error_message = 'Invalid end date/time format.'
            print(f"[ADD APPT DEBUG] Validation Error: {error_message}") # Corrected this error return
            return htmx_error_response(error_message, '#addAppointmentModalError')
    
    temp_user_id = get_first_user_id()
    if temp_user_id is None:
        flash('Cannot create appointment: No users found in the system.', 'danger')
        return redirect(url_for('dogs.dog_details', dog_id=dog_id))

    appt = Appointment(
        dog_id=dog.id,
        rescue_id=dog.rescue_id,
        type_id=int(appt_type_id) if appt_type_id else None,
        title=appt_title,
        description=appt_notes,
        start_datetime=start_dt,
        end_datetime=end_dt,
        status=appt_status,
        created_by=temp_user_id
    )
    print('Creating appointment:', appt)
    db.session.add(appt)
    db.session.commit()
    # --- AUDIT LOG ---
    log_audit_event(
        user_id=temp_user_id,
        rescue_id=dog.rescue_id,
        action='create',
        resource_type='Appointment',
        resource_id=appt.id,
        details={
            'dog_id': dog.id,
            'type_id': appt.type_id,
            'title': appt.title,
            'start_datetime': appt.start_datetime.isoformat() if appt.start_datetime else None,
            'end_datetime': appt.end_datetime.isoformat() if appt.end_datetime else None,
            'status': appt.status
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )

    # Reminder Generation
    try:
        # Reminder 1: Info about the appointment itself
        reminder_message_info = f"{dog.name}'s appointment for '{appt.title if appt.title else 'Appointment'}' is scheduled on {appt.start_datetime.strftime('%Y-%m-%d at %I:%M %p')}."
        new_reminder_info = Reminder(
            message=reminder_message_info,
            due_datetime=appt.start_datetime, 
            status='pending',
            reminder_type='appointment_info',
            dog_id=dog.id,
            appointment_id=appt.id,
            user_id=temp_user_id
        )
        db.session.add(new_reminder_info)

        # Reminder 2: 24 hours before (if applicable)
        if appt.start_datetime > datetime.utcnow() + timedelta(hours=23): # Give a bit of buffer
            due_24h = appt.start_datetime - timedelta(hours=24)
            reminder_message_24h = f"REMINDER: {dog.name}'s appointment '{appt.title if appt.title else 'Appointment'}' is in 24 hours ({due_24h.strftime('%Y-%m-%d at %I:%M %p')})."
            new_reminder_24h = Reminder(
                message=reminder_message_24h,
                due_datetime=due_24h,
                status='pending',
                reminder_type='appointment_upcoming_24h',
                dog_id=dog.id,
                appointment_id=appt.id,
                user_id=temp_user_id
            )
            db.session.add(new_reminder_24h)

        # Reminder 3: 1 hour before (if applicable)
        if appt.start_datetime > datetime.utcnow() + timedelta(minutes=59): # Give a bit of buffer
            due_1h = appt.start_datetime - timedelta(hours=1)
            reminder_message_1h = f"REMINDER: {dog.name}'s appointment '{appt.title if appt.title else 'Appointment'}' is in 1 hour ({due_1h.strftime('%Y-%m-%d at %I:%M %p')})."
            new_reminder_1h = Reminder(
                message=reminder_message_1h,
                due_datetime=due_1h,
                status='pending',
                reminder_type='appointment_upcoming_1h',
                dog_id=dog.id,
                appointment_id=appt.id,
                user_id=temp_user_id
            )
            db.session.add(new_reminder_1h)
        
        db.session.commit() # Commit new reminders
    except Exception as e:
        db.session.rollback()
        print(f"Error creating reminders: {e}") # Log error, but don't fail the appointment creation

    dog = Dog.query.get_or_404(dog_id)  # Refresh
    appointment_types = AppointmentType.query.filter_by(rescue_id=dog.rescue_id).all()
    return render_template('partials/appointments_list.html', dog=dog, appointment_types=appointment_types, now=datetime.now(), timedelta=timedelta)

@appointments_bp.route('/dog/<int:dog_id>/appointment/edit/<int:appointment_id>', methods=['POST'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def edit_appointment(dog_id, appointment_id):
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
    print('--- Edit Appointment Debug ---')
    print('dog_id:', dog_id)
    print('appointment_id:', appointment_id)
    print('Form data:', dict(request.form))
    
    # Get the appointment directly from the database
    appt = Appointment.query.filter_by(id=appointment_id, dog_id=dog_id).first_or_404()
    
    # Store old start_datetime to check if it changed for reminder regeneration
    old_start_datetime = appt.start_datetime
    appt_type_id = request.form.get('appt_type_id')
    appt_title = request.form.get('appt_title', '').strip()
    appt_notes = request.form.get('appt_notes', '').strip()
    appt_status = request.form.get('appt_status', '').strip()
    appt_start_datetime = request.form.get('appt_start_datetime')
    appt_end_datetime = request.form.get('appt_end_datetime')

    # Validation
    if appt_title and len(appt_title) > 100:
        error_message = 'Title must be 100 characters or less.'
        return htmx_error_response(error_message, f'#editAppointmentModalError-{appointment_id}')
    if appt_notes and len(appt_notes) > 2000:
        error_message = 'Notes must be 2000 characters or less.'
        return htmx_error_response(error_message, f'#editAppointmentModalError-{appointment_id}')
    # Sanitize notes
    appt_notes = bleach.clean(appt_notes)

    appt.type_id = int(appt_type_id) if appt_type_id else None
    appt.title = appt_title
    appt.description = appt_notes
    appt.status = appt_status
    if appt_start_datetime:
        appt.start_datetime = datetime.strptime(appt_start_datetime, '%Y-%m-%dT%H:%M')
    if appt_end_datetime:
        appt.end_datetime = datetime.strptime(appt_end_datetime, '%Y-%m-%dT%H:%M')
    
    temp_user_id = get_first_user_id()
    if temp_user_id is None:
        flash('Cannot update appointment/reminders: No users found.', 'danger')
        return redirect(url_for('dogs.dog_details', dog_id=dog_id))

    db.session.commit()
    print('Updated appointment:', appt)

    # --- AUDIT LOG ---
    log_audit_event(
        user_id=temp_user_id,
        rescue_id=dog.rescue_id,
        action='edit',
        resource_type='Appointment',
        resource_id=appt.id,
        details={
            'dog_id': dog.id,
            'type_id': appt.type_id,
            'title': appt.title,
            'start_datetime': appt.start_datetime.isoformat() if appt.start_datetime else None,
            'end_datetime': appt.end_datetime.isoformat() if appt.end_datetime else None,
            'status': appt.status
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )

    # Reminder Generation/Update Logic
    # Only update reminders if the start time has changed, or perhaps always regenerate for simplicity if other details changed.
    # For now, let's always delete old and create new ones if the critical date changed or for simplicity.
    if appt.start_datetime != old_start_datetime or True: # Condition to always regenerate for now
        try:
            # Delete existing reminders for this appointment
            Reminder.query.filter_by(appointment_id=appt.id).delete()
            # db.session.commit() # Commit deletion - or do it with new additions

            # Reminder 1: Info about the appointment itself
            reminder_message_info = f"{dog.name}'s appointment for '{appt.title if appt.title else 'Appointment'}' is scheduled on {appt.start_datetime.strftime('%Y-%m-%d at %I:%M %p')}."
            new_reminder_info = Reminder(
                message=reminder_message_info,
                due_datetime=appt.start_datetime,
                status='pending',
                reminder_type='appointment_info',
                dog_id=dog.id,
                appointment_id=appt.id,
                user_id=temp_user_id
            )
            db.session.add(new_reminder_info)

            # Reminder 2: 24 hours before (if applicable)
            if appt.start_datetime > datetime.utcnow() + timedelta(hours=23):
                due_24h = appt.start_datetime - timedelta(hours=24)
                reminder_message_24h = f"REMINDER: {dog.name}'s appointment '{appt.title if appt.title else 'Appointment'}' is in 24 hours ({due_24h.strftime('%Y-%m-%d at %I:%M %p')})."
                new_reminder_24h = Reminder(
                    message=reminder_message_24h,
                    due_datetime=due_24h,
                    status='pending',
                    reminder_type='appointment_upcoming_24h',
                    dog_id=dog.id,
                    appointment_id=appt.id,
                    user_id=temp_user_id
                )
                db.session.add(new_reminder_24h)

            # Reminder 3: 1 hour before (if applicable)
            if appt.start_datetime > datetime.utcnow() + timedelta(minutes=59):
                due_1h = appt.start_datetime - timedelta(hours=1)
                reminder_message_1h = f"REMINDER: {dog.name}'s appointment '{appt.title if appt.title else 'Appointment'}' is in 1 hour ({due_1h.strftime('%Y-%m-%d at %I:%M %p')})."
                new_reminder_1h = Reminder(
                    message=reminder_message_1h,
                    due_datetime=due_1h,
                    status='pending',
                    reminder_type='appointment_upcoming_1h',
                    dog_id=dog.id,
                    appointment_id=appt.id,
                    user_id=temp_user_id
                )
                db.session.add(new_reminder_1h)

            db.session.commit() # Commit deletions and new reminders
        except Exception as e:
            db.session.rollback()
            print(f"Error updating/creating reminders for edited appointment: {e}")

    dog = Dog.query.get_or_404(dog_id)  # Refresh
    print('All appointments for dog:', dog_id)
    for a in dog.appointments:
        print(f'  id={a.id}, title={a.title}, start={a.start_datetime}')
    appointment_types = AppointmentType.query.filter_by(rescue_id=dog.rescue_id).all()
    return render_template('partials/appointments_list.html', dog=dog, appointment_types=appointment_types, now=datetime.now(), timedelta=timedelta)

@appointments_bp.route('/dog/<int:dog_id>/appointment/delete/<int:appointment_id>', methods=['POST'])
@login_required
def delete_appointment(dog_id, appointment_id):
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
    appt = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appt)
    db.session.commit()
    # --- AUDIT LOG ---
    temp_user_id = get_first_user_id()
    log_audit_event(
        user_id=temp_user_id,
        rescue_id=dog.rescue_id,
        action='delete',
        resource_type='Appointment',
        resource_id=appt.id,
        details={
            'dog_id': dog.id,
            'type_id': appt.type_id,
            'title': appt.title,
            'start_datetime': appt.start_datetime.isoformat() if appt.start_datetime else None,
            'end_datetime': appt.end_datetime.isoformat() if appt.end_datetime else None,
            'status': appt.status
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    dog = Dog.query.get_or_404(dog_id)  # Refresh
    appointment_types = AppointmentType.query.filter_by(rescue_id=dog.rescue_id).all()
    return render_template('partials/appointments_list.html', dog=dog, appointment_types=appointment_types, now=datetime.now(), timedelta=timedelta)

@appointments_bp.route('/dog/<int:dog_id>/appointment/complete/<int:appointment_id>', methods=['POST'])
@login_required
def complete_appointment(dog_id, appointment_id):
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
    
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.dog_id != dog_id:
        abort(404)
    
    # Update appointment status to completed
    appt.status = 'completed'
    db.session.commit()
    
    # --- AUDIT LOG ---
    temp_user_id = get_first_user_id()
    log_audit_event(
        user_id=temp_user_id,
        rescue_id=dog.rescue_id,
        action='complete',
        resource_type='Appointment',
        resource_id=appt.id,
        details={
            'dog_id': dog.id,
            'type_id': appt.type_id,
            'title': appt.title,
            'previous_status': appt.status,
            'new_status': 'completed'
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    
    # Mark any related reminders as acknowledged
    related_reminders = Reminder.query.filter_by(appointment_id=appointment_id, status='pending').all()
    for reminder in related_reminders:
        reminder.status = 'acknowledged'
    db.session.commit()
    
    dog = Dog.query.get_or_404(dog_id)  # Refresh
    appointment_types = AppointmentType.query.filter_by(rescue_id=dog.rescue_id).all()
    return render_template('partials/appointments_list.html', dog=dog, appointment_types=appointment_types, now=datetime.now(), timedelta=timedelta)

# --- Appointment List and Details ---

@appointments_bp.route('/appointments')
@roles_required(['staff', 'admin', 'owner', 'superadmin'])
@login_required
def appointment_list():
    appointments = get_rescue_appointments().all() if current_user.role != 'superadmin' else Appointment.query.all()
    # Note: appointments.html template does not exist yet
    # TODO: Create appointments list template
    # For now, return a simple response
    return jsonify({'message': 'Appointments list view not yet implemented', 'count': len(appointments)})

@appointments_bp.route('/appointment/<int:appointment_id>')
@rescue_access_required(lambda kwargs: Appointment.query.get(kwargs['appointment_id']).rescue_id)
@login_required
def appointment_details(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    check_rescue_access(appointment)
    # Note: appointment_details.html template does not exist yet
    # TODO: Create appointment details template
    # For now, return appointment data as JSON
    return jsonify({
        'id': appointment.id,
        'dog_id': appointment.dog_id,
        'type_id': appointment.type_id,
        'title': appointment.title,
        'description': appointment.description,
        'start_datetime': appointment.start_datetime.isoformat() if appointment.start_datetime else None,
        'end_datetime': appointment.end_datetime.isoformat() if appointment.end_datetime else None,
        'status': appointment.status
    })

# --- API Routes ---

@appointments_bp.route('/api/appointment/<int:appointment_id>')
def api_get_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    return jsonify({
        'id': appt.id,
        'type_id': appt.type_id,
        'title': appt.title,
        'description': appt.description,
        'start_datetime': appt.start_datetime.isoformat() if appt.start_datetime else '',
        'end_datetime': appt.end_datetime.isoformat() if appt.end_datetime else '',
        'status': appt.status
    })