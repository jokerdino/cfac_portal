from flask import Blueprint

mis_bp = Blueprint("mis", __name__, template_folder="templates")

from app.mis_tracker import mis_routes
