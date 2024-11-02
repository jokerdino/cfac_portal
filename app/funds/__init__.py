from flask import Blueprint

funds_bp = Blueprint("funds", __name__, template_folder="templates")

from app.funds import funds_routes, funds_jv, funds_reports
