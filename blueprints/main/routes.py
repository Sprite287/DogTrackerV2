from flask import Blueprint, redirect, url_for, render_template, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from sqlalchemy.orm import joinedload
from extensions import db
from models import Reminder, Appointment, DogMedicine, Rescue
from blueprints.core.utils import group_reminders_by_type

main_bp = Blueprint('main', __name__, url_prefix='')

@main_bp.route('/')
def home_redirect():
    """Redirect users to appropriate landing page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page with reminders and statistics."""
    rescue_id = request.args.get('rescue_id', type=int)
    
    if current_user.role == 'superadmin':
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        if rescue_id:
            # Filter reminders for specific rescue
            overdue_reminders = Reminder.query.options(
                db.joinedload(Reminder.appointment).joinedload(Appointment.type),
                db.joinedload(Reminder.dog_medicine).joinedload(DogMedicine.preset),
                db.joinedload(Reminder.dog)
            ).filter(
                Reminder.status == 'pending',
                Reminder.due_datetime < datetime.utcnow(),
                Reminder.dog.has(rescue_id=rescue_id)
            ).order_by(Reminder.due_datetime.asc()).all()
            
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = today_start + timedelta(days=1)
            today_reminders = Reminder.query.options(
                db.joinedload(Reminder.appointment).joinedload(Appointment.type),
                db.joinedload(Reminder.dog_medicine).joinedload(DogMedicine.preset),
                db.joinedload(Reminder.dog)
            ).filter(
                Reminder.status == 'pending',
                Reminder.due_datetime >= today_start,
                Reminder.due_datetime < today_end,
                Reminder.dog.has(rescue_id=rescue_id)
            ).order_by(Reminder.due_datetime.asc()).all()
        else:
            # All reminders across all rescues
            overdue_reminders = Reminder.query.options(
                db.joinedload(Reminder.appointment).joinedload(Appointment.type),
                db.joinedload(Reminder.dog_medicine).joinedload(DogMedicine.preset),
                db.joinedload(Reminder.dog)
            ).filter(
                Reminder.status == 'pending',
                Reminder.due_datetime < datetime.utcnow()
            ).order_by(Reminder.due_datetime.asc()).all()
            
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = today_start + timedelta(days=1)
            today_reminders = Reminder.query.options(
                db.joinedload(Reminder.appointment).joinedload(Appointment.type),
                db.joinedload(Reminder.dog_medicine).joinedload(DogMedicine.preset),
                db.joinedload(Reminder.dog)
            ).filter(
                Reminder.status == 'pending',
                Reminder.due_datetime >= today_start,
                Reminder.due_datetime < today_end
            ).order_by(Reminder.due_datetime.asc()).all()
    else:
        # Regular users see only their rescue's reminders
        rescues = None
        rescue_id = current_user.rescue_id
        overdue_reminders = Reminder.query.options(
            db.joinedload(Reminder.appointment).joinedload(Appointment.type),
            db.joinedload(Reminder.dog_medicine).joinedload(DogMedicine.preset),
            db.joinedload(Reminder.dog)
        ).filter(
            Reminder.status == 'pending',
            Reminder.due_datetime < datetime.utcnow(),
            Reminder.dog.has(rescue_id=rescue_id)
        ).order_by(Reminder.due_datetime.asc()).all()
        
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = today_start + timedelta(days=1)
        today_reminders = Reminder.query.options(
            db.joinedload(Reminder.appointment).joinedload(Appointment.type),
            db.joinedload(Reminder.dog_medicine).joinedload(DogMedicine.preset),
            db.joinedload(Reminder.dog)
        ).filter(
            Reminder.status == 'pending',
            Reminder.due_datetime >= today_start,
            Reminder.due_datetime < today_end,
            Reminder.dog.has(rescue_id=rescue_id)
        ).order_by(Reminder.due_datetime.asc()).all()

    # Group reminders by type for better organization
    overdue_grouped = group_reminders_by_type(overdue_reminders)
    today_grouped = group_reminders_by_type(today_reminders)

    return render_template('dashboard.html',
                         current_user=current_user,
                         grouped_overdue_reminders=overdue_grouped,
                         grouped_today_reminders=today_grouped,
                         now=datetime.utcnow(),
                         rescues=rescues,
                         selected_rescue_id=rescue_id)