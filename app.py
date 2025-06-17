from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, render_template_string, get_flashed_messages, make_response, send_file, abort, g, session
import os
from extensions import db, migrate, login_manager
from flask_wtf.csrf import CSRFProtect
import json
from models import Dog, AppointmentType, MedicinePreset, Appointment, DogMedicine, Reminder, User, DogNote, Rescue, AuditLog
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import joinedload
import csv
import io
from werkzeug.utils import secure_filename
from audit import log_audit_event, AuditCleanupThread, get_audit_system_stats, _audit_batcher, cleanup_old_audit_logs, init_audit
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm, RegistrationForm, RescueRegistrationForm, PasswordResetRequestForm, PasswordResetForm, AuditForm
from rescue_helpers import get_rescue_dogs, get_rescue_appointments, get_rescue_medicines, get_rescue_reminders, get_rescue_medicine_presets
from permissions import roles_required, role_required, rescue_access_required
from werkzeug.security import generate_password_hash
import secrets
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFError
import secrets
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import bleach
from flask_mail import Mail, Message
import warnings

# Load configuration from centralized config
from config import config

# Load environment variables from .env if present
load_dotenv()

# Initialize Flask app with centralized configuration
config_name = os.getenv('FLASK_ENV', 'development')
app = Flask(__name__)
app.config.from_object(config[config_name])
config[config_name].init_app(app)

# Import blueprints
from blueprints.main.routes import main_bp
from blueprints.auth.routes import auth_bp
from blueprints.dogs.routes import dogs_bp
from blueprints.appointments.routes import appointments_bp
from blueprints.medicines.routes import medicines_bp
from blueprints.admin.routes import admin_bp
from blueprints.api.routes import api_bp
from blueprints.calendar.routes import calendar_bp

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dogs_bp)
app.register_blueprint(appointments_bp)
app.register_blueprint(medicines_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)
app.register_blueprint(calendar_bp)

# Register error handlers from core module
from blueprints.core.errors import register_error_handlers
register_error_handlers(app)

csrf = CSRFProtect(app)


db.init_app(app)
migrate.init_app(app, db)

# Initialize Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Custom key function for Flask-Limiter
def get_rate_limit_key():
    if current_user.is_authenticated:
        return str(current_user.get_id()) # Use user ID for authenticated users
    return get_remote_address() # Fallback to IP address for anonymous users

# Initialize Flask-Limiter
limiter = Limiter(
    key_func=get_rate_limit_key, # Use our custom key function
    app=app,
    default_limits=["200 per day", "50 per hour"], # Global default limits
    # You can also define specific limits for authenticated users vs anonymous if needed
    # by using different decorators or conditional logic within routes.
    # For example, a stricter limit for anonymous users on certain actions.
    default_limits_per_method=True,
    default_limits_exempt_when=lambda: current_user.is_authenticated and current_user.is_rescue_admin() # Example: exempt admins
)

# Flask-Mail configuration (use environment variables for secrets in production)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.example.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() in ['true', '1', 'yes']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'DogTracker <noreply@example.com>')

mail = Mail(app)

# Initialize mail and limiter for auth blueprint
from blueprints.auth.routes import init_mail, init_limiter
init_mail(mail)
init_limiter(limiter)

# Initialize Audit System (disable cleanup thread during migration)
init_audit(app, start_cleanup_thread=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Dog-related functions moved to blueprints/dogs/routes.py in Phase R4A

def group_reminders_by_type(reminders_query):
    """Group reminders by their type for dashboard display."""
    from collections import defaultdict
    
    # Define group order preference
    group_order = ["Vet Visit", "Vaccination", "Grooming", "Medication", "General Appointment", "Other Reminder"]
    
    grouped = defaultdict(list)
    for reminder in reminders_query:
        group_name = "Other Reminder" # Default
        if reminder.appointment:
            if reminder.appointment.type:
                group_name = reminder.appointment.type.name
            else:
                group_name = "General Appointment"
        elif reminder.dog_medicine_id:
            group_name = "Medication"
        elif reminder.reminder_type: # Fallback to reminder_type if not appt/med
             # Capitalize and replace underscores for better display
            group_name = reminder.reminder_type.replace('_', ' ').title()

        grouped[group_name].append(reminder)
    
    # Order the groups according to group_order, then alphabetically for others
    ordered_grouped = {group: grouped[group] for group in group_order if group in grouped}
    other_groups = {k: v for k, v in sorted(grouped.items()) if k not in ordered_grouped}
    ordered_grouped.update(other_groups)
    return ordered_grouped

# render_dog_cards moved to blueprints/dogs/routes.py in Phase R4A

def render_alert(message, category='success'):
    return render_template_string('<div class="alert alert-{{ category }} alert-dismissible fade show" role="alert" hx-swap-oob="true">{{ message }}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>', message=message, category=category)

# Home route moved to blueprints/main/routes.py
# @app.route('/')
# def home_redirect():

# Authentication Routes moved to blueprints/auth/routes.py
# @app.route('/login', methods=['GET', 'POST'])
# @limiter.limit("5 per minute")
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for('main.dashboard'))
#     
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         if user and user.check_password(form.password.data):
#             if not user.is_active:
#                 flash('Your account has been deactivated. Please contact support.', 'danger')
#                 return render_template('auth/login.html', form=form)
#             if not user.email_verified:
#                 flash('Please verify your email before logging in. Check your inbox for the verification link.', 'warning')
#                 return render_template('auth/login.html', form=form)
#             login_user(user, remember=form.remember_me.data)
#             user.last_login = datetime.utcnow()
#             db.session.commit()
#             # Log successful login
#             log_audit_event(
#                 user_id=user.id,
#                 rescue_id=user.rescue_id,
#                 action='login_success',
#                 resource_type='User',
#                 resource_id=user.id,
#                 details={'email': user.email},
#                 ip_address=request.remote_addr,
#                 user_agent=request.headers.get('User-Agent'),
#                 success=True
#             )
#             next_page = request.args.get('next')
#             if not next_page or not next_page.startswith('/'):
#                 next_page = url_for('main.dashboard')
#             return redirect(next_page)
#         else:
#             # Log failed login attempt
#             log_audit_event(
#                 user_id=None,
#                 rescue_id=None,
#                 action='login_failed',
#                 resource_type='User',
#                 resource_id=None,
#                 details={'email': form.email.data, 'reason': 'invalid_credentials'},
#                 ip_address=request.remote_addr,
#                 user_agent=request.headers.get('User-Agent'),
#                 success=False
#             )
#             flash('Invalid email or password.', 'danger')
#     return render_template('auth/login.html', form=form)

# @app.route('/logout')
# @login_required
# def logout():
#     # Log logout
#     log_audit_event(
#         user_id=current_user.id,
#         rescue_id=current_user.rescue_id,
#         action='logout',
#         resource_type='User',
#         resource_id=current_user.id,
#         details={'email': current_user.email},
#         ip_address=request.remote_addr,
#         user_agent=request.headers.get('User-Agent'),
#         success=True
#     )
#     
#     logout_user()
#     flash('You have been logged out successfully.', 'info')
#     return redirect(url_for('login'))

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if current_user.is_authenticated:
#         return redirect(url_for('main.dashboard'))
#     
#     form = RegistrationForm()
#     if form.validate_on_submit():
#         # This is for individual user registration (not rescue registration)
#         # For now, redirect to rescue registration
#         flash('Please register your rescue organization first.', 'info')
#         return redirect(url_for('register_rescue'))
#     
#     return render_template('auth/register.html', form=form)

# @app.route('/register-rescue', methods=['GET', 'POST'])
# def register_rescue():
#     if current_user.is_authenticated:
#         return redirect(url_for('main.dashboard'))
#     
#     form = RescueRegistrationForm()
#     if form.validate_on_submit():
#         # Create rescue
#         rescue = Rescue(
#             name=form.rescue_name.data,
#             address=form.rescue_address.data,
#             phone=form.rescue_phone.data,
#             email=form.rescue_email.data,
#             primary_contact_name=form.contact_name.data,
#             primary_contact_email=form.contact_email.data,
#             primary_contact_phone=form.contact_phone.data,
#             data_consent=form.data_consent.data,
#             marketing_consent=form.marketing_consent.data,
#             status='active'  # No admin approval needed
#         )
#         db.session.add(rescue)
#         db.session.flush()  # Get the rescue ID
#         
#         # Create first user (admin of the rescue)
#         user = User(
#             name=form.contact_name.data,
#             email=form.contact_email.data,
#             role='admin',
#             rescue_id=rescue.id,
#             is_first_user=True,
#             email_verified=False,  # Will need email verification
#             data_consent=form.data_consent.data,
#             marketing_consent=form.marketing_consent.data
#         )
#         user.set_password(form.contact_password.data)
#         token = user.generate_email_verification_token()
#         db.session.add(user)
#         db.session.commit()
#         
#         # Send verification email
#         verification_url = url_for('verify_email', token=token, _external=True)
#         try:
#             msg = Message(
#                 subject="Verify your DogTracker account",
#                 recipients=[user.email],
#                 body=f"Hello {user.name},\n\nPlease verify your email by clicking the link below:\n{verification_url}\n\nIf you did not register, please ignore this email."
#             )
#             mail.send(msg)
#         except Exception as e:
#             print(f"[EMAIL ERROR] Failed to send verification email: {e}")
#             flash('Registration successful, but failed to send verification email. Please contact support.', 'danger')
#             return redirect(url_for('login'))
#         
#         # Log rescue registration
#         log_audit_event(
#             user_id=user.id,
#             rescue_id=rescue.id,
#             action='rescue_registration',
#             resource_type='Rescue',
#             resource_id=rescue.id,
#             details={
#                 'rescue_name': rescue.name,
#                 'primary_contact_email': rescue.primary_contact_email,
#                 'status': rescue.status
#             },
#             ip_address=request.remote_addr,
#             user_agent=request.headers.get('User-Agent'),
#             success=True
#         )
#         
#         flash('Registration successful! Please check your email to verify your account before logging in.', 'success')
#         return redirect(url_for('login'))
#     
#     return render_template('auth/register_rescue.html', form=form)
# 
# @app.route('/password-reset-request', methods=['GET', 'POST'])
# @limiter.limit("3 per minute")
# def password_reset_request():
#     if current_user.is_authenticated:
#         return redirect(url_for('main.dashboard'))
#     
#     form = PasswordResetRequestForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(email=form.email.data).first()
#         if user:
#             token = user.generate_password_reset_token()
#             db.session.commit()
#             
#             # Log password reset request
#             log_audit_event(
#                 user_id=user.id,
#                 rescue_id=user.rescue_id,
#                 action='password_reset_request',
#                 resource_type='User',
#                 resource_id=user.id,
#                 details={'email': user.email},
#                 ip_address=request.remote_addr,
#                 user_agent=request.headers.get('User-Agent'),
#                 success=True
#             )
#             
#             # TODO: Send email with reset link
#             # For now, just show a message
#             flash(f'Password reset instructions have been sent to {form.email.data}. (Note: Email functionality not yet implemented)', 'info')
#         else:
#             # Don't reveal if email exists or not for security
#             flash(f'If an account with email {form.email.data} exists, password reset instructions have been sent.', 'info')
#         
#         return redirect(url_for('login'))
#     
#     return render_template('auth/password_reset_request.html', form=form)
# 
# @app.route('/password-reset/<token>', methods=['GET', 'POST'])
# def password_reset(token):
#     if current_user.is_authenticated:
#         return redirect(url_for('main.dashboard'))
#     
#     user = User.query.filter_by(password_reset_token=token).first()
#     if not user or not user.verify_password_reset_token(token):
#         flash('Invalid or expired password reset token.', 'danger')
#         return redirect(url_for('login'))
#     
#     form = PasswordResetForm()
#     if form.validate_on_submit():
#         user.set_password(form.password.data)
#         user.password_reset_token = None
#         user.password_reset_expires = None
#         db.session.commit()
#         
#         # Log successful password reset
#         log_audit_event(
#             user_id=user.id,
#             rescue_id=user.rescue_id,
#             action='password_reset_success',
#             resource_type='User',
#             resource_id=user.id,
#             details={'email': user.email},
#             ip_address=request.remote_addr,
#             user_agent=request.headers.get('User-Agent'),
#             success=True
#         )
#         
#         flash('Your password has been reset successfully. You can now log in.', 'success')
#         return redirect(url_for('login'))
#     
#     return render_template('auth/password_reset.html', form=form)

# Phase R4A: Dog routes migrated to blueprints/dogs/routes.py
# The following routes were moved to the dogs blueprint to avoid conflicts:
# - /dogs (dog_list_page)
# - /dog/add (add_dog)
# - /dog/edit (edit_dog)
# - /dog/<int:dog_id>/delete (delete_dog)
# - /dog/<int:dog_id> (dog_details)
# - render_dog_cards_html() helper function
# - render_dog_stats_html() helper function

# Phase R4B: Appointment routes migrated to blueprints/appointments/routes.py

# Phase R4B: edit_appointment migrated to blueprints/appointments/routes.py
# Phase R4B: delete_appointment migrated to blueprints/appointments/routes.py

# --- Medicines CRUD ---
# Moved to blueprints/medicines/routes.py in Phase R4C-2

# Moved to blueprints/medicines/routes.py in Phase R4C-2

# Moved to blueprints/medicines/routes.py in Phase R4C-2

# Phase R4B: api_get_appointment migrated to blueprints/appointments/routes.py

# Moved to blueprints/medicines/routes.py in Phase R4C-2

# --- Reminders Page ---
# This route is being removed as its functionality is merged into /calendar
# @app.route('/reminders')
# def reminders_page():
#     # TODO: Filter by current_user.id when user system is fully integrated
#     # For now, fetching reminders for user_id=1 or all pending if user_id is nullable and might be None
#     pending_reminders = Reminder.query.filter_by(status='pending').order_by(Reminder.due_datetime.asc()).all()
#     return render_template('reminders_page.html', reminders=pending_reminders)

@app.route('/reminder/<int:reminder_id>/acknowledge', methods=['POST'])
@rescue_access_required(lambda kwargs: Reminder.query.get(kwargs['reminder_id']).dog.rescue_id if Reminder.query.get(kwargs['reminder_id']).dog else None)
@login_required
def acknowledge_reminder(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    reminder.status = 'acknowledged'
    db.session.commit()
    return '', 200

@app.route('/reminder/<int:reminder_id>/dismiss', methods=['POST'])
@rescue_access_required(lambda kwargs: Reminder.query.get(kwargs['reminder_id']).dog.rescue_id if Reminder.query.get(kwargs['reminder_id']).dog else None)
@login_required
def dismiss_reminder(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    reminder.status = 'dismissed'
    db.session.commit()
    return '', 200

# --- Calendar Integration ---
@app.route('/calendar')
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
    from collections import defaultdict
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

@app.route('/api/calendar/events')
def calendar_events_api():
    try:
        events = []
        # Fetch and process appointments
        appointments = Appointment.query.options(db.joinedload(Appointment.dog), db.joinedload(Appointment.type)).all()
        for appt in appointments:
            if not appt.start_datetime: # Required by FullCalendar
                print(f"Skipping appointment {appt.id} due to missing start_datetime")
                continue

            event_color = appt.type.color if appt.type else '#007bff' 
            # Construct URL to dog details, anchoring to the specific appointment if possible
            # This assumes your dog_details page can handle an anchor like #appointment-ID
            event_url = url_for('dogs.dog_details', dog_id=appt.dog_id, _anchor=f"appointment-{appt.id}") if appt.dog_id else '#'
            
            event_title_parts = []
            if appt.dog: event_title_parts.append(appt.dog.name)
            else: event_title_parts.append("Unknown Dog")
            
            main_title_part = appt.title
            if not main_title_part and appt.type: main_title_part = appt.type.name
            if not main_title_part: main_title_part = "Appointment"
            event_title_str = " - ".join(filter(None, event_title_parts))

            event_data = {
                'id': f'appt-{appt.id}', # Prefix ID to ensure uniqueness across types
                'title': event_title_str,
                'start': appt.start_datetime.isoformat(),
                'color': event_color,
                'url': event_url,
                'extendedProps': {
                    'eventType': 'appointment',
                    'dog_name': appt.dog.name if appt.dog else 'N/A',
                    'appointment_type': appt.type.name if appt.type else 'N/A',
                    'status': appt.status if appt.status else 'N/A',
                    'description': appt.description if appt.description else ''
                }
            }
            if appt.end_datetime:
                event_data['end'] = appt.end_datetime.isoformat()
            events.append(event_data)

        # Fetch and process medicine start dates
        medicines = DogMedicine.query.options(db.joinedload(DogMedicine.dog), db.joinedload(DogMedicine.preset)).filter(DogMedicine.start_date != None).all()
        medicine_event_color = "#6c757d" # Default grey for medicine events
        # Attempt to get the color from the "Medication Start" AppointmentType if it exists
        med_start_type = AppointmentType.query.filter_by(name="Medication Start").first()
        if med_start_type and med_start_type.color:
            medicine_event_color = med_start_type.color
            
        for med in medicines:
            if not med.start_date: 
                continue
            
            # Corrected access to medicine_preset
            med_name = med.custom_name or (med.preset.name if med.preset else "Medicine")
            event_title = f"{med.dog.name if med.dog else 'Unknown Dog'} - {med_name} (Meds Start)"
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
                'color': medicine_event_color, 
                'url': event_url,
                'extendedProps': {
                    'eventType': 'medicine_start',
                    'dog_name': med.dog.name if med.dog else 'N/A',
                    'medicine_name': med_name,
                    'dosage': med.dosage,
                    'unit': med.unit,
                    'status': med.status,
                    'notes': med.notes if med.notes else ''
                }
            })

        return jsonify(events)
    except Exception as e:
        print(f"Error in calendar_events_api: {e}")
        return jsonify({"error": str(e), "message": "Failed to load calendar events."}), 500

# Dashboard route moved to blueprints/main/routes.py
# @app.route('/dashboard')
# @login_required  
# def dashboard():
# Dashboard function body moved to blueprints/main/routes.py
#     Complete dashboard implementation now in main blueprint

@app.route('/dog/<int:dog_id>/history')
@login_required
def dog_history(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    if current_user.role != 'superadmin' and dog.rescue_id != current_user.rescue_id:
        abort(403)
    dog, all_history_events = _get_dog_history_events(dog_id)
    
    # Calculate days in care if intake_date exists
    days_in_care = None
    if dog.intake_date:
        days_in_care = (datetime.now().date() - dog.intake_date).days
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    total_events = len(all_history_events)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_events = all_history_events[start_index:end_index]

    return render_template('dog_history.html', 
                           dog=dog, 
                           history_events=paginated_events,
                           days_in_care=days_in_care,
                           page=page,
                           per_page=per_page,
                           total_events=total_events)

@app.route('/history')
def dog_history_overview():
    rescue_id = request.args.get('rescue_id', type=int)
    if current_user.role == 'superadmin':
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        if rescue_id:
            dogs = Dog.query.filter_by(rescue_id=rescue_id).order_by(Dog.name.asc()).all()
        else:
            dogs = Dog.query.order_by(Dog.name.asc()).all()
    else:
        rescues = None
        rescue_id = current_user.rescue_id
        dogs = Dog.query.filter_by(rescue_id=current_user.rescue_id).order_by(Dog.name.asc()).all()
    # Organize dogs alphabetically for accordion display
    dogs_by_letter = {}
    for dog in dogs:
        first_letter = dog.name[0].upper() if dog.name else 'Unknown'
        if first_letter not in dogs_by_letter:
            dogs_by_letter[first_letter] = []
        dogs_by_letter[first_letter].append(dog)
    sorted_dogs_by_letter = dict(sorted(dogs_by_letter.items()))
    # Get recent history events across all dogs (last 20 events)
    recent_events = []
    for dog in dogs:
        _, dog_events = _get_dog_history_events(dog.id)
        for event in dog_events:
            event['dog_name'] = dog.name
            event['dog_id'] = dog.id
        recent_events.extend(dog_events)
    recent_events.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_events = recent_events[:20]
    return render_template('dog_history_overview.html', 
                           dogs=dogs,
                           dogs_by_letter=sorted_dogs_by_letter,
                           recent_events=recent_events,
                           rescues=rescues,
                           selected_rescue_id=rescue_id)

@app.route('/dog/<int:dog_id>/note/add', methods=['POST'])
@login_required
def add_dog_note(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    if current_user.role != 'superadmin' and dog.rescue_id != current_user.rescue_id:
        abort(403)
    dog_check = Dog.query.get_or_404(dog_id)
    current_user_id = get_first_user_id()
    if not current_user_id:
        if request.headers.get('HX-Request'):
            response = make_response(render_template('partials/modal_form_error.html', message='Error: Could not identify user for note creation.'), 400)
            response.headers['HX-Retarget'] = '#addDogNoteModalError'
            response.headers['HX-Reswap'] = 'innerHTML'
            return response
        flash('Error: Could not identify user for note creation.', 'danger')
        return redirect(url_for('dog_history', dog_id=dog_id))

    category = request.form.get('category', '').strip()
    note_text = request.form.get('note_text', '').strip()

    # Validation
    error_message = None
    if not category or not note_text:
        error_message = "Category and Note text are required."
    elif len(category) > 100:
        error_message = "Category must be 100 characters or less."
    elif len(note_text) > 2000:
        error_message = "Note text must be 2000 characters or less."

    if error_message:
        if request.headers.get('HX-Request'):
            response = make_response(render_template('partials/modal_form_error.html', message=error_message), 200)
            response.headers['HX-Retarget'] = '#addDogNoteModalError'
            response.headers['HX-Reswap'] = 'innerHTML'
            return response
        else:
            flash(error_message, 'danger')
            return redirect(url_for('dog_history', dog_id=dog_id))

    # Sanitize note_text
    note_text = bleach.clean(note_text)

    new_note = DogNote(
        dog_id=dog_check.id,
        rescue_id=dog_check.rescue_id, 
        user_id=current_user_id,
        category=category,
        note_text=note_text,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_note)
    db.session.commit()

    # After successful submission, re-fetch all history events for the dog using the helper
    dog_for_render, all_history_events_updated = _get_dog_history_events(dog_id)
    page = 1 
    per_page = 50 
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_events_for_partial = all_history_events_updated[start_index:end_index]

    if request.headers.get('HX-Request'):
        return render_template('partials/history_event_list.html', history_events=paginated_events_for_partial, dog=dog_for_render) 
    else:
        flash('Note added successfully!', 'success')
        return redirect(url_for('dog_history', dog_id=dog_id))

@app.route('/api/dog/<int:dog_id>/history_events')
def api_dog_history_events(dog_id):
    """API endpoint for filtered dog history events (Phase 5B functionality)."""
    dog = Dog.query.get_or_404(dog_id)
    
    # Get filter parameters from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    event_types = request.args.getlist('event_types[]')  # Multiple values
    categories = request.args.getlist('categories[]')    # Multiple values
    search_query = request.args.get('search_query', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 25  # Smaller per page for filtered results
    
    # Get all history events
    _, all_history_events = _get_dog_history_events(dog_id)
    
    # Apply filters
    filtered_events = all_history_events
    
    # Date range filter
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            filtered_events = [e for e in filtered_events if e['timestamp'] >= start_dt]
        except ValueError:
            pass  # Ignore invalid date format
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include end day
            filtered_events = [e for e in filtered_events if e['timestamp'] < end_dt]
        except ValueError:
            pass
    
    # Event type filter
    if event_types:
        filtered_events = [e for e in filtered_events if any(et.lower() in e['event_type'].lower() for et in event_types)]
    
    # Category filter (for notes)
    if categories:
        filtered_events = [e for e in filtered_events 
                         if 'Note - ' in e['event_type'] and 
                         any(cat.lower() in e['event_type'].lower() for cat in categories)]
    
    # Search query filter
    if search_query:
        query_lower = search_query.lower()
        filtered_events = [e for e in filtered_events 
                         if query_lower in e['description'].lower() or 
                         query_lower in e['event_type'].lower()]
    
    # Pagination
    total_filtered = len(filtered_events)
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_events = filtered_events[start_index:end_index]
    
    return render_template('partials/history_event_list.html', 
                           history_events=paginated_events,
                           dog=dog,
                           page=page,
                           per_page=per_page,
                           total_events=total_filtered,
                           is_filtered=True)

@app.route('/export/dog_history/<int:dog_id>', methods=['GET'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
def export_dog_history(dog_id):
    dog, all_history_events = _get_dog_history_events(dog_id)
    
    # Create a CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV header
    writer.writerow(['Timestamp', 'Event Type', 'Description', 'Author', 'Source Model', 'Source ID'])
    
    # Write each history event to the CSV file
    for event in all_history_events:
        writer.writerow([event['timestamp'].isoformat(), event['event_type'], event['description'], event['author'], event['source_model'], event['source_id']])
    
    # Get the CSV content
    csv_content = output.getvalue()
    
    # Create a response with the CSV content
    response = make_response(csv_content)
    response.headers['Content-Disposition'] = f'attachment; filename={dog.name}_history.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response

@app.route('/export/medical_summary/<int:dog_id>', methods=['GET'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
def export_medical_summary(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    
    # Create a CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV header
    writer.writerow(['Medicine Name', 'Dosage', 'Unit', 'Form', 'Frequency', 'Start Date', 'End Date', 'Status', 'Notes'])
    
    # Write each medicine to the CSV file
    for med in dog.medicines:
        writer.writerow([
            med.custom_name or (med.preset.name if med.preset else "Unnamed Medicine"),
            med.dosage,
            med.unit,
            med.form,
            med.frequency,
            med.start_date.isoformat() if med.start_date else '',
            med.end_date.isoformat() if med.end_date else '',
            med.status,
            med.notes
        ])
    
    # Get the CSV content
    csv_content = output.getvalue()
    
    # Create a response with the CSV content
    response = make_response(csv_content)
    response.headers['Content-Disposition'] = f'attachment; filename={dog.name}_medical_summary.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response

@app.route('/export/medication_log/<int:dog_id>', methods=['GET'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
def export_medication_log(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    
    # Create a CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV header
    writer.writerow(['Medicine Name', 'Dosage', 'Unit', 'Form', 'Frequency', 'Start Date', 'End Date', 'Status', 'Notes'])
    
    # Write each medicine to the CSV file
    for med in dog.medicines:
        writer.writerow([
            med.custom_name or (med.preset.name if med.preset else "Unnamed Medicine"),
            med.dosage,
            med.unit,
            med.form,
            med.frequency,
            med.start_date.isoformat() if med.start_date else '',
            med.end_date.isoformat() if med.end_date else '',
            med.status,
            med.notes
        ])
    
    # Get the CSV content
    csv_content = output.getvalue()
    
    # Create a response with the CSV content
    response = make_response(csv_content)
    response.headers['Content-Disposition'] = f'attachment; filename={dog.name}_medication_log.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response

@app.route('/export/care_summary/<int:dog_id>', methods=['GET'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
def export_care_summary(dog_id):
    dog, all_history_events = _get_dog_history_events(dog_id)
    
    # Generate a comprehensive text report
    report_lines = []
    report_lines.append(f"COMPREHENSIVE CARE SUMMARY")
    report_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
    report_lines.append("=" * 60)
    report_lines.append("")
    
    # Basic Information
    report_lines.append("BASIC INFORMATION")
    report_lines.append("-" * 20)
    report_lines.append(f"Name: {dog.name}")
    report_lines.append(f"Age: {dog.age or 'Not specified'}")
    report_lines.append(f"Breed: {dog.breed or 'Unknown'}")
    report_lines.append(f"Adoption Status: {dog.adoption_status or 'Not set'}")
    report_lines.append(f"Intake Date: {dog.intake_date.strftime('%Y-%m-%d') if dog.intake_date else 'Not specified'}")
    report_lines.append(f"Microchip ID: {dog.microchip_id or 'Not specified'}")
    if dog.notes:
        report_lines.append(f"General Notes: {dog.notes}")
    if dog.medical_info:
        report_lines.append(f"Medical Information: {dog.medical_info}")
    report_lines.append("")
    
    # Medical History Summary
    report_lines.append("MEDICAL HISTORY SUMMARY")
    report_lines.append("-" * 25)
    if dog.medicines:
        report_lines.append("Current and Past Medications:")
        for med in dog.medicines:
            med_name = med.custom_name or (med.preset.name if med.preset else "Unnamed Medicine")
            report_lines.append(f"  • {med_name}")
            report_lines.append(f"    Dosage: {med.dosage} {med.unit}")
            report_lines.append(f"    Form: {med.form or 'Not specified'}")
            report_lines.append(f"    Frequency: {med.frequency}")
            report_lines.append(f"    Period: {med.start_date} to {med.end_date if med.end_date else 'Ongoing'}")
            report_lines.append(f"    Status: {med.status}")
            if med.notes:
                report_lines.append(f"    Notes: {med.notes}")
            report_lines.append("")
    else:
        report_lines.append("No medication records found.")
        report_lines.append("")
    
    # Appointment History
    report_lines.append("APPOINTMENT HISTORY")
    report_lines.append("-" * 19)
    if dog.appointments:
        for appt in sorted(dog.appointments, key=lambda x: x.start_datetime, reverse=True):
            report_lines.append(f"  • {appt.title or 'Appointment'}")
            report_lines.append(f"    Type: {appt.type.name if appt.type else 'General'}")
            report_lines.append(f"    Date: {appt.start_datetime.strftime('%Y-%m-%d %I:%M %p')}")
            report_lines.append(f"    Status: {appt.status}")
            if appt.description:
                report_lines.append(f"    Notes: {appt.description}")
            report_lines.append("")
    else:
        report_lines.append("No appointment records found.")
        report_lines.append("")
    
    # Care Notes Summary
    care_notes = DogNote.query.filter_by(dog_id=dog_id).order_by(DogNote.timestamp.desc()).all()
    report_lines.append("CARE NOTES SUMMARY")
    report_lines.append("-" * 18)
    if care_notes:
        for note in care_notes[:10]:  # Last 10 notes
            report_lines.append(f"  • [{note.category}] {note.timestamp.strftime('%Y-%m-%d %I:%M %p')}")
            report_lines.append(f"    {note.note_text}")
            report_lines.append(f"    By: {note.user.name if note.user else 'Unknown'}")
            report_lines.append("")
    else:
        report_lines.append("No care notes found.")
        report_lines.append("")
    
    # Summary Statistics
    report_lines.append("CARE STATISTICS")
    report_lines.append("-" * 15)
    report_lines.append(f"Total Appointments: {len(dog.appointments)}")
    report_lines.append(f"Total Medications: {len(dog.medicines)}")
    report_lines.append(f"Total Care Notes: {len(care_notes)}")
    if dog.intake_date:
        days_in_care = (datetime.now().date() - dog.intake_date).days
        report_lines.append(f"Days in Care: {days_in_care}")
    report_lines.append("")
    
    # Footer
    report_lines.append("=" * 60)
    report_lines.append("This report was generated by DogTrackerV2")
    report_lines.append("For questions about this report, contact the rescue organization.")
    
    # Join all lines into a single text
    report_text = "\n".join(report_lines)
    
    # Create a response with the text content
    response = make_response(report_text)
    response.headers['Content-Disposition'] = f'attachment; filename={dog.name}_care_summary.txt'
    response.headers['Content-Type'] = 'text/plain'
    
    return response

def get_current_user():
    """Get current authenticated user or None if not authenticated."""
    if current_user.is_authenticated:
        return current_user
    return None

@app.route('/admin/audit-logs', methods=['GET', 'POST'])
@roles_required(['superadmin', 'owner'])
def admin_audit_logs():
    current_user = get_current_user()
    page = int(request.args.get('page', 1))
    per_page = 25
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    audit_stats = get_audit_system_stats() if current_user.role == 'superadmin' else None
    flush_form = AuditForm()
    cleanup_form = AuditForm()
    return render_template('admin_audit_logs.html', logs=logs, current_user=current_user, audit_stats=audit_stats, flush_form=flush_form, cleanup_form=cleanup_form)

@app.route('/admin/flush-audit-batch', methods=['POST'])
@role_required('superadmin')
def admin_flush_audit_batch():
    print(f"[CSRF DEBUG /admin/flush-audit-batch] Session CSRF Token: {session.get('_csrf_token')}")
    print(f"[CSRF DEBUG /admin/flush-audit-batch] Form CSRF Token: {request.form.get('csrf_token')}")
    current_user = get_current_user()
    # Force flush the audit batch queue
    flushed = False
    if hasattr(_audit_batcher, 'queue'):
        batch = []
        while not _audit_batcher.queue.empty():
            batch.append(_audit_batcher.queue.get())
        if batch:
            _audit_batcher._flush(batch)
            flushed = True
    flash('Audit batch flushed.' if flushed else 'No events to flush.', 'info')
    return redirect(url_for('admin_audit_logs'))

@app.route('/admin/run-audit-cleanup', methods=['POST'])
@login_required
@role_required('superadmin')
def admin_run_audit_cleanup():
    audit_action = request.form.get('audit_action')
    if audit_action == 'cleanup':
        cleanup_old_audit_logs()
        flash('Audit logs cleanup initiated.', 'success')
    return redirect(url_for('admin_audit_logs'))

@app.route('/staff-management')
@login_required
def staff_management():
    # Only show users for the current rescue, unless superadmin
    if current_user.role == 'superadmin':
        staff_users = User.query.order_by(User.rescue_id, User.role, User.name).all()
    else:
        staff_users = User.query.filter_by(rescue_id=current_user.rescue_id).order_by(User.role, User.name).all()
    # Sort by role (owner, admin, staff) then by name
    role_order = {'owner': 0, 'admin': 1, 'staff': 2}
    staff_users = sorted(staff_users, key=lambda u: (role_order.get(u.role, 99), u.name.lower()))
    
    # Pass rescues data if superadmin
    if current_user.role == 'superadmin':
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        return render_template('staff_management.html', staff_users=staff_users, rescues=rescues)
    else:
        return render_template('staff_management.html', staff_users=staff_users)

@app.route('/rescue-info')
@login_required
def rescue_info():
    print('--- Rescue Info Debug ---')
    print(f'User role: {current_user.role}')
    print(f'Request args: {dict(request.args)}')
    
    if current_user.role == 'superadmin':
        rescue_id = request.args.get('rescue_id', type=int)
        print(f'rescue_id from request: {rescue_id}')
        selected_rescue_id = rescue_id
        if rescue_id:
            rescue = Rescue.query.get_or_404(rescue_id)
            print(f'Found rescue: {rescue.name} (ID: {rescue.id})')
        else:
            print('No rescue_id provided')
            rescue = None
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        print(f'Total rescues available: {len(rescues)}')
        return render_template('rescue_info.html', rescue=rescue, rescues=rescues, selected_rescue_id=selected_rescue_id)
    else:
        rescue = current_user.rescue
        print(f'Regular user rescue: {rescue.name if rescue else "None"}')
        return render_template('rescue_info.html', rescue=rescue)

# Phase R4B: Appointment list and details routes migrated to blueprints/appointments/routes.py

# Moved to blueprints/medicines/routes.py in Phase R4C-1

# Moved to blueprints/medicines/routes.py in Phase R4C-1

# Moved to blueprints/medicines/routes.py in Phase R4C-1

# Moved to blueprints/medicines/routes.py in Phase R4C-1

# Moved to blueprints/medicines/routes.py in Phase R4C-1

@app.route('/staff-management/add', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def add_staff_member():
    from models import User
    import bleach
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    role = request.form.get('role', '').strip().lower()
    # Length validation and sanitization for name
    if not name or len(name) < 2 or len(name) > 120:
        return jsonify({'success': False, 'error': 'Name must be between 2 and 120 characters.'}), 400
    name = bleach.clean(name)
    if not email or role not in ['owner', 'admin', 'staff']:
        return jsonify({'success': False, 'error': 'Invalid input.'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Email already exists.'}), 400
    # Only superadmin can add users to any rescue; others only to their own
    rescue_id = current_user.rescue_id if current_user.role != 'superadmin' else request.form.get('rescue_id')
    if current_user.role != 'superadmin' and not rescue_id:
        return jsonify({'success': False, 'error': 'Rescue not specified.'}), 400
    # Validate rescue_id for superadmins
    if current_user.role == 'superadmin' and not rescue_id:
        return jsonify({'success': False, 'error': 'Please select a rescue for this staff member.'}), 400
    password = secrets.token_urlsafe(8)
    user = User(
        name=name,
        email=email,
        role=role,
        is_active=True,
        email_verified=False,
        rescue_id=rescue_id
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'name': name, 'email': email, 'role': role, 'password': password})

@app.route('/staff-management/edit', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def edit_staff_member():
    from models import User
    import bleach
    user_id = request.form.get('user_id')
    name = request.form.get('name', '').strip()
    role = request.form.get('role', '').strip().lower()
    is_active = request.form.get('is_active') == 'true'
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    # Only superadmin can edit any user; others only users in their rescue
    if current_user.role != 'superadmin' and user.rescue_id != current_user.rescue_id:
        return jsonify({'success': False, 'error': 'Permission denied.'}), 403
    # Length validation and sanitization for name
    if not name or len(name) < 2 or len(name) > 120:
        return jsonify({'success': False, 'error': 'Name must be between 2 and 120 characters.'}), 400
    name = bleach.clean(name)
    if role not in ['owner', 'admin', 'staff']:
        return jsonify({'success': False, 'error': 'Invalid input.'}), 400
    user.name = name
    user.role = role
    user.is_active = is_active
    db.session.commit()
    return jsonify({'success': True, 'name': name, 'role': role, 'is_active': is_active})

@app.route('/staff-management/toggle-active', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def toggle_staff_active():
    from models import User
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    # Only superadmin can toggle any user; others only users in their rescue
    if current_user.role != 'superadmin' and user.rescue_id != current_user.rescue_id:
        return jsonify({'success': False, 'error': 'Permission denied.'}), 403
    if user.id == current_user.id or user.role == 'superadmin':
        return jsonify({'success': False, 'error': 'Cannot toggle this user.'}), 403
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': user.is_active})

@app.route('/staff-management/delete', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def delete_staff_member():
    from models import User
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    if current_user.role != 'superadmin' and user.rescue_id != current_user.rescue_id:
        return jsonify({'success': False, 'error': 'Permission denied.'}), 403
    if user.id == current_user.id or user.role == 'superadmin':
        return jsonify({'success': False, 'error': 'Cannot delete this user.'}), 403
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/staff-management/reset-password', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def reset_staff_password():
    from models import User
    import secrets
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    if current_user.role != 'superadmin' and user.rescue_id != current_user.rescue_id:
        return jsonify({'success': False, 'error': 'Permission denied.'}), 403
    if user.id == current_user.id or user.role == 'superadmin':
        return jsonify({'success': False, 'error': 'Cannot reset password for this user.'}), 403
    new_password = secrets.token_urlsafe(8)
    user.set_password(new_password)
    db.session.commit()
    return jsonify({'success': True, 'password': new_password})

@app.before_request
def generate_csp_nonce():
    g.csp_nonce = secrets.token_hex(16)

# CSRF Error handler moved to blueprints/core/errors.py
# @app.errorhandler(CSRFError)
# def handle_csrf_error(e):

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    nonce = getattr(g, 'csp_nonce', None)
    if nonce:
        csp_policy = (
            "default-src 'self'; "
            f"script-src 'self' https://cdn.jsdelivr.net https://unpkg.com 'nonce-{nonce}'; "
            f"style-src 'self' https://cdn.jsdelivr.net 'nonce-{nonce}'; "  # Apply nonce to styles too
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:;"
        )
    else:
        # Fallback CSP if nonce is not available (should not happen in normal flow)
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:;"
        )
    response.headers['Content-Security-Policy'] = csp_policy

    # Consider adding Permissions-Policy if you want to restrict browser features
    # response.headers['Permissions-Policy'] = "geolocation=(), microphone=(), camera=()"
    return response

# Rate limit error handler moved to blueprints/core/errors.py
# @app.errorhandler(429)
# def ratelimit_handler(e):

# @app.route('/verify-email/<token>')
# def verify_email(token):
#     user = User.query.filter_by(email_verification_token=token).first()
#     if not user:
#         flash('Invalid or expired verification link.', 'danger')
#         return redirect(url_for('login'))
#     user.email_verified = True
#     user.email_verification_token = None
#     db.session.commit()
#     return render_template('auth/email_verified.html')

# 404 and 500 error handlers moved to blueprints/core/errors.py
# @app.errorhandler(404)
# def not_found_error(error):
# @app.errorhandler(500)
# def internal_error(error):

@app.route('/test-minimal-form', methods=['GET'])
def show_minimal_test_form():
    # Ensure CSRF token is available for the template
    return render_template('minimal_form_test.html')

@app.route('/receive-test-form', methods=['POST'])
@csrf.exempt
def receive_test_form():
    print(f"[RECEIVE_TEST_FORM] request.form content: {request.form}")
    return "Test form data received. Check console.", 200

if __name__ == '__main__':
    print('--- ROUTES REGISTERED ---')
    for rule in app.url_map.iter_rules():
        print(rule, rule.methods)
    print('-------------------------')
    app.run(debug=True, host='0.0.0.0') 