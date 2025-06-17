from flask import Blueprint

appointments_bp = Blueprint('appointments', __name__, url_prefix='')

# Appointment management routes will be moved here in Phase R4B