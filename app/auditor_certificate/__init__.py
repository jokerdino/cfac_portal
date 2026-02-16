from flask import Blueprint

auditor_certificate_bp = Blueprint(
    "auditor_certificate", __name__, template_folder="templates"
)

from app.auditor_certificate import routes
