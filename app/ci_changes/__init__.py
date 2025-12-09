from flask import Blueprint

ci_bp = Blueprint("ci", __name__, template_folder="templates")

from app.ci_changes import routes
