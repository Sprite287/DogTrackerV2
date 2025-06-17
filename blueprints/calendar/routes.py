from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from collections import defaultdict
from blueprints.core.decorators import rescue_access_required
from models import Reminder, Rescue
from blueprints.core.utils import get_rescue_reminders

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
    
    return render_template('calendar_view.html', grouped_reminders=ordered_final_groups, rescues=rescues, selected_rescue_id=rescue_id)