# DogTrackerV2/app.py
import os
import uuid # Added for UUID validation potentially
from flask import Flask, render_template, redirect, url_for, session, abort, g, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from functools import wraps # For decorator

# Import configurations and db instance
from config import config_by_name
from models import db, Rescue # Import db and initial models

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
        rescue_id = session.get('selected_rescue_id')
        if not rescue_id:
            return redirect(url_for('select_rescue'))

        # Fetch the specific rescue for the welcome message
        rescue = db.session.get(Rescue, rescue_id) # Use db.session.get for primary key lookup
        if not rescue:
            # If ID in session is somehow invalid, clear session and redirect
            session.pop('selected_rescue_id', None)
            return redirect(url_for('select_rescue'))

        return render_template('welcome.html', rescue=rescue)

    @app.route('/select_rescue')
    def select_rescue():
        # Clear session just in case before selection
        # session.pop('selected_rescue_id', None) # Optional: force re-selection
        rescues = Rescue.query.order_by(Rescue.name).all()
        return render_template('select_rescue.html', rescues=rescues)

    @app.route('/set_rescue/<uuid_string:rescue_id>') # Use converter for basic format check
    def set_rescue(rescue_id):
        # Convert string UUID from URL back to hex string if needed (converter handles format)
        rescue_id_hex = str(rescue_id) # Get the hex string
        rescue = db.session.get(Rescue, rescue_id_hex)
        if rescue:
            session['selected_rescue_id'] = rescue_id_hex
            # Optionally store name too, prevents DB hit on every request for welcome msg?
            # session['selected_rescue_name'] = rescue.name
            return redirect(url_for('welcome'))
        else:
            # Invalid rescue ID provided in URL
            abort(404) # Or flash message and redirect

    @app.route('/home')
    @rescue_required # Protect this route
    def home():
        # The decorator handles the session check and makes g.current_rescue available
        # Later, fetch reminders for g.current_rescue.id
        return render_template('home.html', rescue=g.current_rescue)

    # --- Other Routes Will Go Here (Dogs, Meds, Appts) ---
    # Example:
    # @app.route('/dogs')
    # @rescue_required
    # def list_dogs():
    #    dogs = Dog.query.filter_by(rescue_id=g.current_rescue.id).all()
    #    return render_template('dog_list.html', dogs=dogs, rescue=g.current_rescue)


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