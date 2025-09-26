from flask import Blueprint

kiosk_bp = Blueprint('kiosk', __name__)

from . import routes