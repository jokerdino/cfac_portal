from flask import Blueprint

contracts_bp = Blueprint("contracts", __name__, template_folder="templates")

from app.contracts import contracts_routes
