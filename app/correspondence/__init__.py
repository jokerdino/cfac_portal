from flask import Blueprint

correspondence_bp = Blueprint("correspondence", __name__, template_folder="templates")

from app.correspondence import routes
