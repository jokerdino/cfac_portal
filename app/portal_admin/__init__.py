from flask import Blueprint

admin_bp = Blueprint("portal_admin", __name__, template_folder="templates")

from app.portal_admin import admin_routes
