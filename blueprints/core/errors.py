from flask import render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from audit import log_audit_event


def register_error_handlers(app):
    """Register all error handlers with the Flask app."""
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        print(f"[CSRF ERROR HANDLER] CSRF validation failed. Reason: {e.description}")
        print(f"[CSRF ERROR HANDLER] request.form content: {request.form}")
        # Log CSRF violation to audit log
        log_audit_event(
            user_id=getattr(current_user, 'id', None) if current_user.is_authenticated else None,
            rescue_id=getattr(current_user, 'rescue_id', None) if current_user.is_authenticated else None,
            action='csrf_violation',
            resource_type='Request',
            resource_id=None,
            details={
                'error_description': e.description,
                'path': request.path,
                'method': request.method,
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'remote_addr': request.remote_addr
            }
        )
        return render_template('error_404.html'), 400

    @app.errorhandler(429)
    def ratelimit_handler(e):
        # Log rate limit violation
        log_audit_event(
            user_id=getattr(current_user, 'id', None) if current_user.is_authenticated else None,
            rescue_id=getattr(current_user, 'rescue_id', None) if current_user.is_authenticated else None,
            action='rate_limit_exceeded',
            resource_type='Request',
            resource_id=None,
            details={
                'path': request.path,
                'method': request.method,
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'remote_addr': request.remote_addr,
                'error_description': str(e.description)
            }
        )
        return render_template('error_404.html'), 429

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error_404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error_500.html'), 500