from flask import Blueprint

medicines_bp = Blueprint('medicines', __name__, url_prefix='')

# Medicine management routes will be moved here in Phase R4C