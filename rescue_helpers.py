from flask_login import current_user
from models import Dog, Appointment, DogMedicine, AppointmentType, MedicinePreset, Reminder, RescueMedicineActivation


def get_rescue_dogs(rescue_id=None):
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return Dog.query.filter_by(rescue_id=rid)

def get_rescue_appointments(rescue_id=None):
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return Appointment.query.filter_by(rescue_id=rid)

def get_rescue_medicines(rescue_id=None):
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return DogMedicine.query.filter_by(rescue_id=rid)

def get_rescue_appointment_types(rescue_id=None):
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return AppointmentType.query.filter_by(rescue_id=rid)

def get_rescue_medicine_presets(rescue_id=None):
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
    rid = rescue_id if rescue_id is not None else current_user.rescue_id
    return Reminder.query.filter(Reminder.dog.has(rescue_id=rid)) 