from flask import Blueprint, jsonify, url_for, request
from flask_login import login_required, current_user
from models import Appointment, DogMedicine, AppointmentType, Dog
from datetime import datetime, timedelta
from extensions import db
import re

api_bp = Blueprint('api', __name__, url_prefix='')

@api_bp.route('/api/calendar/events')
@login_required
def calendar_events_api():
    try:
        # Get rescue filtering parameters
        rescue_id = request.args.get('rescue_id', type=int)
        
        print(f"[CALENDAR API] User: {current_user.email if current_user else 'None'}, Role: {current_user.role if current_user else 'None'}, Requested rescue_id: {rescue_id}")
        
        events = []
        
        # Apply rescue filtering based on user role and parameters
        if current_user.role == 'superadmin':
            if rescue_id:
                # Filter by specific rescue for superadmin
                appointments = Appointment.query.join(Dog).filter(Dog.rescue_id == rescue_id).options(db.joinedload(Appointment.dog), db.joinedload(Appointment.type)).all()
                medicines = DogMedicine.query.join(Dog).filter(Dog.rescue_id == rescue_id).options(db.joinedload(DogMedicine.dog), db.joinedload(DogMedicine.preset)).filter(DogMedicine.start_date != None).all()
            else:
                # Show all rescues for superadmin when no specific rescue selected
                appointments = Appointment.query.options(db.joinedload(Appointment.dog), db.joinedload(Appointment.type)).all()
                medicines = DogMedicine.query.options(db.joinedload(DogMedicine.dog), db.joinedload(DogMedicine.preset)).filter(DogMedicine.start_date != None).all()
        else:
            # Regular users only see their rescue's data
            appointments = Appointment.query.join(Dog).filter(Dog.rescue_id == current_user.rescue_id).options(db.joinedload(Appointment.dog), db.joinedload(Appointment.type)).all()
            medicines = DogMedicine.query.join(Dog).filter(Dog.rescue_id == current_user.rescue_id).options(db.joinedload(DogMedicine.dog), db.joinedload(DogMedicine.preset)).filter(DogMedicine.start_date != None).all()
        
        # Process appointments
        for appt in appointments:
            if not appt.start_datetime: # Required by FullCalendar
                print(f"Skipping appointment {appt.id} due to missing start_datetime")
                continue

            event_color = appt.type.color if appt.type else '#007bff' 
            # Construct URL to dog details, anchoring to the specific appointment if possible
            # This assumes your dog_details page can handle an anchor like #appointment-ID
            event_url = url_for('dogs.dog_details', dog_id=appt.dog_id, _anchor=f"appointment-{appt.id}") if appt.dog_id else '#'
            
            # Format: "DogName: AppointmentType" (pet name first)
            # Sophisticated data cleaning for complex database structure
            raw_dog_name = appt.dog.name if appt.dog else "Unknown Dog"
            raw_appt_type = appt.type.name if appt.type else (appt.title if appt.title else "Appointment")
            
            # Enhanced dog name cleaning - remove various prefixes and codes
            clean_dog_name = raw_dog_name
            # Remove patterns like "9-C ", "10-O ", "123-A ", etc.
            clean_dog_name = re.sub(r'^\d+-[A-Z]+\s+', '', clean_dog_name)
            # Remove standalone numbers and letters at start
            clean_dog_name = re.sub(r'^\d+[A-Z]?\s+', '', clean_dog_name)
            
            # Enhanced appointment type cleaning and mapping
            clean_appt_type = raw_appt_type
            
            # Map complex product names to simple appointment types
            appt_type_lower = clean_appt_type.lower()
            if any(med in appt_type_lower for med in ['rescue', 'nsaid', 'medication', 'medicine', 'drug', 'pill', 'tablet', 'dose']):
                if any(word in appt_type_lower for word in ['comfort', 'nsaid', 'pain', 'anti-inflammatory']):
                    clean_appt_type = "Pain Medication"
                elif any(word in appt_type_lower for word in ['digest', 'probiotic', 'stomach', 'gastro']):
                    clean_appt_type = "Digestive Medication"
                elif any(word in appt_type_lower for word in ['vitamin', 'supplement', 'nutrition']):
                    clean_appt_type = "Vitamin/Supplement"
                elif any(word in appt_type_lower for word in ['oil', 'omega', 'fatty']):
                    clean_appt_type = "Nutritional Oil"
                elif any(word in appt_type_lower for word in ['benadryl', 'diphenhydramine', 'allergy', 'antihistamine']):
                    clean_appt_type = "Allergy Medication"
                else:
                    clean_appt_type = "Medication"
            elif any(word in appt_type_lower for word in ['vet', 'visit', 'checkup', 'exam', 'doctor']):
                clean_appt_type = "Vet Visit"
            elif any(word in appt_type_lower for word in ['groom', 'bath', 'nail', 'trim']):
                clean_appt_type = "Grooming"
            elif any(word in appt_type_lower for word in ['adoption', 'adopt', 'home']):
                clean_appt_type = "Adoption"
            elif any(word in appt_type_lower for word in ['surgery', 'operation', 'procedure']):
                clean_appt_type = "Surgery"
            else:
                # Clean any remaining rescue/product prefixes
                clean_appt_type = re.sub(r'^Rescue\w*\s*', '', clean_appt_type, flags=re.IGNORECASE)
                clean_appt_type = re.sub(r'\s*(NSAID|Probiotic|Multivitamin|Supplement)\s*$', '', clean_appt_type, flags=re.IGNORECASE)
                if not clean_appt_type.strip():
                    clean_appt_type = "Appointment"
            
            event_title_str = f"{clean_dog_name}: {clean_appt_type}"
            
            # Debug logging
            print(f"[CALENDAR API] Raw dog name: '{raw_dog_name}' -> Clean: '{clean_dog_name}'")
            print(f"[CALENDAR API] Raw appt type: '{raw_appt_type}' -> Clean: '{clean_appt_type}'")
            print(f"[CALENDAR API] Final event title: '{event_title_str}'")

            event_data = {
                'id': f'appt-{appt.id}', # Prefix ID to ensure uniqueness across types
                'title': event_title_str,
                'start': appt.start_datetime.isoformat(),
                'color': event_color,
                'url': event_url,
                'allDay': False,  # Explicitly set for time-based views
                'extendedProps': {
                    'eventType': 'appointment',
                    'dog_name': appt.dog.name if appt.dog else 'N/A',
                    'dog_id': appt.dog_id,
                    'appointment_type': appt.type.name if appt.type else 'N/A',
                    'status': appt.status if appt.status else 'N/A',
                    'description': appt.description if appt.description else '',
                    'location': appt.location if hasattr(appt, 'location') and appt.location else '',
                    'notes': appt.notes if hasattr(appt, 'notes') and appt.notes else appt.description if appt.description else ''
                }
            }
            if appt.end_datetime:
                event_data['end'] = appt.end_datetime.isoformat()
            else:
                # Provide default duration of 1 hour for time views
                end_time = appt.start_datetime + timedelta(hours=1)
                event_data['end'] = end_time.isoformat()
            events.append(event_data)

        # Process medicine start dates (already fetched above with rescue filtering)
        medicine_event_color = "#6c757d" # Default grey for medicine events
        # Attempt to get the color from the "Medication Start" AppointmentType if it exists
        med_start_type = AppointmentType.query.filter_by(name="Medication Start").first()
        if med_start_type and med_start_type.color:
            medicine_event_color = med_start_type.color
            
        for med in medicines:
            if not med.start_date: 
                continue
            
            # Format: "DogName: MedicineName" (pet name first)
            # Sophisticated cleaning for medicine events
            raw_dog_name = med.dog.name if med.dog else 'Unknown Dog'
            raw_med_name = med.custom_name or (med.preset.name if med.preset else "Medicine")
            
            # Enhanced dog name cleaning (same as appointments)
            clean_dog_name = raw_dog_name
            clean_dog_name = re.sub(r'^\d+-[A-Z]+\s+', '', clean_dog_name)
            clean_dog_name = re.sub(r'^\d+[A-Z]?\s+', '', clean_dog_name)
            
            # Enhanced medicine name cleaning and mapping
            clean_med_name = raw_med_name
            med_name_lower = clean_med_name.lower()
            
            # Map complex medicine names to user-friendly types
            if any(med in med_name_lower for med in ['rescue', 'nsaid', 'comfort']):
                if any(word in med_name_lower for word in ['comfort', 'nsaid', 'pain']):
                    clean_med_name = "Pain Medication"
                elif any(word in med_name_lower for word in ['digest', 'probiotic']):
                    clean_med_name = "Digestive Medication"
                elif any(word in med_name_lower for word in ['oil', 'omega']):
                    clean_med_name = "Nutritional Oil"
                elif any(word in med_name_lower for word in ['vitamin', 'multivitamin']):
                    clean_med_name = "Vitamin/Supplement"
                else:
                    clean_med_name = "Medication"
            elif any(word in med_name_lower for word in ['benadryl', 'diphenhydramine']):
                clean_med_name = "Allergy Medication"
            else:
                # Clean any remaining rescue/product prefixes
                clean_med_name = re.sub(r'^Rescue\w*\s*', '', clean_med_name, flags=re.IGNORECASE)
                clean_med_name = re.sub(r'\s*(NSAID|Probiotic|Multivitamin|Supplement)\s*$', '', clean_med_name, flags=re.IGNORECASE)
                if not clean_med_name.strip():
                    clean_med_name = "Medication"
            
            event_title = f"{clean_dog_name}: {clean_med_name}"
            event_start_datetime = datetime.combine(med.start_date, datetime.min.time()) + timedelta(hours=9)
            event_end_datetime = event_start_datetime + timedelta(hours=1)

            # Construct URL to dog details, anchoring to the specific medicine if possible
            # This assumes your dog_details page can handle an anchor like #medicine-ID
            event_url = url_for('dogs.dog_details', dog_id=med.dog_id, _anchor=f"medicine-{med.id}") if med.dog_id else '#'

            events.append({
                'id': f'med-{med.id}', # Prefix ID
                'title': event_title,
                'start': event_start_datetime.isoformat(),
                'end': event_end_datetime.isoformat(),
                'allDay': False,  # Explicitly set for time-based views
                'color': medicine_event_color, 
                'url': event_url,
                'extendedProps': {
                    'eventType': 'medicine_start',
                    'dog_name': med.dog.name if med.dog else 'N/A',
                    'dog_id': med.dog_id,
                    'medicine_name': clean_med_name,
                    'dosage': med.dosage,
                    'unit': med.unit,
                    'status': med.status,
                    'notes': med.notes if med.notes else ''
                }
            })

        print(f"[CALENDAR API] Returning {len(events)} events (appointments: {len([e for e in events if e['id'].startswith('appt')])}, medicines: {len([e for e in events if e['id'].startswith('med')])})")
        return jsonify(events)
    except Exception as e:
        print(f"Error in calendar_events_api: {e}")
        return jsonify({"error": str(e), "message": "Failed to load calendar events."}), 500


@api_bp.route('/api/calendar/reminders')
@login_required
def calendar_reminders_api():
    """API endpoint for fetching filtered reminders for the calendar page."""
    try:
        from blueprints.core.utils import get_rescue_reminders
        from models import Reminder, Rescue
        from collections import defaultdict
        
        # Get rescue filtering parameters
        rescue_id = request.args.get('rescue_id', type=int)
        
        print(f"[REMINDERS API] User: {current_user.email if current_user else 'None'}, Role: {current_user.role if current_user else 'None'}, Requested rescue_id: {rescue_id}")
        
        # Apply rescue filtering based on user role and parameters
        if current_user.role == 'superadmin':
            rescues = Rescue.query.order_by(Rescue.name.asc()).all()
            if rescue_id:
                reminders_query = get_rescue_reminders(rescue_id).all()
            else:
                reminders_query = Reminder.query.filter(Reminder.status == 'pending').order_by(Reminder.due_datetime.asc()).all()
        else:
            rescues = None
            rescue_id = current_user.rescue_id
            reminders_query = get_rescue_reminders().filter(Reminder.status == 'pending').order_by(Reminder.due_datetime.asc()).all()
        
        # Group reminders same as calendar_view route
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
        
        # Convert reminder objects to serializable format
        reminders_data = {}
        for group_name, reminders_list in ordered_final_groups.items():
            if reminders_list:  # Only include groups with reminders
                reminders_data[group_name] = []
                for reminder in reminders_list:
                    reminder_data = {
                        'id': reminder.id,
                        'message': reminder.message,
                        'due_datetime': reminder.due_datetime.strftime('%a, %b %d, %Y @ %I:%M %p UTC'),
                        'dog_id': reminder.dog.id if reminder.dog else None,
                        'dog_name': reminder.dog.name if reminder.dog else None,
                        'appointment_id': reminder.appointment_id,
                        'dog_medicine_id': reminder.dog_medicine_id
                    }
                    reminders_data[group_name].append(reminder_data)
        
        response_data = {
            'grouped_reminders': reminders_data,
            'rescues': [{'id': r.id, 'name': r.name} for r in rescues] if rescues else None,
            'selected_rescue_id': rescue_id
        }
        
        print(f"[REMINDERS API] Returning {sum(len(group) for group in reminders_data.values())} reminders in {len(reminders_data)} groups")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in calendar_reminders_api: {e}")
        return jsonify({"error": str(e), "message": "Failed to load calendar reminders."}), 500