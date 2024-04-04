from flask import Blueprint

bg_bp = Blueprint("bg", __name__, template_folder="templates")

from app.bank_guarantee import bg_routes
