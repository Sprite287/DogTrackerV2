from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import AuditLog
from audit import get_audit_system_stats, _audit_batcher, cleanup_old_audit_logs
from forms import AuditForm
from blueprints.core.decorators import roles_required, role_required

admin_bp = Blueprint('admin', __name__, url_prefix='')

def get_current_user():
    """Get current authenticated user or None if not authenticated."""
    if current_user.is_authenticated:
        return current_user
    return None

@admin_bp.route('/admin/audit-logs', methods=['GET', 'POST'])
@roles_required(['superadmin', 'owner'])
def admin_audit_logs():
    current_user = get_current_user()
    page = int(request.args.get('page', 1))
    per_page = 25
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    audit_stats = get_audit_system_stats() if current_user.role == 'superadmin' else None
    flush_form = AuditForm()
    cleanup_form = AuditForm()
    return render_template('admin_audit_logs.html', logs=logs, current_user=current_user, audit_stats=audit_stats, flush_form=flush_form, cleanup_form=cleanup_form)

@admin_bp.route('/admin/flush-audit-batch', methods=['POST'])
@role_required('superadmin')
def admin_flush_audit_batch():
    print(f"[CSRF DEBUG /admin/flush-audit-batch] Session CSRF Token: {session.get('_csrf_token')}")
    print(f"[CSRF DEBUG /admin/flush-audit-batch] Form CSRF Token: {request.form.get('csrf_token')}")
    current_user = get_current_user()
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
    return redirect(url_for('admin.admin_audit_logs'))

@admin_bp.route('/admin/run-audit-cleanup', methods=['POST'])
@login_required
@role_required('superadmin')
def admin_run_audit_cleanup():
    audit_action = request.form.get('audit_action')
    if audit_action == 'cleanup':
        cleanup_old_audit_logs()
        flash('Audit logs cleanup initiated.', 'success')
    return redirect(url_for('admin.admin_audit_logs'))