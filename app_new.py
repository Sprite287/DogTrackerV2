import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_login import current_user

# Configuration and extensions
from config import config
from extensions import db, migrate, login_manager
from audit import init_audit

# Blueprints
from blueprints.auth.routes import auth_bp
from blueprints.dogs.routes import dogs_bp
from blueprints.appointments.routes import appointments_bp
from blueprints.medicines.routes import medicines_bp
from blueprints.admin.routes import admin_bp
from blueprints.api.routes import api_bp
from blueprints.calendar.routes import calendar_bp

# Core utilities
from blueprints.core.errors import register_error_handlers


def create_app(config_name=None):
    """Application factory pattern for creating Flask app instances."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Will change to auth.login in Phase R3
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # CSRF Protection
    csrf = CSRFProtect(app)
    
    # Rate Limiting
    def get_rate_limit_key():
        if current_user.is_authenticated:
            return str(current_user.get_id())
        return get_remote_address()
    
    limiter = Limiter(
        key_func=get_rate_limit_key,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        default_limits_per_method=True,
        default_limits_exempt_when=lambda: current_user.is_authenticated and current_user.is_rescue_admin()
    )
    
    # Mail
    mail = Mail(app)
    
    # Initialize Audit System (disable cleanup thread during migration)
    init_audit(app, start_cleanup_thread=False)
    
    # Register error handlers
    register_error_handlers(app)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Register blueprints (empty for now, routes will be moved in later phases)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dogs_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(medicines_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(calendar_bp)
    
    return app


# Create the app instance using the factory
app = create_app()

# Import all the existing routes from the original app.py (temporarily)
# This allows us to test the new structure while keeping all functionality
# Routes will be moved to blueprints in subsequent phases

from flask import render_template, request, jsonify, redirect, url_for, flash, render_template_string, get_flashed_messages, make_response, send_file, abort, g, session
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
from forms import LoginForm, RegistrationForm, RescueRegistrationForm, PasswordResetRequestForm, PasswordResetForm, AuditForm
from rescue_helpers import get_rescue_dogs, get_rescue_appointments, get_rescue_medicines, get_rescue_reminders, get_rescue_medicine_presets
from permissions import roles_required, role_required, rescue_access_required
from werkzeug.security import generate_password_hash
import secrets
from flask_wtf.csrf import CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import bleach
from flask_mail import Mail, Message
import warnings

# Note: All the route definitions from the original app.py will be imported here
# This is a temporary measure for Phase R1 to ensure the app continues to work
# Routes will be moved to blueprints in phases R2-R6
