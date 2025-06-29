from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from collections import defaultdict
from datetime import datetime, timedelta
from blueprints.core.decorators import rescue_access_required
from models import Reminder, Rescue, Appointment, DogMedicine, Dog, AppointmentType
from blueprints.core.utils import get_rescue_reminders, check_rescue_access, get_effective_rescue_id, filter_by_rescue, get_filtered_reminders

calendar_bp = Blueprint('calendar', __name__, url_prefix='')

@calendar_bp.route('/reminder/<int:reminder_id>/acknowledge', methods=['POST'])
@rescue_access_required(lambda kwargs: Reminder.query.get(kwargs['reminder_id']).dog.rescue_id if Reminder.query.get(kwargs['reminder_id']).dog else None)
@login_required
def acknowledge_reminder(reminder_id):
    from app import db
    reminder = Reminder.query.get_or_404(reminder_id)
    reminder.status = 'acknowledged'
    db.session.commit()
    return '', 200

@calendar_bp.route('/calendar/acknowledge_reminder/<int:reminder_id>', methods=['POST'])
@rescue_access_required(lambda kwargs: Reminder.query.get(kwargs['reminder_id']).dog.rescue_id if Reminder.query.get(kwargs['reminder_id']).dog else None)
@login_required
def calendar_acknowledge_reminder(reminder_id):
    from app import db
    reminder = Reminder.query.get_or_404(reminder_id)
    reminder.status = 'acknowledged'
    db.session.commit()
    return '', 200

@calendar_bp.route('/reminder/<int:reminder_id>/dismiss', methods=['POST'])
@rescue_access_required(lambda kwargs: Reminder.query.get(kwargs['reminder_id']).dog.rescue_id if Reminder.query.get(kwargs['reminder_id']).dog else None)
@login_required
def dismiss_reminder(reminder_id):
    from app import db
    reminder = Reminder.query.get_or_404(reminder_id)
    reminder.status = 'dismissed'
    db.session.commit()
    return '', 200

@calendar_bp.route('/calendar')
@login_required
def calendar_view():
    rescue_id = request.args.get('rescue_id', type=int)
    effective_rescue_id = get_effective_rescue_id(rescue_id)
    
    # Get rescues for dropdown (only for superadmin)
    rescues = Rescue.query.order_by(Rescue.name.asc()).all() if current_user.role == 'superadmin' else None
    
    # Get reminders based on effective rescue_id
    base_query = Reminder.query.filter(Reminder.status == 'pending')
    reminders_query = filter_by_rescue(base_query, Reminder, rescue_id).order_by(Reminder.due_datetime.asc()).all()
    
    group_order = ["Vet Reminders", "Medication Reminders", "Other Reminders"]
    grouped_reminders = defaultdict(list)
    for group in group_order:
        grouped_reminders[group] = []
    
    for reminder in reminders_query:
        group_name = "Other Reminders"
        specific_type_name_for_grouping = None
        if reminder.appointment_id and reminder.appointment:
            if reminder.appointment.type:
                specific_type_name_for_grouping = reminder.appointment.type.name
                if "vet" in specific_type_name_for_grouping.lower():
                    group_name = "Vet Reminders"
                elif "grooming" in specific_type_name_for_grouping.lower():
                    group_name = "Grooming Reminders"
            # else falls to Other Reminders
        elif reminder.dog_medicine_id:
            group_name = "Medication Reminders"
        grouped_reminders[group_name].append(reminder)
    
    ordered_final_groups = {group: grouped_reminders[group] for group in group_order if group in grouped_reminders}
    other_dynamic_groups = {k: v for k, v in sorted(grouped_reminders.items()) if k not in ordered_final_groups and v}
    ordered_final_groups.update(other_dynamic_groups)
    
    # Calculate calendar stats
    today = datetime.now()
    today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
    week_from_today = today + timedelta(days=7)
    
    # Get appointment counts
    appointments_today_query = Appointment.query.filter(
        Appointment.start_datetime >= today_start,
        Appointment.start_datetime <= today_end
    )
    appointments_week_query = Appointment.query.filter(
        Appointment.start_datetime >= today_start,
        Appointment.start_datetime <= week_from_today
    )
    
    appointments_today = filter_by_rescue(appointments_today_query, Appointment, rescue_id).count()
    appointments_week = filter_by_rescue(appointments_week_query, Appointment, rescue_id).count()
    
    # Get active medicines count for today
    medicines_query = DogMedicine.query.filter(DogMedicine.status == 'active')
    medicines_today = filter_by_rescue(medicines_query, DogMedicine, rescue_id).count()
    
    # Count active reminders
    active_reminders = len(reminders_query)
    
    # For the filter counts, we need total counts (not just today/this week)
    total_appointments = filter_by_rescue(Appointment.query, Appointment, rescue_id).count()
    total_medicines = filter_by_rescue(
        DogMedicine.query.filter(DogMedicine.status == 'active'), 
        DogMedicine, 
        rescue_id
    ).count()
    
    calendar_stats = {
        'today_count': appointments_today + medicines_today,
        'week_count': appointments_week + medicines_today,  # medicines are ongoing
        'medications_today': medicines_today,
        'appointments_week': appointments_week,
        'active_reminders': active_reminders,
        'total_events': total_appointments + total_medicines + active_reminders,
        'medications_count': total_medicines,
        'appointments_count': total_appointments,
        'monitoring_count': 0  # Placeholder for now
    }
    
    # Calculate adherence stats (placeholder for now)
    stats = {
        'given_on_time': 0,
        'given_late': 0,
        'missed': 0
    }
    
    # Calculate adherence rate
    total_doses = stats['given_on_time'] + stats['given_late'] + stats['missed']
    adherence_rate = 100 if total_doses == 0 else int((stats['given_on_time'] / total_doses) * 100)
    
    # Get dogs and appointment types for the modal
    dogs = filter_by_rescue(Dog.query, Dog, rescue_id).order_by(Dog.name).all()
    
    appointment_types = AppointmentType.query.order_by(AppointmentType.name).all()
    
    return render_template('calendar_view.html', 
                         grouped_reminders=ordered_final_groups, 
                         rescues=rescues, 
                         selected_rescue_id=effective_rescue_id,
                         calendar_stats=calendar_stats,
                         current_date=today,
                         now=datetime.now(),
                         timedelta=timedelta,
                         stats=stats,
                         adherence_rate=adherence_rate,
                         dogs=dogs,
                         appointment_types=appointment_types)

@calendar_bp.route('/calendar/reminders/overdue')
@login_required
def get_overdue_reminders():
    rescue_id = request.args.get('rescue_id', type=int)
    offset = request.args.get('offset', type=int, default=0)
    limit = request.args.get('limit', type=int, default=None)
    
    # Use the helper function to get filtered reminders
    reminders_query = get_filtered_reminders('overdue', rescue_id=rescue_id, offset=offset, limit=limit)
    reminders_list = reminders_query.all()
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        return render_template('partials/reminder_list_items.html',
                             reminders=reminders_list,
                             reminder_type='overdue',
                             now=datetime.now())
    
    # Return JSON for non-HTMX requests
    return jsonify({'reminders': len(reminders_list)})

@calendar_bp.route('/calendar/reminders/today')
@login_required
def get_today_reminders():
    rescue_id = request.args.get('rescue_id', type=int)
    offset = request.args.get('offset', type=int, default=0)
    limit = request.args.get('limit', type=int, default=None)
    
    # Use the helper function to get filtered reminders
    reminders_query = get_filtered_reminders('today', rescue_id=rescue_id, offset=offset, limit=limit)
    reminders_list = reminders_query.all()
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        return render_template('partials/reminder_list_items.html',
                             reminders=reminders_list,
                             reminder_type='today',
                             now=datetime.now())
    
    # Return JSON for non-HTMX requests
    return jsonify({'reminders': len(reminders_list)})

@calendar_bp.route('/calendar/reminders/upcoming')
@login_required
def get_upcoming_reminders():
    rescue_id = request.args.get('rescue_id', type=int)
    offset = request.args.get('offset', type=int, default=0)
    limit = request.args.get('limit', type=int, default=None)
    
    # Use the helper function to get filtered reminders
    reminders_query = get_filtered_reminders('upcoming', rescue_id=rescue_id, offset=offset, limit=limit)
    reminders_list = reminders_query.all()
    
    # Check if this is an HTMX request
    if request.headers.get('HX-Request'):
        return render_template('partials/reminder_list_items.html',
                             reminders=reminders_list,
                             reminder_type='upcoming',
                             now=datetime.now())
    
    # Return JSON for non-HTMX requests
    return jsonify({'reminders': len(reminders_list)})

@calendar_bp.route('/calendar/add-appointment', methods=['POST'])
@login_required
def add_appointment():
    from app import db
    
    # Get form data
    dog_id = request.form.get('dog_id', type=int)
    appt_type_id = request.form.get('appt_type_id', type=int)
    title = request.form.get('appt_title')
    start_datetime_str = request.form.get('appt_start_datetime')
    end_datetime_str = request.form.get('appt_end_datetime')
    notes = request.form.get('appt_notes')
    
    # Validate dog access
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog, 'dog')
    # Note: check_rescue_access will abort(403) if access is denied
    
    # Parse dates
    try:
        start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_datetime_str, '%Y-%m-%dT%H:%M') if end_datetime_str else None
    except ValueError:
        flash('Invalid date format provided.', 'danger')
        return redirect(url_for('calendar.calendar_view'))
    
    # Create appointment
    appointment = Appointment(
        dog_id=dog_id,
        type_id=appt_type_id,
        title=title,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        description=notes,
        status='scheduled'
    )
    
    db.session.add(appointment)
    db.session.flush()  # Flush to get the appointment ID
    
    # Create reminder for the appointment
    reminder = Reminder(
        dog_id=dog_id,
        appointment_id=appointment.id,
        message=f"Appointment: {title}",
        due_datetime=start_datetime,
        status='pending'
    )
    
    db.session.add(reminder)
    db.session.commit()
    
    flash(f'Appointment "{title}" has been scheduled for {dog.name}.', 'success')
    return redirect(url_for('calendar.calendar_view'))