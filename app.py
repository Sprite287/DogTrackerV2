from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, render_template_string, get_flashed_messages, make_response, send_file, abort
import os
from extensions import db, migrate, login_manager
import json
from models import Dog, AppointmentType, MedicinePreset, Appointment, DogMedicine, Reminder, User, DogNote, Rescue, AuditLog
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import joinedload
import csv
import io
from werkzeug.utils import secure_filename
from audit import log_audit_event, AuditCleanupThread, get_audit_system_stats, _audit_batcher, cleanup_old_audit_logs
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm, RegistrationForm, RescueRegistrationForm, PasswordResetRequestForm, PasswordResetForm

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://doguser:dogpassword@localhost:5432/dogtracker')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')

# Development settings to prevent caching issues
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

db.init_app(app)
migrate.init_app(app, db)

# Initialize Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def _get_dog_history_events(dog_id):
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
            'event_type': 'Dog Record', 'description': f'{dog.name} was taken into care.',
            'author': 'System', 'source_model': 'Dog', 'source_id': dog.id
        })
    # 2. DogNote Events
    for note in care_notes:
        history_events.append({
            'timestamp': note.timestamp, 'event_type': f'Note - {note.category}',
            'description': note.note_text, 'author': note.user.name if note.user else 'Unknown User',
            'source_model': 'DogNote', 'source_id': note.id
        })
    # 3. Appointment Events
    for appt in dog.appointments:
        history_events.append({
            'timestamp': appt.created_at,
            'event_type': f'Appointment - {appt.type.name if appt.type else "General"}',
            'description': f'Appointment "{appt.title}" scheduled for {appt.start_datetime.strftime("%Y-%m-%d %I:%M %p")}. Status: {appt.status}.',
            'author': appt.creator.name if appt.creator else 'System/Unknown', 'source_model': 'Appointment', 'source_id': appt.id
        })
        if appt.updated_at and appt.updated_at != appt.created_at:
            history_events.append({
                'timestamp': appt.updated_at, 'event_type': f'Appointment Update - {appt.type.name if appt.type else "General"}',
                'description': f'Details for appointment "{appt.title}" were updated. New Status: {appt.status}.',
                'author': 'System/Unknown', 'source_model': 'Appointment', 'source_id': appt.id
            })
    # 4. DogMedicine Events
    for med in dog.medicines:
        med_name = med.custom_name or (med.preset.name if med.preset else "Unnamed Medicine")
        history_events.append({
            'timestamp': datetime.combine(med.start_date, datetime.min.time()),
            'event_type': f'Medication - {med_name}',
            'description': f'Started medication: {med_name}. Dosage: {med.dosage} {med.unit}, Frequency: {med.frequency}. Status: {med.status}.',
            'author': med.creator.name if med.creator else 'System/Unknown', 'source_model': 'DogMedicine', 'source_id': med.id
        })
        if med.end_date:
            history_events.append({
                'timestamp': datetime.combine(med.end_date, datetime.max.time() - timedelta(seconds=1)),
                'event_type': f'Medication Ended - {med_name}',
                'description': f'Ended medication: {med_name}.',
                'author': med.creator.name if med.creator else 'System/Unknown', 'source_model': 'DogMedicine', 'source_id': med.id
            })
        if med.created_at.date() != med.start_date and med.created_at < datetime.combine(med.start_date, datetime.min.time()):
            history_events.append({
                'timestamp': med.created_at, 'event_type': f'Medication Logged - {med_name}',
                'description': f'Medication record for {med_name} was created/updated.',
                'author': med.creator.name if med.creator else 'System/Unknown', 'source_model': 'DogMedicine', 'source_id': med.id
            })
    # 5. Reminder Events
    for reminder in dog.reminders:
        history_events.append({
            'timestamp': reminder.created_at, 'event_type': 'Reminder Created',
            'description': f'Reminder set: "{reminder.message}" due {reminder.due_datetime.strftime("%Y-%m-%d %I:%M %p")}',
            'author': reminder.user.name if reminder.user else 'System', 'source_model': 'Reminder', 'source_id': reminder.id
        })
        if reminder.status == 'acknowledged' or reminder.status == 'dismissed':
            status_change_time = reminder.updated_at
            history_events.append({
                'timestamp': status_change_time, 'event_type': f'Reminder {reminder.status.title()}',
                'description': f'Reminder "{reminder.message}" was {reminder.status}.',
                'author': reminder.user.name if reminder.user else 'System', 'source_model': 'Reminder', 'source_id': reminder.id
            })
    history_events.sort(key=lambda x: x['timestamp'], reverse=True)
    return dog, history_events

def get_first_user_id():
    """Helper to get the ID of the first available user, or None."""
    first_user = User.query.order_by(User.id.asc()).first()
    if first_user:
        return first_user.id
    print("WARNING: No users found in the database. 'created_by' fields will be None.")
    return None # Or raise an error, or handle as per application requirements

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

def render_dog_cards():
    if current_user.is_authenticated:
        dogs = Dog.query.filter_by(rescue_id=current_user.rescue_id).order_by(Dog.name.asc()).all()
    else:
        dogs = []
    return render_template('dog_cards.html', dogs=dogs)

def render_alert(message, category='success'):
    return render_template_string('<div class="alert alert-{{ category }} alert-dismissible fade show" role="alert" hx-swap-oob="true">{{ message }}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>', message=message, category=category)

@app.route('/')
def home_redirect():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)
            
            # Check if user's rescue is approved (unless superadmin)
            if not user.is_superadmin() and user.rescue and user.rescue.status != 'approved':
                flash('Your rescue organization is still pending approval. Please wait for admin approval.', 'warning')
                return render_template('auth/login.html', form=form)
            
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log successful login
            log_audit_event(
                user_id=user.id,
                rescue_id=user.rescue_id,
                action='login_success',
                resource_type='User',
                resource_id=user.id,
                details={'email': user.email},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=True
            )
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
        else:
            # Log failed login attempt
            log_audit_event(
                user_id=None,
                rescue_id=None,
                action='login_failed',
                resource_type='User',
                resource_id=None,
                details={'email': form.email.data, 'reason': 'invalid_credentials'},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=False
            )
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    # Log logout
    log_audit_event(
        user_id=current_user.id,
        rescue_id=current_user.rescue_id,
        action='logout',
        resource_type='User',
        resource_id=current_user.id,
        details={'email': current_user.email},
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # This is for individual user registration (not rescue registration)
        # For now, redirect to rescue registration
        flash('Please register your rescue organization first.', 'info')
        return redirect(url_for('register_rescue'))
    
    return render_template('auth/register.html', form=form)

@app.route('/register-rescue', methods=['GET', 'POST'])
def register_rescue():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RescueRegistrationForm()
    if form.validate_on_submit():
        # Create rescue
        rescue = Rescue(
            name=form.rescue_name.data,
            address=form.rescue_address.data,
            phone=form.rescue_phone.data,
            email=form.rescue_email.data,
            primary_contact_name=form.contact_name.data,
            primary_contact_email=form.contact_email.data,
            primary_contact_phone=form.contact_phone.data,
            data_consent=form.data_consent.data,
            marketing_consent=form.marketing_consent.data,
            status='pending'  # Requires admin approval
        )
        db.session.add(rescue)
        db.session.flush()  # Get the rescue ID
        
        # Create first user (admin of the rescue)
        user = User(
            name=form.contact_name.data,
            email=form.contact_email.data,
            role='admin',
            rescue_id=rescue.id,
            is_first_user=True,
            email_verified=False,  # Will need email verification
            data_consent=form.data_consent.data,
            marketing_consent=form.marketing_consent.data
        )
        user.set_password(form.contact_password.data)
        user.generate_email_verification_token()
        
        db.session.add(user)
        db.session.commit()
        
        # Log rescue registration
        log_audit_event(
            user_id=user.id,
            rescue_id=rescue.id,
            action='rescue_registration',
            resource_type='Rescue',
            resource_id=rescue.id,
            details={
                'rescue_name': rescue.name,
                'primary_contact_email': rescue.primary_contact_email,
                'status': rescue.status
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=True
        )
        
        flash('Rescue registration submitted successfully! Your registration is pending admin approval. You will receive an email once approved.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register_rescue.html', form=form)

@app.route('/password-reset-request', methods=['GET', 'POST'])
def password_reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_password_reset_token()
            db.session.commit()
            
            # Log password reset request
            log_audit_event(
                user_id=user.id,
                rescue_id=user.rescue_id,
                action='password_reset_request',
                resource_type='User',
                resource_id=user.id,
                details={'email': user.email},
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=True
            )
            
            # TODO: Send email with reset link
            # For now, just show a message
            flash(f'Password reset instructions have been sent to {form.email.data}. (Note: Email functionality not yet implemented)', 'info')
        else:
            # Don't reveal if email exists or not for security
            flash(f'If an account with email {form.email.data} exists, password reset instructions have been sent.', 'info')
        
        return redirect(url_for('login'))
    
    return render_template('auth/password_reset_request.html', form=form)

@app.route('/password-reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    user = User.query.filter_by(password_reset_token=token).first()
    if not user or not user.verify_password_reset_token(token):
        flash('Invalid or expired password reset token.', 'danger')
        return redirect(url_for('login'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()
        
        # Log successful password reset
        log_audit_event(
            user_id=user.id,
            rescue_id=user.rescue_id,
            action='password_reset_success',
            resource_type='User',
            resource_id=user.id,
            details={'email': user.email},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            success=True
        )
        
        flash('Your password has been reset successfully. You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/password_reset.html', form=form)

@app.route('/dogs')
@login_required
def dog_list_page():
    if current_user.role == 'superadmin':
        rescue_id = request.args.get('rescue_id', type=int)
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        if rescue_id:
            dogs = Dog.query.filter_by(rescue_id=rescue_id).order_by(Dog.name.asc()).all()
        else:
            dogs = Dog.query.order_by(Dog.name.asc()).all()
        return render_template('index.html', dogs=dogs, rescues=rescues, selected_rescue_id=rescue_id)
    else:
        dogs = Dog.query.filter_by(rescue_id=current_user.rescue_id).order_by(Dog.name.asc()).all()
        return render_template('index.html', dogs=dogs)

def render_dog_cards_html():
    if current_user.is_authenticated:
        dogs = Dog.query.filter_by(rescue_id=current_user.rescue_id).order_by(Dog.name.asc()).all()
    else:
        dogs = []
    return render_template('dog_cards.html', dogs=dogs)

@app.route('/dog/add', methods=['POST'])
@login_required
def add_dog():
    name = request.form.get('name')
    if not name:
        if request.headers.get('HX-Request'):
            cards = render_dog_cards_html()
            resp = make_response(cards)
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog name is required.", "category": "danger"}})
            return resp
        flash('Dog name is required.', 'danger')
        return redirect(url_for('dog_list_page'))
    age = request.form.get('age')
    breed = request.form.get('breed')
    adoption_status = request.form.get('adoption_status')
    intake_date = request.form.get('intake_date')
    if not intake_date:
        intake_date = None
    microchip_id = request.form.get('microchip_id')
    notes = request.form.get('notes')
    medical_info = request.form.get('medical_info')
    # Use current user's rescue_id
    rescue_id = current_user.rescue_id
    dog = Dog(name=name, age=age, breed=breed, adoption_status=adoption_status,
              intake_date=intake_date, microchip_id=microchip_id, notes=notes,
              medical_info=medical_info, rescue_id=rescue_id)
    db.session.add(dog)
    db.session.commit()
    # --- AUDIT LOG ---
    log_audit_event(
        user_id=current_user.id,
        rescue_id=dog.rescue_id,
        action='create',
        resource_type='Dog',
        resource_id=dog.id,
        details={
            'name': dog.name,
            'age': dog.age,
            'breed': dog.breed,
            'adoption_status': dog.adoption_status,
            'intake_date': str(dog.intake_date),
            'microchip_id': dog.microchip_id
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    if request.headers.get('HX-Request'):
        cards = render_dog_cards_html()
        resp = make_response(cards)
        resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog added successfully!", "category": "success"}})
        return resp
    flash('Dog added successfully!', 'success')
    return redirect(url_for('dog_list_page'))

@app.route('/dog/edit', methods=['POST'])
@login_required
def edit_dog():
    dog_id = request.form.get('dog_id')
    dog = Dog.query.get_or_404(dog_id)
    name = request.form.get('name')
    if not name:
        if request.headers.get('HX-Request'):
            cards = render_dog_cards_html()
            resp = make_response(cards)
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog name is required.", "category": "danger"}})
            return resp
        flash('Dog name is required.', 'danger')
        return redirect(request.referrer or url_for('dog_list_page'))
    dog.name = name
    dog.age = request.form.get('age')
    dog.breed = request.form.get('breed')
    dog.adoption_status = request.form.get('adoption_status')
    dog.intake_date = request.form.get('intake_date')
    if not dog.intake_date:
        dog.intake_date = None
    dog.microchip_id = request.form.get('microchip_id')
    dog.notes = request.form.get('notes')
    dog.medical_info = request.form.get('medical_info')
    db.session.commit()
    # --- AUDIT LOG ---
    log_audit_event(
        user_id=current_user.id,
        rescue_id=dog.rescue_id,
        action='edit',
        resource_type='Dog',
        resource_id=dog.id,
        details={
            'name': dog.name,
            'age': dog.age,
            'breed': dog.breed,
            'adoption_status': dog.adoption_status,
            'intake_date': str(dog.intake_date),
            'microchip_id': dog.microchip_id
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    if request.headers.get('HX-Request'):
        if request.form.get('from_details') == 'details':
            from flask import make_response, request as flask_request
            flash('Dog updated successfully!', 'success')
            resp = make_response('')
            resp.headers['HX-Redirect'] = flask_request.referrer or '/'
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog updated successfully!", "category": "success"}})
            return resp
        cards = render_dog_cards_html()
        resp = make_response(cards)
        resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog updated successfully!", "category": "success"}})
        return resp
    flash('Dog updated successfully!', 'success')
    return redirect(url_for('dog_list_page'))

@app.route('/dog/<int:dog_id>/delete', methods=['POST'])
@login_required
def delete_dog(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    db.session.delete(dog)
    db.session.commit()
    # --- AUDIT LOG ---
    log_audit_event(
        user_id=current_user.id,
        rescue_id=dog.rescue_id,
        action='delete',
        resource_type='Dog',
        resource_id=dog.id,
        details={
            'name': dog.name,
            'age': dog.age,
            'breed': dog.breed,
            'adoption_status': dog.adoption_status,
            'intake_date': str(dog.intake_date),
            'microchip_id': dog.microchip_id
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    if request.headers.get('HX-Request'):
        cards = render_dog_cards_html()
        resp = make_response(cards)
        resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog deleted successfully!", "category": "success"}})
        return resp
    flash('Dog deleted successfully!', 'success')
    return redirect(url_for('dog_list_page'))



@app.route('/dog/<int:dog_id>')
@login_required
def dog_details(dog_id):
    dog = Dog.query.get_or_404(dog_id)

    # Fetch and prepare appointment types ensuring unique names, sorted
    appointment_types_db = AppointmentType.query.filter_by(rescue_id=dog.rescue_id).order_by(AppointmentType.name).all()
    unique_appointment_types_dict = {}
    for t in appointment_types_db:
        if t.name not in unique_appointment_types_dict: # Keep first encountered based on initial sort
            unique_appointment_types_dict[t.name] = {"id": t.id, "name": t.name}
    appointment_types_json = sorted(list(unique_appointment_types_dict.values()), key=lambda x: x['name'])

    # Fetch and prepare medicine presets, grouped by category, and sorted
    all_medicine_presets_db = MedicinePreset.query.filter(
        (MedicinePreset.rescue_id == dog.rescue_id) | (MedicinePreset.rescue_id == None)
    ).order_by(MedicinePreset.category, MedicinePreset.name).all()

    categorized_medicine_presets = defaultdict(list)
    # Prioritize rescue-specific if names clash, then by original sort order (category, name)
    # This step also dedupes based on name across global/rescue-specific
    temp_deduped_presets_by_name = {}
    rescue_specific_presets = [p for p in all_medicine_presets_db if p.rescue_id == dog.rescue_id]
    global_presets = [p for p in all_medicine_presets_db if p.rescue_id == None]

    for preset in rescue_specific_presets:
        temp_deduped_presets_by_name[preset.name] = preset
    for preset in global_presets:
        if preset.name not in temp_deduped_presets_by_name:
            temp_deduped_presets_by_name[preset.name] = preset
    
    # Now group the deduped and prioritized list by category
    final_sorted_presets = sorted(temp_deduped_presets_by_name.values(), key=lambda p: (p.category or "Uncategorized", p.name))

    for preset in final_sorted_presets:
        category_name = preset.category if preset.category else "Uncategorized"
        categorized_medicine_presets[category_name].append({
            "id": preset.id,
            "name": preset.name,
            "suggested_units": preset.suggested_units, # Comma-separated string
            "default_dosage_instructions": preset.default_dosage_instructions
        })
    
    # Sort the categories themselves for ordered display in the template
    # Convert defaultdict to dict for easier iteration in Jinja if preferred, and sort by category name
    sorted_categorized_medicine_presets = dict(sorted(categorized_medicine_presets.items()))

    # Phase 5B: Get recent history events for the Recent Activity widget
    _, all_history_events = _get_dog_history_events(dog_id)
    recent_history_events = all_history_events[:5]  # Last 5 events for the widget

    return render_template('dog_details.html', 
                           dog=dog, 
                           appointment_types=appointment_types_json, 
                           medicine_presets_categorized=sorted_categorized_medicine_presets,
                           recent_history_events=recent_history_events)

@app.cli.command('list-routes')
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods))
        line = urllib.parse.unquote(f"{rule.endpoint:30s} {methods:20s} {rule}")
        output.append(line)
    for line in sorted(output):
        print(line)

# --- Appointments CRUD ---
@app.route('/dog/<int:dog_id>/appointment/add', methods=['POST'])
@login_required
def add_appointment(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    print(f"[ADD APPT DEBUG] Form data: {request.form}") # Debug form data

    appt_type_id = request.form.get('appt_type_id')
    appt_start_datetime = request.form.get('appt_start_datetime')
    appt_end_datetime = request.form.get('appt_end_datetime')

    if not appt_type_id:
        error_message = 'Appointment type is required.'
        print(f"[ADD APPT DEBUG] Validation Error: {error_message}")
        response = make_response(render_template('partials/modal_form_error.html', message=error_message))
        response.status_code = 400
        response.headers['HX-Retarget'] = '#addAppointmentModalError'
        response.headers['HX-Reswap'] = 'innerHTML'
        return response

    if not appt_start_datetime:
        error_message = 'Start date/time is required.'
        print(f"[ADD APPT DEBUG] Validation Error: {error_message}")
        response = make_response(render_template('partials/modal_form_error.html', message=error_message))
        response.status_code = 400
        response.headers['HX-Retarget'] = '#addAppointmentModalError'
        response.headers['HX-Reswap'] = 'innerHTML'
        return response
    
    try:
        start_dt = datetime.strptime(appt_start_datetime, '%Y-%m-%dT%H:%M')
    except ValueError:
        error_message = 'Invalid start date/time format.'
        print(f"[ADD APPT DEBUG] Validation Error: {error_message}")
        response = make_response(render_template('partials/modal_form_error.html', message=error_message))
        response.status_code = 400
        response.headers['HX-Retarget'] = '#addAppointmentModalError'
        response.headers['HX-Reswap'] = 'innerHTML'
        return response

    end_dt = None
    if appt_end_datetime:
        try:
            end_dt = datetime.strptime(appt_end_datetime, '%Y-%m-%dT%H:%M')
        except ValueError:
            error_message = 'Invalid end date/time format.'
            print(f"[ADD APPT DEBUG] Validation Error: {error_message}") # Corrected this error return
            response = make_response(render_template('partials/modal_form_error.html', message=error_message))
            response.status_code = 400
            response.headers['HX-Retarget'] = '#addAppointmentModalError'
            response.headers['HX-Reswap'] = 'innerHTML'
            return response
    
    temp_user_id = get_first_user_id()
    if temp_user_id is None:
        flash('Cannot create appointment: No users found in the system.', 'danger')
        return redirect(url_for('dog_details', dog_id=dog_id))

    appt = Appointment(
        dog_id=dog.id,
        rescue_id=dog.rescue_id,
        type_id=int(appt_type_id) if appt_type_id else None,
        title=request.form.get('appt_title'),
        description=request.form.get('appt_notes'),
        start_datetime=start_dt,
        end_datetime=end_dt,
        status=request.form.get('appt_status'),
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
    return render_template('partials/appointments_list.html', dog=dog, appointment_types=appointment_types)

@app.route('/dog/<int:dog_id>/appointment/edit/<int:appointment_id>', methods=['POST'])
def edit_appointment(dog_id, appointment_id):
    print('--- Edit Appointment Debug ---')
    print('dog_id:', dog_id)
    print('appointment_id:', appointment_id)
    print('Form data:', dict(request.form))
    dog = Dog.query.get_or_404(dog_id)
    appt = Appointment.query.get_or_404(appointment_id)
    
    # Store old start_datetime to check if it changed for reminder regeneration
    old_start_datetime = appt.start_datetime 

    # Update appointment fields from form
    appt.type_id = int(request.form.get('appt_type_id')) if request.form.get('appt_type_id') else None
    appt.title = request.form.get('appt_title')
    appt.description = request.form.get('appt_notes')
    appt.status = request.form.get('appt_status')
    appt_start_datetime = request.form.get('appt_start_datetime')
    appt_end_datetime = request.form.get('appt_end_datetime')
    if appt_start_datetime:
        appt.start_datetime = datetime.strptime(appt_start_datetime, '%Y-%m-%dT%H:%M')
    if appt_end_datetime:
        appt.end_datetime = datetime.strptime(appt_end_datetime, '%Y-%m-%dT%H:%M')
    
    temp_user_id = get_first_user_id()
    if temp_user_id is None:
        flash('Cannot update appointment/reminders: No users found.', 'danger')
        return redirect(url_for('dog_details', dog_id=dog_id))

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
    return render_template('partials/appointments_list.html', dog=dog, appointment_types=appointment_types)

@app.route('/dog/<int:dog_id>/appointment/delete/<int:appointment_id>', methods=['POST'])
def delete_appointment(dog_id, appointment_id):
    dog = Dog.query.get_or_404(dog_id)
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
    return render_template('partials/appointments_list.html', dog=dog, appointment_types=appointment_types)

# --- Medicines CRUD ---
@app.route('/dog/<int:dog_id>/medicine/add', methods=['POST'])
def add_medicine(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    med_preset_id_str = request.form.get('med_preset_id')
    med_dosage = request.form.get('med_dosage')
    med_unit = request.form.get('med_unit')
    med_form = request.form.get('med_form')
    med_frequency = request.form.get('med_frequency')
    med_start_date_str = request.form.get('med_start_date')
    med_end_date_str = request.form.get('med_end_date')
    med_status = request.form.get('med_status')
    med_notes = request.form.get('med_notes')

    error_message = None
    start_date = None
    end_date = None

    if not med_start_date_str:
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
    
    temp_user_id = get_first_user_id()
    if temp_user_id is None:
        # This case is a more systemic issue, flash message and redirect might be okay
        # or could also be an HTMX response if the whole page context allows for it.
        # For now, keeping flash for this rarer case.
        flash('Cannot add medicine: No users found in the system.', 'danger')
        # If HTMX request, perhaps return an OOB flash message instead of full redirect render
        if request.headers.get('HX-Request'):
             # Simplified: just trigger an alert for now if HX, actual OOB flash more complex
            alert_resp = make_response('') # Empty response, HX-Trigger does the work
            alert_resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Cannot add medicine: No users found.", "category": "danger"}})
            return alert_resp, 200 # 200 so HTMX processes the trigger, not an error
        return redirect(url_for('dog_details', dog_id=dog_id))

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
        medicine_id=final_preset_id, # This is the FK to medicine_preset
        custom_name=None, # Explicitly None
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

    # Reminder Generation for Medicine Start
    if med.start_date:
        try:
            # Create a datetime object for the reminder, e.g., at 9 AM on the start date
            reminder_due_dt = datetime.combine(med.start_date, datetime.min.time()) + timedelta(hours=9)
            
            medicine_name = med.custom_name
            if not medicine_name and med.medicine_id:
                preset = MedicinePreset.query.get(med.medicine_id)
                if preset:
                    medicine_name = preset.name
            if not medicine_name:
                medicine_name = "Medicine"

            reminder_message = f"{dog.name}'s prescription for '{medicine_name}' is scheduled to start on {med.start_date.strftime('%Y-%m-%d')}."
            
            start_reminder = Reminder(
                message=reminder_message,
                due_datetime=reminder_due_dt,
                status='pending',
                reminder_type='medicine_start',
                dog_id=dog.id,
                dog_medicine_id=med.id,
                user_id=temp_user_id
            )
            db.session.add(start_reminder)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error creating reminder for medicine start: {e}")

    dog = Dog.query.get_or_404(dog_id)
    medicine_presets_data = MedicinePreset.query.filter(
        (MedicinePreset.rescue_id == dog.rescue_id) | (MedicinePreset.rescue_id == None)
    ).all()
    return render_template('partials/medicines_list.html', dog=dog, medicine_presets=medicine_presets_data)

@app.route('/dog/<int:dog_id>/medicine/edit/<int:medicine_id>', methods=['POST'])
def edit_medicine(dog_id, medicine_id):
    dog = Dog.query.get_or_404(dog_id)
    med = DogMedicine.query.get_or_404(medicine_id)

    old_start_date = med.start_date

    # Get data from form
    med_preset_id_str = request.form.get('med_preset_id')
    med_dosage = request.form.get('med_dosage')
    med_unit = request.form.get('med_unit')
    med_form = request.form.get('med_form')
    med_frequency = request.form.get('med_frequency')
    med_start_date_str = request.form.get('med_start_date')
    med_end_date_str = request.form.get('med_end_date')
    med_status = request.form.get('med_status')
    med_notes = request.form.get('med_notes')

    error_message = None
    start_date = None
    end_date = None

    if not med_start_date_str:
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
        response.status_code = 200 # Keep 200 for HTMX to process swap
        response.headers['HX-Retarget'] = '#editMedicineModalError'
        response.headers['HX-Reswap'] = 'innerHTML'
        return response

    temp_user_id = get_first_user_id()
    if temp_user_id is None:
        flash('Cannot edit medicine: No users found in the system.', 'danger')
        return redirect(url_for('dog_details', dog_id=dog_id))

    # Update medicine object properties
    med.medicine_id = int(med_preset_id_str) if med_preset_id_str else None
    med.custom_name = None # If using preset, custom_name is typically nullified.
                           # UI should handle if custom name is allowed when no preset or a specific "custom" preset is chosen.
                           # For now, aligning with add_medicine where custom_name is set to None if preset is used.
    med.dosage = med_dosage
    med.unit = med_unit
    med.form = med_form
    med.frequency = med_frequency
    med.start_date = start_date
    med.end_date = end_date
    med.status = med_status
    med.notes = med_notes
    
    db.session.commit()
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

    # Reminder Generation/Update Logic for Medicine Start
    # Regenerate if start_date changed or for simplicity, always (current condition `or True`)
    if med.start_date and (med.start_date != old_start_date or True):
        try:
            # Delete existing reminders for this medicine instance
            Reminder.query.filter_by(dog_medicine_id=med.id).delete()

            # Create new reminder for the start date
            reminder_due_dt = datetime.combine(med.start_date, datetime.min.time()) + timedelta(hours=9)
            
            medicine_name = med.custom_name # Will be None if preset was chosen above
            if not medicine_name and med.medicine_id:
                preset = MedicinePreset.query.get(med.medicine_id)
                if preset:
                    medicine_name = preset.name
            if not medicine_name: # Fallback if still no name
                medicine_name = "Medicine"

            reminder_message = f"{dog.name}'s prescription for '{medicine_name}' is scheduled to start on {med.start_date.strftime('%Y-%m-%d')}."
            
            updated_start_reminder = Reminder(
                message=reminder_message,
                due_datetime=reminder_due_dt,
                status='pending',
                reminder_type='medicine_start',
                dog_id=dog.id,
                dog_medicine_id=med.id,
                user_id=temp_user_id
            )
            db.session.add(updated_start_reminder)
            db.session.commit() # Commit reminder changes
        except Exception as e:
            db.session.rollback()
            print(f"Error updating/creating reminder for edited medicine: {e}")

    dog = Dog.query.get_or_404(dog_id)
    medicine_presets_data = MedicinePreset.query.filter(
        (MedicinePreset.rescue_id == dog.rescue_id) | (MedicinePreset.rescue_id == None)
    ).all()
    return render_template('partials/medicines_list.html', dog=dog, medicine_presets=medicine_presets_data)

@app.route('/dog/<int:dog_id>/medicine/delete/<int:medicine_id>', methods=['POST'])
def delete_medicine(dog_id, medicine_id):
    dog = Dog.query.get_or_404(dog_id)
    med = DogMedicine.query.get_or_404(medicine_id)
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

@app.route('/api/appointment/<int:appointment_id>')
def api_get_appointment(appointment_id):
    from models import Appointment
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

@app.route('/api/medicine/<int:medicine_id>')
def api_get_medicine(medicine_id):
    from models import DogMedicine
    med = DogMedicine.query.get_or_404(medicine_id)
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

# --- Reminders Page ---
# This route is being removed as its functionality is merged into /calendar
# @app.route('/reminders')
# def reminders_page():
#     # TODO: Filter by current_user.id when user system is fully integrated
#     # For now, fetching reminders for user_id=1 or all pending if user_id is nullable and might be None
#     pending_reminders = Reminder.query.filter_by(status='pending').order_by(Reminder.due_datetime.asc()).all()
#     return render_template('reminders_page.html', reminders=pending_reminders)

@app.route('/reminder/<int:reminder_id>/acknowledge', methods=['POST'])
def acknowledge_reminder(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    # TODO: Add user authorization check - ensure current_user owns this reminder or has permission
    reminder.status = 'acknowledged'
    db.session.commit()
    # For HTMX, an empty response with 200 OK will typically remove the element if hx-swap="outerHTML"
    # Or we could return a partial showing the item as acknowledged.
    # For now, it will be removed from the pending list.
    return '', 200

@app.route('/reminder/<int:reminder_id>/dismiss', methods=['POST'])
def dismiss_reminder(reminder_id):
    reminder = Reminder.query.get_or_404(reminder_id)
    # TODO: Add user authorization check
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
            reminders_query = Reminder.query.options(
                db.joinedload(Reminder.appointment).joinedload(Appointment.type),
                db.joinedload(Reminder.dog_medicine)
            ).filter(Reminder.status == 'pending', Reminder.dog.has(rescue_id=rescue_id)).order_by(Reminder.due_datetime.asc()).all()
        else:
            reminders_query = Reminder.query.options(
                db.joinedload(Reminder.appointment).joinedload(Appointment.type),
                db.joinedload(Reminder.dog_medicine)
            ).filter(Reminder.status == 'pending').order_by(Reminder.due_datetime.asc()).all()
    else:
        rescues = None
        rescue_id = current_user.rescue_id
        reminders_query = Reminder.query.options(
            db.joinedload(Reminder.appointment).joinedload(Appointment.type),
            db.joinedload(Reminder.dog_medicine)
        ).filter(Reminder.status == 'pending', Reminder.dog.has(rescue_id=current_user.rescue_id)).order_by(Reminder.due_datetime.asc()).all()
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
            event_url = url_for('dog_details', dog_id=appt.dog_id, _anchor=f"appointment-{appt.id}") if appt.dog_id else '#'
            
            event_title_parts = []
            if appt.dog: event_title_parts.append(appt.dog.name)
            else: event_title_parts.append("Unknown Dog")
            
            main_title_part = appt.title
            if not main_title_part and appt.type: main_title_part = appt.type.name
            if not main_title_part: main_title_part = "Appointment"
            event_title_parts.append(main_title_part)
            
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
            event_url = url_for('dog_details', dog_id=med.dog_id, _anchor=f"medicine-{med.id}") if med.dog_id else '#'

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

# --- Dashboard Route ---
@app.route('/dashboard')
@login_required
def dashboard():
    from datetime import date
    rescue_id = request.args.get('rescue_id', type=int)
    if current_user.role == 'superadmin':
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        if rescue_id:
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
        rescues = None
        rescue_id = current_user.rescue_id
        overdue_reminders = Reminder.query.options(
            db.joinedload(Reminder.appointment).joinedload(Appointment.type),
            db.joinedload(Reminder.dog_medicine).joinedload(DogMedicine.preset),
            db.joinedload(Reminder.dog)
        ).filter(
            Reminder.status == 'pending',
            Reminder.due_datetime < datetime.utcnow(),
            Reminder.dog.has(rescue_id=current_user.rescue_id)
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
            Reminder.dog.has(rescue_id=current_user.rescue_id)
        ).order_by(Reminder.due_datetime.asc()).all()
    grouped_overdue_reminders = group_reminders_by_type(overdue_reminders)
    grouped_today_reminders = group_reminders_by_type(today_reminders)
    return render_template('dashboard.html',
                           current_user=current_user,
                           grouped_overdue_reminders=grouped_overdue_reminders,
                           grouped_today_reminders=grouped_today_reminders,
                           now=datetime.utcnow(),
                           rescues=rescues,
                           selected_rescue_id=rescue_id)

@app.route('/dog/<int:dog_id>/history')
def dog_history(dog_id):
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
def add_dog_note(dog_id):
    # dog object is fetched by _get_dog_history_events if needed, or use a simpler query here just for validation
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

    category = request.form.get('category')
    note_text = request.form.get('note_text')

    if not category or not note_text:
        error_message = "Category and Note text are required."
        if not category and not note_text:
            error_message = "Category and Note text are required."
        elif not category:
            error_message = "Category is required."
        else: 
            error_message = "Note text is required."
        
        if request.headers.get('HX-Request'):
            response = make_response(render_template('partials/modal_form_error.html', message=error_message), 200)
            response.headers['HX-Retarget'] = '#addDogNoteModalError'
            response.headers['HX-Reswap'] = 'innerHTML'
            return response
        else:
            flash(error_message, 'danger')
            return redirect(url_for('dog_history', dog_id=dog_id))

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

@app.route('/admin/audit-logs')
def admin_audit_logs():
    current_user = get_current_user()
    if not current_user or not (current_user.role in ('superadmin', 'owner')):
        abort(403)
    page = int(request.args.get('page', 1))
    per_page = 25
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    audit_stats = get_audit_system_stats() if current_user.role == 'superadmin' else None
    return render_template('admin_audit_logs.html', logs=logs, current_user=current_user, audit_stats=audit_stats)

@app.route('/admin/flush-audit-batch', methods=['POST'])
def admin_flush_audit_batch():
    current_user = get_current_user()
    if not current_user or current_user.role != 'superadmin':
        abort(403)
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
def admin_run_audit_cleanup():
    current_user = get_current_user()
    if not current_user or current_user.role != 'superadmin':
        abort(403)
    cleanup_old_audit_logs()
    flash('Audit log cleanup completed.', 'info')
    return redirect(url_for('admin_audit_logs'))

@app.route('/staff-management')
@login_required
def staff_management():
    return render_template('staff_management.html')

@app.route('/rescue-info')
@login_required
def rescue_info():
    return render_template('rescue_info.html')

if __name__ == '__main__':
    print('--- ROUTES REGISTERED ---')
    for rule in app.url_map.iter_rules():
        print(rule, rule.methods)
    print('-------------------------')
    app.run(debug=True, host='0.0.0.0') 