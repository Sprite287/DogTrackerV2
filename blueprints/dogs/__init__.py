from flask import Blueprint

dogs_bp = Blueprint('dogs', __name__, url_prefix='')

from . import routes