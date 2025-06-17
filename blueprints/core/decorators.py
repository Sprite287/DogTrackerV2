from functools import wraps
from flask import abort, request
from flask_login import current_user
from audit import log_audit_event


def roles_required(roles):
    """
    Decorator to require the current user to have one of the specified roles.
    Usage: @roles_required(['admin', 'owner'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                log_audit_event(
                    user_id=getattr(current_user, 'id', None) if current_user.is_authenticated else None,
                    rescue_id=getattr(current_user, 'rescue_id', None) if current_user.is_authenticated else None,
                    action='permission_denied',
                    resource_type='Route',
                    resource_id=request.endpoint,
                    details={
                        'required_roles': roles,
                        'actual_role': getattr(current_user, 'role', None),
                        'reason': 'not_authenticated' if not current_user.is_authenticated else 'role_mismatch'
                    },
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    success=False
                )
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(role):
    """
    Decorator to require the current user to have a specific role.
    Usage: @role_required('superadmin')
    """
    return roles_required([role])


def rescue_access_required(get_rescue_id_func):
    """
    Decorator to require the current user to have access to a specific rescue.
    Pass a function that returns the rescue_id for the resource being accessed.
    Usage:
        @rescue_access_required(lambda kwargs: Dog.query.get(kwargs['dog_id']).rescue_id)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                log_audit_event(
                    user_id=None,
                    rescue_id=None,
                    action='permission_denied',
                    resource_type='Route',
                    resource_id=request.endpoint,
                    details={
                        'required': 'authenticated',
                        'reason': 'not_authenticated'
                    },
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    success=False
                )
                abort(403)
            rescue_id = get_rescue_id_func(kwargs)
            if not current_user.is_superadmin() and current_user.rescue_id != rescue_id:
                log_audit_event(
                    user_id=getattr(current_user, 'id', None),
                    rescue_id=getattr(current_user, 'rescue_id', None),
                    action='permission_denied',
                    resource_type='Route',
                    resource_id=request.endpoint,
                    details={
                        'required_rescue_id': rescue_id,
                        'actual_rescue_id': getattr(current_user, 'rescue_id', None),
                        'actual_role': getattr(current_user, 'role', None),
                        'reason': 'rescue_mismatch'
                    },
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    success=False
                )
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator