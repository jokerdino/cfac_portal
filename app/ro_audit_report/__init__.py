from flask import Blueprint

ro_audit_report_bp = Blueprint("ro_audit", __name__, template_folder="templates")

from app.ro_audit_report import routes
