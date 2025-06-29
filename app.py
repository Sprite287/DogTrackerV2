# Standard library imports
import os
import secrets

# Third-party imports
from dotenv import load_dotenv
from flask import Flask, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

# Local application imports
from audit import init_audit
from config import config
from extensions import db, migrate, login_manager
from models import User

# Load environment variables from .env if present
load_dotenv()

# Initialize Flask app with centralized configuration
config_name = os.getenv('FLASK_ENV', 'development')
app = Flask(__name__)
app.config.from_object(config[config_name])
config[config_name].init_app(app)

# Import blueprints
from blueprints.admin.routes import admin_bp
from blueprints.api.routes import api_bp
from blueprints.appointments.routes import appointments_bp
from blueprints.auth.routes import auth_bp
from blueprints.calendar.routes import calendar_bp
from blueprints.dogs.routes import dogs_bp
from blueprints.main.routes import main_bp
from blueprints.medicines.routes import medicines_bp
from blueprints.rescue.routes import rescue_bp
from blueprints.staff.routes import staff_bp

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dogs_bp)
app.register_blueprint(appointments_bp)
app.register_blueprint(medicines_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(rescue_bp)
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
from blueprints.auth.routes import init_limiter, init_mail

init_mail(mail)
init_limiter(limiter)

# Initialize Audit System
init_audit(app, start_cleanup_thread=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



@app.before_request
def generate_csp_nonce():
    g.csp_nonce = secrets.token_hex(16)

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
            f"style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'nonce-{nonce}'; "  # Apply nonce to styles too
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com; "
            "img-src 'self' data:;"
        )
    else:
        # Fallback CSP if nonce is not available (should not happen in normal flow)
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com https://fonts.gstatic.com; "
            "img-src 'self' data:;"
        )
    response.headers['Content-Security-Policy'] = csp_policy

    # Consider adding Permissions-Policy if you want to restrict browser features
    # response.headers['Permissions-Policy'] = "geolocation=(), microphone=(), camera=()"
    return response

if __name__ == '__main__':
    print('--- ROUTES REGISTERED ---')
    for rule in app.url_map.iter_rules():
        print(rule, rule.methods)
    print('-------------------------')
    app.run(debug=True, host='0.0.0.0') 