from flask import Blueprint

announcements_bp = Blueprint("announcements", __name__, template_folder="templates")

from app.announcements import announcements_routes
