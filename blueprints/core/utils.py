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


# Phase R4C-3: Medicine Frequency Interpretation Engine

def parse_medicine_frequency(frequency_text):
    """
    Parse medical frequency abbreviations into structured data.
    
    Args:
        frequency_text (str): The frequency text (e.g., "BID", "twice daily", "2x daily")
        
    Returns:
        dict: {
            'times_per_day': int,
            'is_as_needed': bool,
            'parsed_from': str,
            'display_name': str
        }
    """
    if not frequency_text:
        return {'times_per_day': 1, 'is_as_needed': False, 'parsed_from': 'default', 'display_name': 'Once daily'}
    
    # Normalize input
    freq_lower = frequency_text.lower().strip()
    
    # Medical abbreviation mappings
    frequency_mappings = {
        # Standard medical abbreviations
        'sid': {'times_per_day': 1, 'display_name': 'Once daily (SID)'},
        'qd': {'times_per_day': 1, 'display_name': 'Once daily (QD)'},
        'od': {'times_per_day': 1, 'display_name': 'Once daily (OD)'},
        'bid': {'times_per_day': 2, 'display_name': 'Twice daily (BID)'},
        'tid': {'times_per_day': 3, 'display_name': 'Three times daily (TID)'},
        'qid': {'times_per_day': 4, 'display_name': 'Four times daily (QID)'},
        'q6h': {'times_per_day': 4, 'display_name': 'Every 6 hours (Q6H)'},
        'q8h': {'times_per_day': 3, 'display_name': 'Every 8 hours (Q8H)'},
        'q12h': {'times_per_day': 2, 'display_name': 'Every 12 hours (Q12H)'},
        
        # As needed
        'prn': {'times_per_day': 0, 'is_as_needed': True, 'display_name': 'As needed (PRN)'},
        'as needed': {'times_per_day': 0, 'is_as_needed': True, 'display_name': 'As needed'},
        
        # Common text variations
        'once daily': {'times_per_day': 1, 'display_name': 'Once daily'},
        'once a day': {'times_per_day': 1, 'display_name': 'Once daily'},
        'daily': {'times_per_day': 1, 'display_name': 'Once daily'},
        'twice daily': {'times_per_day': 2, 'display_name': 'Twice daily'},
        'twice a day': {'times_per_day': 2, 'display_name': 'Twice daily'},
        'three times daily': {'times_per_day': 3, 'display_name': 'Three times daily'},
        'three times a day': {'times_per_day': 3, 'display_name': 'Three times daily'},
        'four times daily': {'times_per_day': 4, 'display_name': 'Four times daily'},
        'four times a day': {'times_per_day': 4, 'display_name': 'Four times daily'},
    }
    
    # Check for exact matches first
    if freq_lower in frequency_mappings:
        result = frequency_mappings[freq_lower].copy()
        result['parsed_from'] = 'exact_match'
        result.setdefault('is_as_needed', False)
        return result
    
    # Pattern matching for "Nx daily", "X times daily", etc.
    import re
    
    # Pattern: "2x daily", "3x a day", etc.
    pattern1 = re.search(r'(\d+)x?\s*(?:times?\s*)?(?:per\s+day|daily|a\s+day)', freq_lower)
    if pattern1:
        times = int(pattern1.group(1))
        return {
            'times_per_day': times,
            'is_as_needed': False,
            'parsed_from': 'pattern_match',
            'display_name': f'{times} times daily'
        }
    
    # Pattern: "every X hours"
    pattern2 = re.search(r'every\s+(\d+)\s*hours?', freq_lower)
    if pattern2:
        hours = int(pattern2.group(1))
        times_per_day = 24 // hours if hours > 0 else 1
        return {
            'times_per_day': times_per_day,
            'is_as_needed': False,
            'parsed_from': 'pattern_match',
            'display_name': f'Every {hours} hours ({times_per_day}x daily)'
        }
    
    # Default fallback - treat as once daily
    return {
        'times_per_day': 1,
        'is_as_needed': False,
        'parsed_from': 'fallback',
        'display_name': f'Once daily (from "{frequency_text}")'
    }


def generate_daily_medicine_reminders(dog_medicine, user_id):
    """
    Generate daily recurring reminders based on medicine frequency.
    
    Args:
        dog_medicine: DogMedicine instance
        user_id: User ID for reminder creation
        
    Returns:
        list: Created Reminder instances
    """
    from models import Reminder
    from datetime import datetime, timedelta, time
    
    if not dog_medicine.start_date:
        return []
    
    # Parse frequency
    frequency_data = parse_medicine_frequency(dog_medicine.frequency)
    
    # Skip if it's PRN (as needed)
    if frequency_data.get('is_as_needed', False):
        return []
    
    times_per_day = frequency_data.get('times_per_day', 1)
    
    # Calculate end date (default to 30 days if no end date specified)
    end_date = dog_medicine.end_date
    if not end_date:
        end_date = dog_medicine.start_date + timedelta(days=30)
    
    # Calculate date range
    current_date = dog_medicine.start_date
    created_reminders = []
    
    # Default reminder times based on frequency
    if times_per_day == 1:
        reminder_times = [time(9, 0)]  # 9 AM
    elif times_per_day == 2:
        reminder_times = [time(9, 0), time(21, 0)]  # 9 AM, 9 PM
    elif times_per_day == 3:
        reminder_times = [time(9, 0), time(15, 0), time(21, 0)]  # 9 AM, 3 PM, 9 PM
    elif times_per_day == 4:
        reminder_times = [time(9, 0), time(15, 0), time(21, 0), time(1, 0)]  # 9 AM, 3 PM, 9 PM, 1 AM
    else:
        # For frequencies > 4, distribute evenly across 24 hours
        hours_between = 24 / times_per_day
        reminder_times = []
        for i in range(times_per_day):
            hour = int(9 + (i * hours_between)) % 24  # Start at 9 AM and distribute
            reminder_times.append(time(hour, 0))
    
    # Get medicine name for reminder message
    medicine_name = 'Medicine'
    if dog_medicine.medicine_id:
        from models import MedicinePreset
        preset = MedicinePreset.query.get(dog_medicine.medicine_id)
        if preset:
            medicine_name = preset.name
    elif dog_medicine.custom_name:
        medicine_name = dog_medicine.custom_name
    
    # Generate reminders for each day in the range
    while current_date <= end_date:
        for reminder_time in reminder_times:
            reminder_datetime = datetime.combine(current_date, reminder_time)
            
            # Skip if the reminder time is in the past
            if reminder_datetime < datetime.now():
                continue
            
            # Create reminder message
            dosage_info = f"{dog_medicine.dosage} {dog_medicine.unit}" if dog_medicine.dosage and dog_medicine.unit else ""
            reminder_message = f"Give {dog_medicine.dog.name} their {medicine_name}"
            if dosage_info:
                reminder_message += f" ({dosage_info})"
            reminder_message += f" - {frequency_data['display_name']}"
            
            # Create reminder
            reminder = Reminder(
                message=reminder_message,
                due_datetime=reminder_datetime,
                status='pending',
                reminder_type='medicine_daily',
                dog_id=dog_medicine.dog_id,
                dog_medicine_id=dog_medicine.id,
                user_id=user_id
            )
            
            created_reminders.append(reminder)
        
        current_date += timedelta(days=1)
    
    return created_reminders