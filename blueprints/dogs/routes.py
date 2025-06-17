from flask import Blueprint

dogs_bp = Blueprint('dogs', __name__, url_prefix='')

# Dog management routes will be moved here in Phase R4A