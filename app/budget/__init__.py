from flask import Blueprint

budget_bp = Blueprint("budget", __name__, template_folder="templates")

from app.budget import budget_routes
