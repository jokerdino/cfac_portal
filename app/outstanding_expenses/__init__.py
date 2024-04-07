from flask import Blueprint

os_bp = Blueprint("outstanding_expenses", __name__, template_folder="templates")

from app.outstanding_expenses import os_routes
