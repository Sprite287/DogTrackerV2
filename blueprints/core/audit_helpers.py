from flask import request
from flask_login import current_user
from audit import log_audit_event


def log_crud_event(action, resource_type, resource_id=None, details=None, success=True, error_message=None):
    """
    Helper function to log CRUD operations with standard fields.
    
    Args:
        action: The action performed (create, read, update, delete)
        resource_type: The type of resource (Dog, Appointment, Medicine, etc.)
        resource_id: The ID of the resource
        details: Additional details about the operation
        success: Whether the operation succeeded
        error_message: Error message if operation failed
    """
    log_audit_event(
        user_id=getattr(current_user, 'id', None) if current_user.is_authenticated else None,
        rescue_id=getattr(current_user, 'rescue_id', None) if current_user.is_authenticated else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        success=success,
        error_message=error_message,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )


def log_permission_denied(required_permission, resource_type, resource_id=None, reason=None):
    """
    Helper function to log permission denied events.
    
    Args:
        required_permission: The permission that was required
        resource_type: The type of resource being accessed
        resource_id: The ID of the resource
        reason: Reason for denial (not_authenticated, role_mismatch, etc.)
    """
    log_audit_event(
        user_id=getattr(current_user, 'id', None) if current_user.is_authenticated else None,
        rescue_id=getattr(current_user, 'rescue_id', None) if current_user.is_authenticated else None,
        action='permission_denied',
        resource_type=resource_type,
        resource_id=resource_id,
        details={
            'required_permission': required_permission,
            'actual_role': getattr(current_user, 'role', None),
            'reason': reason,
            'endpoint': request.endpoint
        },
        success=False,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )


def log_authentication_event(action, success=True, error_message=None, details=None):
    """
    Helper function to log authentication events.
    
    Args:
        action: The authentication action (login, logout, register, password_reset, etc.)
        success: Whether the action succeeded
        error_message: Error message if action failed
        details: Additional details about the authentication event
    """
    log_audit_event(
        user_id=getattr(current_user, 'id', None) if current_user.is_authenticated else None,
        rescue_id=getattr(current_user, 'rescue_id', None) if current_user.is_authenticated else None,
        action=action,
        resource_type='Authentication',
        resource_id=None,
        details=details,
        success=success,
        error_message=error_message,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )


def log_medicine_preset_event(action, preset_id, rescue_id, success=True, error_message=None, details=None):
    """
    Helper function specifically for medicine preset activation/deactivation events.
    
    Args:
        action: The action (activate_preset, deactivate_preset)
        preset_id: The ID of the medicine preset
        rescue_id: The rescue ID this applies to
        success: Whether the action succeeded
        error_message: Error message if action failed
        details: Additional details
    """
    log_audit_event(
        user_id=getattr(current_user, 'id', None) if current_user.is_authenticated else None,
        rescue_id=rescue_id,
        action=action,
        resource_type='MedicinePreset',
        resource_id=preset_id,
        details=details,
        success=success,
        error_message=error_message,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )