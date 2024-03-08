from flask import Blueprint

flask_admin_bp = Blueprint("flask_admin_bp", __name__)

from app.cfac_flask_admin import routes
