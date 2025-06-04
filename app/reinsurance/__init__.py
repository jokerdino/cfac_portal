from flask import Blueprint

reinsurance_bp = Blueprint("reinsurance", __name__, template_folder="templates")

from app.reinsurance import routes
