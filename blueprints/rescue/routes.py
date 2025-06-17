from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import Rescue

rescue_bp = Blueprint('rescue', __name__, url_prefix='')

@rescue_bp.route('/rescue-info')
@login_required
def rescue_info():
    print('--- Rescue Info Debug ---')
    print(f'User role: {current_user.role}')
    print(f'Request args: {dict(request.args)}')
    
    if current_user.role == 'superadmin':
        rescue_id = request.args.get('rescue_id', type=int)
        print(f'rescue_id from request: {rescue_id}')
        selected_rescue_id = rescue_id
        if rescue_id:
            rescue = Rescue.query.get_or_404(rescue_id)
            print(f'Found rescue: {rescue.name} (ID: {rescue.id})')
        else:
            print('No rescue_id provided')
            rescue = None
        rescues = Rescue.query.order_by(Rescue.name.asc()).all()
        print(f'Total rescues available: {len(rescues)}')
        return render_template('rescue_info.html', rescue=rescue, rescues=rescues, selected_rescue_id=selected_rescue_id)
    else:
        rescue = current_user.rescue
        print(f'Regular user rescue: {rescue.name if rescue else "None"}')
        return render_template('rescue_info.html', rescue=rescue)