from flask import Blueprint

admin_bp = Blueprint("admin", __name__, template_folder="templates")

from app.admin import admin_routes
