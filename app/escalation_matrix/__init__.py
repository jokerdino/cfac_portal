from flask import Blueprint

em_bp = Blueprint("escalation_matrix", __name__, template_folder="templates")

from app.escalation_matrix import routes
