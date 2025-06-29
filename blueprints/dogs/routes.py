# Standard library imports
import json
from collections import defaultdict
from datetime import datetime, timedelta

# Third-party imports
import bleach
from flask import (abort, flash, g, jsonify, make_response, redirect,
                   render_template, render_template_string, request, send_file,
                   session, url_for)
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

# Local application imports
from . import dogs_bp
from blueprints.core.audit_helpers import log_audit_event
from blueprints.core.decorators import (rescue_access_required, role_required,
                                        roles_required)
from blueprints.core.utils import (check_rescue_access, export_to_csv,
                                   get_dog_history_events, get_first_user_id,
                                   get_rescue_appointments, get_rescue_dogs,
                                   get_rescue_medicine_presets,
                                   get_rescue_medicines, htmx_error_response)
from empathetic_messages import flash_error, flash_success
from extensions import db
from models import (Appointment, AppointmentType, AuditLog, Dog, DogMedicine,
                    DogNote, MedicinePreset, Reminder, Rescue, User)


def _get_dog_history_events(dog_id):
    """Get dog history events including personality information."""
    dog, history_events = get_dog_history_events(dog_id)
    
    # Add personality observations if available
    if dog.personality_notes or dog.energy_level or dog.social_notes or dog.special_story or dog.temperament_tags:
        personality_details = []
        if dog.energy_level:
            personality_details.append(f"Energy level: {dog.energy_level}")
        if dog.temperament_tags:
            tags = [tag.strip() for tag in dog.temperament_tags.split(',') if tag.strip()]
            if tags:
                personality_details.append(f"Traits: {', '.join(tags[:3])}")
        if dog.personality_notes:
            personality_details.append(f"Character: {dog.personality_notes[:100]}{'...' if len(dog.personality_notes) > 100 else ''}")
        if dog.social_notes:
            personality_details.append(f"Social: {dog.social_notes[:100]}{'...' if len(dog.social_notes) > 100 else ''}")
        
        description = f"Personality observations recorded for {dog.name}. " + " | ".join(personality_details)
        
        # Use current time since we don't have specific personality update timestamps
        history_events.append({
            'timestamp': datetime.utcnow(),
            'event_type': 'Personality Profile',
            'description': description,
            'author': 'Care Team',
            'source_model': 'DogPersonality',
            'source_id': dog.id
        })
        
        # Re-sort after adding personality event
        history_events.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return dog, history_events


def render_dog_cards_html(selected_rescue_id=None):
    """Render dog cards HTML for HTMX updates."""
    dogs = []
    if current_user.is_authenticated:
        if current_user.role == 'superadmin':
            if selected_rescue_id and selected_rescue_id != "":
                try:
                    rescue_id_int = int(selected_rescue_id)
                    dogs = Dog.query.filter_by(rescue_id=rescue_id_int).order_by(Dog.name.asc()).all()
                except ValueError:
                    dogs = Dog.query.order_by(Dog.name.asc()).all()
            else:
                dogs = Dog.query.order_by(Dog.name.asc()).all()
        else:
            dogs = Dog.query.filter_by(rescue_id=current_user.rescue_id).order_by(Dog.name.asc()).all()
    else:
        dogs = []
    return render_template('dog_cards.html', dogs=dogs, selected_rescue_id=selected_rescue_id)


def render_dog_stats_html(selected_rescue_id=None):
    """Render dog statistics HTML for dashboard."""
    dogs = []
    rescues = []

    if current_user.is_authenticated:
        if current_user.role == 'superadmin':
            if selected_rescue_id and selected_rescue_id != "":
                try:
                    rescue_id_int = int(selected_rescue_id)
                    dogs = Dog.query.filter_by(rescue_id=rescue_id_int).order_by(Dog.name.asc()).all()
                except ValueError:
                    dogs = Dog.query.order_by(Dog.name.asc()).all()
            else:
                dogs = Dog.query.order_by(Dog.name.asc()).all()
        else:
            dogs = Dog.query.filter_by(rescue_id=current_user.rescue_id).order_by(Dog.name.asc()).all()
        
        if current_user.role == 'superadmin':
            rescues = Rescue.query.all()

    return render_template_string('''
<div class="row mb-4" id="dogStatsRow" hx-swap-oob="outerHTML">
    <div class="col-12">
        <div class="card bg-light">
            <div class="card-body">
                <div class="row text-center">
                    <div class="col-md-4">
                        <h5 class="mb-1">{{ dogs|length }}</h5>
                        <small class="text-muted">Total Dogs</small>
                    </div>
                    <div class="col-md-4">
                        <h5 class="mb-1">{{ dogs|selectattr('adoption_status', 'equalto', 'Adopted')|list|length }}</h5>
                        <small class="text-muted">Adopted</small>
                    </div>
                    <div class="col-md-4">
                        <h5 class="mb-1">{{ dogs|selectattr('adoption_status', 'equalto', 'Not Adopted')|list|length }}</h5>
                        <small class="text-muted">Available</small>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
''', dogs=dogs, rescues=rescues, selected_rescue_id=selected_rescue_id)


@dogs_bp.route('/dogs')
@login_required
def dog_list_page():
    """Dog list page with multi-tenant filtering."""
    if current_user.role == 'superadmin':
        rescue_id = request.args.get('rescue_id', type=int)
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        if rescue_id:
            dogs = Dog.query.filter_by(rescue_id=rescue_id).order_by(Dog.name.asc()).all()
        else:
            dogs = Dog.query.order_by(Dog.name.asc()).all()
        session['selected_rescue_id'] = str(rescue_id) if rescue_id else ""
        return render_template('index.html', dogs=dogs, rescues=rescues, selected_rescue_id=rescue_id)
    else:
        dogs = Dog.query.filter_by(rescue_id=current_user.rescue_id).order_by(Dog.name.asc()).all()
        session['selected_rescue_id'] = str(current_user.rescue_id)
        return render_template('index.html', dogs=dogs)


@dogs_bp.route('/dog/<int:dog_id>')
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def dog_details(dog_id):
    """Dog details page with appointments, medicines, and recent history."""
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)

    # Fetch and prepare appointment types ensuring unique names, sorted
    appointment_types_db = AppointmentType.query.filter_by(rescue_id=dog.rescue_id).order_by(AppointmentType.name).all()
    unique_appointment_types_dict = {}
    for t in appointment_types_db:
        if t.name not in unique_appointment_types_dict:
            unique_appointment_types_dict[t.name] = {"id": t.id, "name": t.name}
    appointment_types_json = sorted(list(unique_appointment_types_dict.values()), key=lambda x: x['name'])

    # Fetch and prepare medicine presets, grouped by category, and sorted
    all_medicine_presets_db = get_rescue_medicine_presets(dog.rescue_id).order_by(MedicinePreset.category, MedicinePreset.name).all()

    categorized_medicine_presets = defaultdict(list)
    temp_deduped_presets_by_name = {}
    rescue_specific_presets = [p for p in all_medicine_presets_db if p.rescue_id == dog.rescue_id]
    global_presets = [p for p in all_medicine_presets_db if p.rescue_id == None]

    for preset in rescue_specific_presets:
        temp_deduped_presets_by_name[preset.name] = preset
    for preset in global_presets:
        if preset.name not in temp_deduped_presets_by_name:
            temp_deduped_presets_by_name[preset.name] = preset
    
    final_sorted_presets = sorted(temp_deduped_presets_by_name.values(), key=lambda p: (p.category or "Uncategorized", p.name))

    for preset in final_sorted_presets:
        category_name = preset.category if preset.category else "Uncategorized"
        categorized_medicine_presets[category_name].append({
            "id": preset.id,
            "name": preset.name,
            "suggested_units": preset.suggested_units,
            "default_dosage_instructions": preset.default_dosage_instructions
        })
    
    sorted_categorized_medicine_presets = dict(sorted(categorized_medicine_presets.items()))

    # Get recent history events for the Recent Activity widget
    _, all_history_events = _get_dog_history_events(dog_id)
    recent_history_events = all_history_events[:5]

    return render_template('dog_details.html', 
                           dog=dog, 
                           appointment_types=appointment_types_json, 
                           medicine_presets_categorized=sorted_categorized_medicine_presets,
                           recent_history_events=recent_history_events,
                           now=datetime.now(),
                           timedelta=timedelta)


@dogs_bp.route('/dog/add', methods=['POST'])
@login_required
def add_dog():
    """Add new dog with validation and audit logging."""
    name = request.form.get('name', '').strip()
    if not name or len(name) > 100:
        error_msg = 'Dog name is required and must be 100 characters or less.'
        if request.headers.get('HX-Request'):
            cards = render_dog_cards_html()
            resp = make_response(cards)
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": error_msg, "category": "danger"}})
            return resp
        flash(error_msg, 'danger')
        return redirect(url_for('dogs.dog_list_page'))
    
    age = request.form.get('age', '').strip()
    if age and len(age) > 10:
        age = age[:10]
    breed = request.form.get('breed', '').strip()
    if breed and len(breed) > 50:
        breed = breed[:50]
    adoption_status = request.form.get('adoption_status', '').strip()
    if adoption_status and len(adoption_status) > 30:
        adoption_status = adoption_status[:30]
    intake_date = request.form.get('intake_date')
    if not intake_date:
        intake_date = None
    microchip_id = request.form.get('microchip_id', '').strip()
    if microchip_id and len(microchip_id) > 50:
        microchip_id = microchip_id[:50]
    notes = request.form.get('notes', '').strip()
    if notes and len(notes) > 1000:
        notes = notes[:1000]
    notes = bleach.clean(notes)
    medical_info = request.form.get('medical_info', '').strip()
    if medical_info and len(medical_info) > 1000:
        medical_info = medical_info[:1000]
    medical_info = bleach.clean(medical_info)
    
    rescue_id = current_user.rescue_id if current_user.role != 'superadmin' else request.form.get('rescue_id')
    
    if current_user.role == 'superadmin' and not rescue_id:
        error_msg = 'Please select a rescue for this dog.'
        if request.headers.get('HX-Request'):
            cards = render_dog_cards_html()
            resp = make_response(cards)
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": error_msg, "category": "danger"}})
            return resp
        flash(error_msg, 'danger')
        return redirect(url_for('dogs.dog_list_page'))
    
    dog = Dog(name=name, age=age, breed=breed, adoption_status=adoption_status,
              intake_date=intake_date, microchip_id=microchip_id, notes=notes,
              medical_info=medical_info, rescue_id=rescue_id)
    db.session.add(dog)
    db.session.commit()
    
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
    return redirect(url_for('dogs.dog_list_page'))


@dogs_bp.route('/dog/edit', methods=['POST'])
@rescue_access_required(lambda kwargs: Dog.query.get(int(request.form.get('dog_id'))).rescue_id)
@login_required
def edit_dog():
    """Edit existing dog with validation and audit logging."""
    dog_id = request.form.get('dog_id')
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
    
    name = request.form.get('name', '').strip()
    if not name or len(name) > 100:
        error_msg = flash_error('form_validation_general')
        if request.headers.get('HX-Request'):
            cards = render_dog_cards_html()
            resp = make_response(cards)
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": error_msg, "category": "danger"}})
            return resp
        return redirect(request.referrer or url_for('dogs.dog_list_page'))
    
    dog.name = name
    dog.age = request.form.get('age', '').strip()[:10]
    dog.breed = request.form.get('breed', '').strip()[:50]
    dog.adoption_status = request.form.get('adoption_status', '').strip()[:30]
    dog.intake_date = request.form.get('intake_date')
    if not dog.intake_date:
        dog.intake_date = None
    dog.microchip_id = request.form.get('microchip_id', '').strip()[:50]
    notes = request.form.get('notes', '').strip()[:1000]
    dog.notes = bleach.clean(notes)
    medical_info = request.form.get('medical_info', '').strip()[:1000]
    dog.medical_info = bleach.clean(medical_info)
    
    db.session.commit()
    
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
    
    success_msg = flash_success('dog_updated', dog_name=dog.name)
    
    if request.headers.get('HX-Request'):
        if request.form.get('from_details') == 'details':
            resp = make_response('')
            resp.headers['HX-Redirect'] = request.referrer or '/'
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": success_msg, "category": "success"}})
            return resp
        cards = render_dog_cards_html()
        resp = make_response(cards)
        resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": success_msg, "category": "success"}})
        return resp
    return redirect(url_for('dogs.dog_list_page'))


@dogs_bp.route('/dog/<int:dog_id>/personality/edit', methods=['POST'])
@login_required
def edit_dog_personality(dog_id):
    """Edit dog personality fields separately."""
    print(f"DEBUG: edit_dog_personality called with dog_id={dog_id}")
    print(f"DEBUG: Current user: {current_user}")
    print(f"DEBUG: Request form data: {request.form}")
    
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
    
    # Phase 7C: Personality fields only
    dog.energy_level = request.form.get('energy_level', '').strip()[:20] if request.form.get('energy_level') else None
    temperament_tags = request.form.get('temperament_tags', '').strip()[:200]
    dog.temperament_tags = bleach.clean(temperament_tags) if temperament_tags else None
    personality_notes = request.form.get('personality_notes', '').strip()[:2000]
    dog.personality_notes = bleach.clean(personality_notes) if personality_notes else None
    social_notes = request.form.get('social_notes', '').strip()[:2000]
    dog.social_notes = bleach.clean(social_notes) if social_notes else None
    special_story = request.form.get('special_story', '').strip()[:2000]
    dog.special_story = bleach.clean(special_story) if special_story else None
    
    db.session.commit()
    
    log_audit_event(
        user_id=current_user.id,
        rescue_id=dog.rescue_id,
        action='edit_personality',
        resource_type='Dog',
        resource_id=dog.id,
        details={
            'name': dog.name,
            'energy_level': dog.energy_level,
            'has_temperament_tags': bool(dog.temperament_tags),
            'has_personality_notes': bool(dog.personality_notes),
            'has_social_notes': bool(dog.social_notes),
            'has_special_story': bool(dog.special_story)
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    
    success_msg = flash_success('dog_updated', dog_name=f"{dog.name}'s personality")
    
    if request.headers.get('HX-Request'):
        resp = make_response('')
        resp.headers['HX-Redirect'] = request.referrer or url_for('dogs.dog_details', dog_id=dog.id)
        resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": success_msg, "category": "success"}})
        return resp
    
    return redirect(url_for('dogs.dog_details', dog_id=dog.id))


@dogs_bp.route('/dog/<int:dog_id>/delete', methods=['POST'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def delete_dog(dog_id):
    """Delete dog with audit logging and HTMX support."""
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
    
    # Store dog info for audit log before deletion
    dog_info = {
        'name': dog.name,
        'age': dog.age,
        'breed': dog.breed,
        'adoption_status': dog.adoption_status,
        'intake_date': str(dog.intake_date),
        'microchip_id': dog.microchip_id
    }
    dog_rescue_id = dog.rescue_id
    
    db.session.delete(dog)
    db.session.commit()
    
    log_audit_event(
        user_id=current_user.id,
        rescue_id=dog_rescue_id,
        action='delete',
        resource_type='Dog',
        resource_id=dog_id,
        details=dog_info,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        success=True
    )
    
    if request.headers.get('HX-Request'):
        current_selected_rescue_id = request.form.get('selected_rescue_id')
        if current_selected_rescue_id is None:
            current_selected_rescue_id = request.args.get('rescue_id', session.get('selected_rescue_id'))
            if current_selected_rescue_id is None:
                current_selected_rescue_id = ""

        dog_cards_html = render_dog_cards_html(selected_rescue_id=current_selected_rescue_id)
        dog_stats_html = render_dog_stats_html(selected_rescue_id=current_selected_rescue_id)
        
        combined_html = dog_cards_html + dog_stats_html
        resp = make_response(combined_html)
        resp.headers['HX-Trigger'] = json.dumps({
            "showAlert": {"message": "Dog deleted successfully!", "category": "success"}
        })
        return resp
    flash('Dog deleted successfully!', 'success')
    return redirect(url_for('dogs.dog_list_page'))


@dogs_bp.route('/dog/<int:dog_id>/history')
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def dog_history(dog_id):
    """Dog history timeline with pagination."""
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
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


@dogs_bp.route('/history')
@login_required
def dog_history_overview():
    """Overview of all dogs with recent history events."""
    rescue_id = request.args.get('rescue_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Limit per_page to reasonable values
    if per_page not in [10, 20, 50, 100]:
        per_page = 20
    
    # Build base query
    if current_user.role == 'superadmin':
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        if rescue_id:
            base_query = Dog.query.filter_by(rescue_id=rescue_id)
        else:
            base_query = Dog.query
    else:
        rescues = None
        rescue_id = current_user.rescue_id
        base_query = Dog.query.filter_by(rescue_id=current_user.rescue_id)
    
    # Get paginated results
    dogs_pagination = base_query.order_by(Dog.name.asc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    dogs = dogs_pagination.items
    
    # Organize dogs alphabetically for display
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
                           selected_rescue_id=rescue_id,
                           pagination=dogs_pagination,
                           per_page=per_page,
                           now=datetime.now())


@dogs_bp.route('/dog/<int:dog_id>/note/add', methods=['POST'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def add_dog_note(dog_id):
    """Add care note to dog with validation and HTMX support."""
    dog = Dog.query.get_or_404(dog_id)
    check_rescue_access(dog)
    
    dog_check = Dog.query.get_or_404(dog_id)
    current_user_id = get_first_user_id()
    if not current_user_id:
        if request.headers.get('HX-Request'):
            return htmx_error_response('Error: Could not identify user for note creation.', 'addDogNoteModal', 400)
        flash('Error: Could not identify user for note creation.', 'danger')
        return redirect(url_for('dogs.dog_history', dog_id=dog_id))

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
            return htmx_error_response(error_message, 'addDogNoteModal', 200)
        else:
            flash(error_message, 'danger')
            return redirect(url_for('dogs.dog_history', dog_id=dog_id))

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

    # Re-fetch all history events for the dog
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
        return redirect(url_for('dogs.dog_history', dog_id=dog_id))


@dogs_bp.route('/api/dog/<int:dog_id>/history_events')
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def api_dog_history_events(dog_id):
    """API endpoint for filtered dog history events."""
    dog = Dog.query.get_or_404(dog_id)
    
    # Get filter parameters from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    event_types = request.args.getlist('event_types[]')
    categories = request.args.getlist('categories[]')
    search_query = request.args.get('search_query', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
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
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
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


@dogs_bp.route('/export/dog_history/<int:dog_id>', methods=['GET'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def export_dog_history(dog_id):
    """Export complete dog history as CSV."""
    dog, all_history_events = _get_dog_history_events(dog_id)
    
    # Prepare headers
    headers = ['Timestamp', 'Event Type', 'Description', 'Author', 'Source Model', 'Source ID']
    
    # Prepare data rows
    data = []
    for event in all_history_events:
        data.append([
            event['timestamp'].isoformat(),
            event['event_type'],
            event['description'],
            event['author'],
            event['source_model'],
            event['source_id']
        ])
    
    # Generate filename
    filename = f"{dog.name}_history"
    
    return export_to_csv(data, headers, filename)


@dogs_bp.route('/export/medical_summary/<int:dog_id>', methods=['GET'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def export_medical_summary(dog_id):
    """Export medical summary as CSV."""
    dog = Dog.query.get_or_404(dog_id)
    
    # Prepare headers
    headers = ['Medicine Name', 'Dosage', 'Unit', 'Form', 'Frequency', 'Start Date', 'End Date', 'Status', 'Notes']
    
    # Prepare data rows
    data = []
    for med in dog.medicines:
        data.append([
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
    
    # Generate filename
    filename = f"{dog.name}_medical_summary"
    
    return export_to_csv(data, headers, filename)


@dogs_bp.route('/export/medication_log/<int:dog_id>', methods=['GET'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def export_medication_log(dog_id):
    """Export medication log as CSV."""
    dog = Dog.query.get_or_404(dog_id)
    
    # Prepare headers
    headers = ['Medicine Name', 'Dosage', 'Unit', 'Form', 'Frequency', 'Start Date', 'End Date', 'Status', 'Notes']
    
    # Prepare data rows
    data = []
    for med in dog.medicines:
        data.append([
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
    
    # Generate filename
    filename = f"{dog.name}_medication_log"
    
    return export_to_csv(data, headers, filename)


@dogs_bp.route('/export/care_summary/<int:dog_id>', methods=['GET'])
@rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
@login_required
def export_care_summary(dog_id):
    """Export comprehensive care summary as text file."""
    dog, all_history_events = _get_dog_history_events(dog_id)
    
    # Generate comprehensive text report
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
    
    report_content = "\n".join(report_lines)
    
    response = make_response(report_content)
    response.headers['Content-Disposition'] = f'attachment; filename={dog.name}_care_summary.txt'
    response.headers['Content-Type'] = 'text/plain'
    
    return response