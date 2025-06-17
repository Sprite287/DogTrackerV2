from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='')

# Admin routes will be moved here in Phase R5A