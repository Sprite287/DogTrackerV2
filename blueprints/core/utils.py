from datetime import datetime, timedelta
from collections import defaultdict
from flask import render_template
from flask_login import current_user
from sqlalchemy.orm import joinedload
from models import Dog, Appointment, DogMedicine, AppointmentType, MedicinePreset, Reminder, RescueMedicineActivation, DogNote, User


def get_rescue_dogs(rescue_id=None):
    """Get dogs for a specific rescue or current user's rescue."""
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return Dog.query.filter_by(rescue_id=rid)


def get_rescue_appointments(rescue_id=None):
    """Get appointments for a specific rescue or current user's rescue."""
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return Appointment.query.filter_by(rescue_id=rid)


def get_rescue_medicines(rescue_id=None):
    """Get medicines for a specific rescue or current user's rescue."""
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return DogMedicine.query.filter_by(rescue_id=rid)


def get_rescue_appointment_types(rescue_id=None):
    """Get appointment types for a specific rescue or current user's rescue."""
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return AppointmentType.query.filter_by(rescue_id=rid)


def get_rescue_medicine_presets(rescue_id=None):
    """Get medicine presets for a specific rescue with activation filtering."""
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    if hasattr(current_user, 'role') and current_user.role == 'superadmin':
        return MedicinePreset.query
    # Get all active activations for this rescue
    active_activations = RescueMedicineActivation.query.filter_by(rescue_id=rid, is_active=True).all()
    active_ids = {a.medicine_preset_id for a in active_activations}
    # Query for rescue-specific presets that are active
    rescue_presets = MedicinePreset.query.filter(MedicinePreset.rescue_id == rid, MedicinePreset.id.in_(active_ids))
    # Query for global presets that are active
    global_presets = MedicinePreset.query.filter(MedicinePreset.rescue_id == None, MedicinePreset.id.in_(active_ids))
    # Union the two queries
    return rescue_presets.union(global_presets)


def get_rescue_reminders(rescue_id=None):
    """Get reminders for a specific rescue or current user's rescue."""
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return Reminder.query.filter(Reminder.dog.has(rescue_id=rid))


def get_dog_history_events(dog_id):
    """Get comprehensive history events for a specific dog."""
    dog = Dog.query.options(
        joinedload(Dog.appointments).joinedload(Appointment.type),
        joinedload(Dog.appointments).joinedload(Appointment.creator),
        joinedload(Dog.medicines).joinedload(DogMedicine.preset),
        joinedload(Dog.medicines).joinedload(DogMedicine.creator),
        joinedload(Dog.reminders).joinedload(Reminder.user)
    ).get_or_404(dog_id)

    # Get care notes separately since it's a dynamic relationship
    care_notes = DogNote.query.filter_by(dog_id=dog_id).options(
        joinedload(DogNote.user)
    ).all()

    history_events = []
    
    # 1. Dog Intake Event
    if dog.intake_date:
        history_events.append({
            'timestamp': datetime.combine(dog.intake_date, datetime.min.time()),
            'event_type': 'Dog Record', 
            'description': f'{dog.name} was taken into care.',
            'author': 'System', 
            'source_model': 'Dog', 
            'source_id': dog.id
        })
    
    # 2. DogNote Events
    for note in care_notes:
        history_events.append({
            'timestamp': note.timestamp, 
            'event_type': f'Note - {note.category}',
            'description': note.note_text, 
            'author': note.user.name if note.user else 'Unknown User',
            'source_model': 'DogNote', 
            'source_id': note.id
        })
    
    # 3. Appointment Events
    for appt in dog.appointments:
        history_events.append({
            'timestamp': appt.created_at,
            'event_type': f'Appointment - {appt.type.name if appt.type else "General"}',
            'description': f'Appointment "{appt.title}" scheduled for {appt.start_datetime.strftime("%Y-%m-%d %I:%M %p")}. Status: {appt.status}.',
            'author': appt.creator.name if appt.creator else 'System/Unknown', 
            'source_model': 'Appointment', 
            'source_id': appt.id
        })
        if appt.updated_at and appt.updated_at != appt.created_at:
            history_events.append({
                'timestamp': appt.updated_at, 
                'event_type': f'Appointment Update - {appt.type.name if appt.type else "General"}',
                'description': f'Details for appointment "{appt.title}" were updated. New Status: {appt.status}.',
                'author': 'System/Unknown', 
                'source_model': 'Appointment', 
                'source_id': appt.id
            })
    
    # 4. DogMedicine Events
    for med in dog.medicines:
        med_name = med.custom_name or (med.preset.name if med.preset else "Unnamed Medicine")
        history_events.append({
            'timestamp': datetime.combine(med.start_date, datetime.min.time()),
            'event_type': f'Medication - {med_name}',
            'description': f'Started medication: {med_name}. Dosage: {med.dosage} {med.unit}, Frequency: {med.frequency}. Status: {med.status}.',
            'author': med.creator.name if med.creator else 'System/Unknown', 
            'source_model': 'DogMedicine', 
            'source_id': med.id
        })
        if med.end_date:
            history_events.append({
                'timestamp': datetime.combine(med.end_date, datetime.max.time() - timedelta(seconds=1)),
                'event_type': f'Medication Ended - {med_name}',
                'description': f'Ended medication: {med_name}.',
                'author': med.creator.name if med.creator else 'System/Unknown', 
                'source_model': 'DogMedicine', 
                'source_id': med.id
            })
        if med.created_at.date() != med.start_date and med.created_at < datetime.combine(med.start_date, datetime.min.time()):
            history_events.append({
                'timestamp': med.created_at, 
                'event_type': f'Medication Logged - {med_name}',
                'description': f'Medication record for {med_name} was created/updated.',
                'author': med.creator.name if med.creator else 'System/Unknown', 
                'source_model': 'DogMedicine', 
                'source_id': med.id
            })
    
    # 5. Reminder Events
    for reminder in dog.reminders:
        history_events.append({
            'timestamp': reminder.created_at, 
            'event_type': 'Reminder Created',
            'description': f'Reminder set: "{reminder.message}" due {reminder.due_datetime.strftime("%Y-%m-%d %I:%M %p")}',
            'author': reminder.user.name if reminder.user else 'System', 
            'source_model': 'Reminder', 
            'source_id': reminder.id
        })
        if reminder.status == 'acknowledged' or reminder.status == 'dismissed':
            status_change_time = reminder.updated_at
            history_events.append({
                'timestamp': status_change_time, 
                'event_type': f'Reminder {reminder.status.title()}',
                'description': f'Reminder "{reminder.message}" was {reminder.status}.',
                'author': reminder.user.name if reminder.user else 'System', 
                'source_model': 'Reminder', 
                'source_id': reminder.id
            })
    
    history_events.sort(key=lambda x: x['timestamp'], reverse=True)
    return dog, history_events


def get_first_user_id():
    """Helper to get the ID of the first available user, or None."""
    first_user = User.query.order_by(User.id.asc()).first()
    if first_user:
        return first_user.id
    print("WARNING: No users found in the database. 'created_by' fields will be None.")
    return None


def group_reminders_by_type(reminders_query):
    """Group reminders by their type for dashboard display."""
    # Define group order preference
    group_order = ["Vet Visit", "Vaccination", "Grooming", "Medication", "General Appointment", "Other Reminder"]
    
    grouped = defaultdict(list)
    for reminder in reminders_query:
        group_name = "Other Reminder"  # Default
        if reminder.appointment:
            if reminder.appointment.type:
                group_name = reminder.appointment.type.name
            else:
                group_name = "General Appointment"
        elif reminder.dog_medicine_id:
            group_name = "Medication"
        elif reminder.reminder_type:  # Fallback to reminder_type if not appt/med
            # Capitalize and replace underscores for better display
            group_name = reminder.reminder_type.replace('_', ' ').title()

        grouped[group_name].append(reminder)
    
    # Order the groups according to group_order, then alphabetically for others
    ordered_grouped = {group: grouped[group] for group in group_order if group in grouped}
    other_groups = {k: v for k, v in sorted(grouped.items()) if k not in ordered_grouped}
    ordered_grouped.update(other_groups)
    return ordered_grouped


def render_dog_cards():
    """Render dog cards for the current user's rescue."""
    if current_user.is_authenticated:
        dogs = Dog.query.filter_by(rescue_id=current_user.rescue_id).order_by(Dog.name.asc()).all()
    else:
        dogs = []
    return render_template('dog_cards.html', dogs=dogs)