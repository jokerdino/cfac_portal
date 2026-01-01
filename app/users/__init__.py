from flask import Blueprint

user_bp = Blueprint("users", __name__, template_folder="templates")

from app.users import user_routes, admin_routes
