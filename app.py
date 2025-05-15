# DogTrackerV2/app.py
import os
import uuid # Added for UUID validation potentially
from flask import Flask, render_template, redirect, url_for, session, abort, g, request, flash
from datetime import datetime, timezone # Import datetime and timezone
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from functools import wraps # For decorator

# Import configurations and db instance
from config import config_by_name
from models import db, Rescue, Dog, Medicine # Import db and initial models
from forms import AddDogForm, EditDogForm, AddMedicineForm, EditDogAndMedicinesForm, MedicineForm # Import AddDogForm and EditDogForm

# Initialize extensions
migrate = Migrate()
csrf = CSRFProtect()

# --- Decorator for checking rescue selection ---
def rescue_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'selected_rescue_id' not in session:
            return redirect(url_for('select_rescue'))
        # Make rescue object available globally for the request via 'g'
        if not hasattr(g, 'current_rescue'):
             rescue_id = session.get('selected_rescue_id')
             g.current_rescue = db.session.get(Rescue, rescue_id) if rescue_id else None
             if rescue_id and g.current_rescue is None:
                 # Invalid ID in session, clear it and redirect
                 session.pop('selected_rescue_id', None)
                 return redirect(url_for('select_rescue'))
        return f(*args, **kwargs)
    return decorated_function

# --- Application Factory ---
def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # --- Routes ---
    @app.route('/')
    def index():
        # Root redirects to welcome page
        return redirect(url_for('welcome'))

    @app.route('/welcome')
    def welcome():
        print("\n--- DEBUG [welcome]: Entering /welcome route ---")
        rescue_id_from_session = session.get('selected_rescue_id')
        print(f"--- DEBUG [welcome]: rescue_id from session: {rescue_id_from_session} ---")

        if not rescue_id_from_session:
            print("--- DEBUG [welcome]: No rescue_id in session, redirecting to select_rescue ---")
            return redirect(url_for('select_rescue'))

        rescue = db.session.get(Rescue, rescue_id_from_session)
        print(f"--- DEBUG [welcome]: Result of db.session.get(Rescue, '{rescue_id_from_session}'): {rescue} ---")

        if not rescue:
            print(f"--- DEBUG [welcome]: Rescue not found for ID {rescue_id_from_session} from session. Clearing session and redirecting. ---")
            session.pop('selected_rescue_id', None)
            return redirect(url_for('select_rescue'))

        print(f"--- DEBUG [welcome]: Rendering welcome.html for rescue: {rescue.name} ---")
        return render_template('welcome.html', rescue=rescue)

    @app.route('/select_rescue')
    def select_rescue():
        print("\n--- DEBUG: Entering /select_rescue route ---")
        rescues = Rescue.query.order_by(Rescue.name).all()
        print(f"--- DEBUG: Fetched {len(rescues)} rescues from DB. ---")
        for r_debug in rescues:
            print(f"    DEBUG FROM ROUTE -> Name: {r_debug.name}, ID: {r_debug.id}")
        print("--- DEBUG: About to render select_rescue.html ---\n")
        return render_template('select_rescue.html', rescues=rescues)


    @app.route('/set_rescue/<string:rescue_id_str>')
    def set_rescue(rescue_id_str):
        print(f"\n--- DEBUG [set_rescue]: ROUTE ENTERED with string: {rescue_id_str} ---")
        print(f"--- DEBUG [set_rescue]: Attempting to find rescue with ID: {rescue_id_str} ---")

        rescue = db.session.get(Rescue, rescue_id_str)

        if rescue:
            print(f"--- DEBUG [set_rescue]: SUCCESS - Found rescue: {rescue.name} with ID: {rescue.id} ---")
            session['selected_rescue_id'] = rescue_id_str
            return redirect(url_for('welcome'))
        else:
            print(f"--- DEBUG [set_rescue]: FAILED - Rescue with ID {rescue_id_str} NOT FOUND by db.session.get() ---")
            abort(404)

    @app.route('/home')
    @rescue_required # Protect this route
    def home():
        # The decorator handles the session check and makes g.current_rescue available
        # Later, fetch reminders for g.current_rescue.id
        return render_template('home.html', rescue=g.current_rescue)

    # --- Dog Management Route (Central hub for listing dogs and displaying various forms) ---
    @app.route('/dogs', methods=['GET', 'POST'])
    @rescue_required
    def manage_dogs():
        action = request.args.get('action')
        dog_id_param = request.args.get('dog_id') # Used for medicine forms or edit_dog_medicines
        edit_dog_id_param = request.args.get('edit_dog_id') # Used for simple dog edit form

        # Initialize variables for template context
        form_to_display = None
        current_form_action_url = None
        form_legend = None
        dog_being_edited = None # This will hold the dog object for any form context
        current_action_for_template = action # Pass the raw action to template, can be refined
        dog_for_form_id_template = None # Initialize this

        # --- Handle POST for Adding a New Dog ---
        # This is the only POST directly handled by manage_dogs. Others have their own routes.
        add_dog_form = AddDogForm(request.form) # Instantiate for POST, even if not initially for display
        if request.method == 'POST' and action == 'show_add_form': # Or check if add_dog_form.submit.data if only one POST target
            if add_dog_form.validate_on_submit():
                try:
                    new_dog = Dog(
                        name=add_dog_form.name.data,
                        approx_age=add_dog_form.approx_age.data,
                        rescue_id=g.current_rescue.id
                    )
                    db.session.add(new_dog)
                    db.session.commit()
                    flash(f'Dog "{new_dog.name}" added successfully!', 'success')
                    return redirect(url_for('manage_dogs'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error adding dog: {e}', 'danger')
                    # If add fails, we fall through to display add_dog_form with errors
                    form_to_display = add_dog_form # Keep the form with errors
                    current_action_for_template = 'show_add_form' # Ensure action is set for re-display
            else:
                # Add form validation failed
                form_to_display = add_dog_form # Keep the form with errors
                current_action_for_template = 'show_add_form' # Ensure action is set for re-display
        
        # --- Handle GET requests for displaying forms (or if AddDogForm POST failed) ---
        if not form_to_display: # Only proceed if AddDogForm POST didn't set form_to_display
            if action == 'show_add_form':
                form_to_display = AddDogForm() # Fresh form for GET
                current_form_action_url = url_for('manage_dogs', action='show_add_form') # POST back to manage_dogs with action
                form_legend = "Add New Dog"
            elif action == 'show_edit_form' and edit_dog_id_param:
                dog_being_edited = Dog.query.filter_by(id=edit_dog_id_param, rescue_id=g.current_rescue.id).first_or_404()
                form_to_display = EditDogForm(obj=dog_being_edited)
                current_form_action_url = url_for('edit_dog', dog_id=dog_being_edited.id)
                form_legend = f"Edit {dog_being_edited.name}"
            elif action == 'show_add_medicine_form' and dog_id_param:
                dog_being_edited = Dog.query.filter_by(id=dog_id_param, rescue_id=g.current_rescue.id).first_or_404()
                form_to_display = AddMedicineForm()
                current_form_action_url = url_for('add_medicine', dog_id=dog_being_edited.id)
                form_legend = f"Add Medicine for {dog_being_edited.name}"
                dog_for_form_id_template = dog_being_edited.id # Set it here
            elif action == 'show_edit_dog_medicines_form' and dog_id_param:
                dog_being_edited = Dog.query.filter_by(id=dog_id_param, rescue_id=g.current_rescue.id).first_or_404()

                form = EditDogAndMedicinesForm()  # Instantiate the form without obj

                # Populate the main dog fields
                form.name.data = dog_being_edited.name
                form.approx_age.data = dog_being_edited.approx_age

                # Clear and populate the medicines FieldList
                while len(form.medicines.entries) > 0:
                    form.medicines.pop_entry()

                for med in dog_being_edited.medicines.order_by(Medicine.created_at).all():
                    med_form = MedicineForm(obj=med)
                    form.medicines.append_entry(med_form)

                # Add a blank entry for a new medicine
                form.medicines.append_entry()

                form_to_display = form
                current_form_action_url = url_for('edit_dog_with_medicines', dog_id=dog_being_edited.id)
                form_legend = f"Edit {dog_being_edited.name} and Medicines"
                dog_for_form_id_template = dog_being_edited.id
            # else: no specific form action, form_to_display remains None

        # If AddDogForm POST failed, current_action_for_template is already set to 'show_add_form'
        # and form_to_display has the errors. We need to ensure legend and URL are also set.
        if current_action_for_template == 'show_add_form' and form_to_display and form_to_display.errors:
            current_form_action_url = url_for('manage_dogs', action='show_add_form')
            form_legend = "Add New Dog"

        all_dogs = Dog.query.filter_by(rescue_id=g.current_rescue.id).order_by(Dog.name).all()
        
        return render_template('dog_list.html',
                               rescue=g.current_rescue,
                               dogs=all_dogs,
                               form_to_display=form_to_display,
                               current_form_action_url=current_form_action_url,
                               form_legend=form_legend,
                               dog_being_edited=dog_being_edited, # Dog context for the form
                               current_action=current_action_for_template, # The action determining the form
                               dog_for_form_id=dog_for_form_id_template) # Add this

    # --- Route for Handling Edit Dog Submission ---
    @app.route('/dog/<string:dog_id>/edit', methods=['POST'])
    @rescue_required
    def edit_dog(dog_id):
        dog_to_edit = Dog.query.filter_by(id=dog_id, rescue_id=g.current_rescue.id).first_or_404()
        edit_form = EditDogForm(request.form) # Populate form with submitted data

        if edit_form.validate_on_submit():
            try:
                dog_to_edit.name = edit_form.name.data
                dog_to_edit.approx_age = edit_form.approx_age.data
                dog_to_edit.updated_at = datetime.now(timezone.utc) # Assuming you have this field
                db.session.commit()
                flash(f'Dog "{dog_to_edit.name}" updated successfully!', 'success')
                return redirect(url_for('manage_dogs'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating dog: {e}', 'danger')
                # If update fails, redirect to the edit view for this dog to show the form again
                # (ideally with errors, but simple redirect for now)
                return redirect(url_for('manage_dogs', edit_dog_id=dog_id))
        else:
            # Form validation failed, re-render the dog_list page with the edit form and errors
            # Pass the form with errors back to the template
            dogs = Dog.query.filter_by(rescue_id=g.current_rescue.id).order_by(Dog.name).all()
            flash('Error updating dog. Please check the form for errors.', 'danger')
            return render_template('dog_list.html',
                                   rescue=g.current_rescue,
                                   dogs=dogs,
                                   form_to_display=edit_form, # Show the form with errors
                                   current_form_action_url=url_for('edit_dog', dog_id=dog_id),
                                   form_legend=f"Edit {dog_to_edit.name}",
                                   dog_being_edited=dog_to_edit,
                                   current_action='show_edit_form')

    # --- Route for Adding Medicine to a Dog ---
    @app.route('/dog/<string:dog_id>/medicine/add', methods=['GET', 'POST'])
    @rescue_required
    def add_medicine(dog_id):
        dog = Dog.query.filter_by(id=dog_id, rescue_id=g.current_rescue.id).first_or_404()
        form = AddMedicineForm()

        if form.validate_on_submit():
            try:
                new_medicine = Medicine(
                    name=form.name.data,
                    dosage=form.dosage.data,
                    frequency=form.frequency.data,
                    start_date=form.start_date.data,
                    end_date=form.end_date.data,
                    notes=form.notes.data,
                    dog_id=dog.id,
                    rescue_id=g.current_rescue.id
                )
                db.session.add(new_medicine)
                db.session.commit()
                flash(f'Medicine "{new_medicine.name}" added for {dog.name} successfully!', 'success')
                return redirect(url_for('manage_dogs')) # Redirect to the main list
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding medicine: {e}', 'danger')
        
        # For GET request or if form validation fails, render dog_list with the add_medicine_form
        # We will need to adjust manage_dogs later to be the primary display controller,
        # but for now, this route will render the template with the specific form.
        dogs = Dog.query.filter_by(rescue_id=g.current_rescue.id).order_by(Dog.name).all()
        return render_template('dog_list.html',
                               rescue=g.current_rescue,
                               dogs=dogs,
                               form_to_display=form,
                               current_form_action_url=url_for('add_medicine', dog_id=dog.id),
                               form_legend=f"Add Medicine for {dog.name}",
                               dog_being_edited=dog, # Context for which dog we are adding medicine
                               current_action='show_add_medicine_form')

    # --- Route for Editing Dog and Its Medicines ---
    @app.route('/dog/<string:dog_id>/edit-with-medicines', methods=['GET', 'POST'])
    @rescue_required
    def edit_dog_with_medicines(dog_id):
        dog = Dog.query.filter_by(id=dog_id, rescue_id=g.current_rescue.id).first_or_404()
        
        if request.method == 'POST':
            form = EditDogAndMedicinesForm(request.form) # For POST, use request.form
            if form.validate_on_submit():
                try:
                    # Update dog details
                    dog.name = form.name.data
                    dog.approx_age = form.approx_age.data
                    dog.updated_at = datetime.now(timezone.utc)

                    # Process medicines
                    existing_medicine_ids = {med.id for med in dog.medicines}
                    processed_medicine_ids = set()

                    for med_form in form.medicines.entries:
                        med_id = med_form.id.data
                        if med_id: # Existing medicine
                            processed_medicine_ids.add(med_id)
                            if med_form.delete.data: # Marked for deletion
                                med_to_delete = Medicine.query.get(med_id)
                                if med_to_delete and med_to_delete.dog_id == dog.id: # Ensure it belongs to this dog
                                    db.session.delete(med_to_delete)
                            else: # Update existing medicine
                                med_to_update = Medicine.query.get(med_id)
                                if med_to_update and med_to_update.dog_id == dog.id:
                                    med_to_update.name = med_form.name.data
                                    med_to_update.dosage = med_form.dosage.data
                                    med_to_update.frequency = med_form.frequency.data
                                    med_to_update.start_date = med_form.start_date.data
                                    med_to_update.end_date = med_form.end_date.data
                                    med_to_update.notes = med_form.notes.data
                                    med_to_update.updated_at = datetime.now(timezone.utc)
                        elif med_form.name.data: # New medicine (if name is provided)
                            new_med = Medicine(
                                name=med_form.name.data,
                                dosage=med_form.dosage.data,
                                frequency=med_form.frequency.data,
                                start_date=med_form.start_date.data,
                                end_date=med_form.end_date.data,
                                notes=med_form.notes.data,
                                dog_id=dog.id,
                                rescue_id=g.current_rescue.id
                            )
                            db.session.add(new_med)
                    
                    db.session.commit()
                    flash(f'{dog.name}\\\'s details and medicines updated successfully!', 'success')
                    return redirect(url_for('manage_dogs', dog_id=dog.id, action='view', _anchor=f'dog-{dog.id}-details')) # Redirect to view the dog
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error updating dog and medicines: {e}', 'danger')
            # If POST validation fails, 'form' has errors and will be passed to render_template below
        else: # GET request
            form = EditDogAndMedicinesForm()

            # Populate the main dog fields
            form.name.data = dog.name
            form.approx_age.data = dog.approx_age

            # Clear and populate the medicines FieldList
            while len(form.medicines.entries) > 0:
                form.medicines.pop_entry()

            for med in dog.medicines.order_by(Medicine.created_at).all():
                med_form = MedicineForm(obj=med)
                form.medicines.append_entry(med_form)

            # Add a blank entry for a new medicine
            form.medicines.append_entry()

        all_dogs = Dog.query.filter_by(rescue_id=g.current_rescue.id).order_by(Dog.name).all()
        return render_template('dog_list.html',
                               rescue=g.current_rescue,
                               dogs=all_dogs,
                               form_to_display=form,
                               current_form_action_url=url_for('edit_dog_with_medicines', dog_id=dog.id),
                               form_legend=f"Edit {dog.name} and Medicines",
                               dog_being_edited=dog,
                               current_action='show_edit_dog_medicines_form',
                               dog_for_form_id=dog.id)

    # --- Routes for Individual Medicine Deletion ---
    @app.route('/medicine/<string:med_id>/confirm-delete', methods=['GET'])
    @rescue_required
    def confirm_delete_medicine(med_id):
        medicine_to_delete = Medicine.query.filter_by(id=med_id, rescue_id=g.current_rescue.id).first_or_404()
        # We also need the dog for context in the confirmation message/redirect, though not strictly for deletion itself
        dog = Dog.query.filter_by(id=medicine_to_delete.dog_id, rescue_id=g.current_rescue.id).first_or_404()
        return render_template('partials/_confirm_delete_partial.html',
                               item_type="Medicine",
                               item_name=f"{medicine_to_delete.name} for {dog.name}",
                               confirm_action_url=url_for('delete_medicine', med_id=medicine_to_delete.id),
                               cancel_url=url_for('manage_dogs')) # Or perhaps a more specific cancel later with HTMX

    @app.route('/medicine/<string:med_id>/delete', methods=['POST'])
    @rescue_required
    def delete_medicine(med_id):
        medicine_to_delete = Medicine.query.filter_by(id=med_id, rescue_id=g.current_rescue.id).first_or_404()
        med_name = medicine_to_delete.name
        dog_name = medicine_to_delete.dog.name # For the flash message
        try:
            db.session.delete(medicine_to_delete)
            db.session.commit()
            flash(f'Medicine "{med_name}" for {dog_name} has been deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting medicine "{med_name}" for {dog_name}: {e}', 'danger')
        return redirect(url_for('manage_dogs')) # Redirect to the main list

    # --- Route for HTMX Dog Deletion Confirmation ---
    @app.route('/dog/<string:dog_id>/confirm-delete', methods=['GET'])
    @rescue_required
    def confirm_delete_dog(dog_id):
        dog_to_delete = Dog.query.filter_by(id=dog_id, rescue_id=g.current_rescue.id).first_or_404()
        return render_template('partials/_confirm_delete_partial.html', 
                               item_type="Dog", 
                               item_name=dog_to_delete.name,
                               confirm_action_url=url_for('delete_dog', dog_id=dog_to_delete.id),
                               cancel_url=url_for('clear_form_area'))

    # --- Route for HTMX to Clear the Form Area ---
    @app.route('/clear-form-area', methods=['GET'])
    @rescue_required
    def clear_form_area():
        return ""

    # --- Route for Deleting a Dog ---
    @app.route('/dog/<string:dog_id>/delete', methods=['POST'])
    @rescue_required
    def delete_dog(dog_id):
        dog_to_delete = Dog.query.filter_by(id=dog_id, rescue_id=g.current_rescue.id).first_or_404()
        dog_name = dog_to_delete.name # Store name for flash message before deleting
        try:
            db.session.delete(dog_to_delete)
            db.session.commit()
            flash(f'Dog "{dog_name}" has been deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting dog "{dog_name}": {e}', 'danger')
        return redirect(url_for('manage_dogs'))

    # --- Shell Context ---
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db, 'Rescue': Rescue, 'Dog': Dog}

    # --- Context Processors ---
    @app.context_processor
    def inject_current_info():
        # Inject current rescue name if selected
        current_rescue = None
        if 'selected_rescue_id' in session:
             # Try using g if available from decorator, otherwise fetch
             current_rescue = getattr(g, 'current_rescue', None)
             if not current_rescue:
                 current_rescue = db.session.get(Rescue, session['selected_rescue_id'])

        return {'current_rescue': current_rescue}


    return app