from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from models import User, Rescue
from blueprints.core.decorators import roles_required
import secrets
import bleach
from extensions import db

staff_bp = Blueprint('staff', __name__, url_prefix='')

@staff_bp.route('/staff-management')
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

@staff_bp.route('/staff-management/add', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def add_staff_member():
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
    return jsonify({'success': True, 'id': user.id, 'name': name, 'email': email, 'role': role, 'password': password})

@staff_bp.route('/staff-management/edit', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def edit_staff_member():
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

@staff_bp.route('/staff-management/toggle-active', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def toggle_staff_active():
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

@staff_bp.route('/staff-management/delete', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def delete_staff_member():
    user_id = request.form.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    if current_user.role != 'superadmin' and user.rescue_id != current_user.rescue_id:
        return jsonify({'success': False, 'error': 'Permission denied.'}), 403
    if user.id == current_user.id or user.role == 'superadmin':
        return jsonify({'success': False, 'error': 'Cannot delete this user.'}), 403
    
    # Check if user has any associated records that would prevent deletion
    from models import DogNote, AuditLog, DogMedicineHistory
    
    # Check for dog notes created by this user
    dog_notes_count = DogNote.query.filter_by(user_id=user.id).count()
    if dog_notes_count > 0:
        return jsonify({
            'success': False, 
            'error': f'Cannot delete user. They have created {dog_notes_count} dog note(s). Transfer ownership first or contact administrator.'
        }), 400
    
    # Check for medicine history records given by this user
    medicine_history_count = DogMedicineHistory.query.filter_by(given_by=user.id).count()
    if medicine_history_count > 0:
        return jsonify({
            'success': False, 
            'error': f'Cannot delete user. They have administered {medicine_history_count} medicine dose(s). Transfer ownership first or contact administrator.'
        }), 400
    
    # Check for audit logs created by this user
    audit_logs_count = AuditLog.query.filter_by(user_id=user.id).count()
    if audit_logs_count > 0:
        return jsonify({
            'success': False, 
            'error': f'Cannot delete user. They have {audit_logs_count} audit log entries. Contact administrator for data archival first.'
        }), 400
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@staff_bp.route('/staff-management/reset-password', methods=['POST'])
@login_required
@roles_required(['superadmin', 'owner', 'admin'])
def reset_staff_password():
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