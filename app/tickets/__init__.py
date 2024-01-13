from flask import Blueprint

tickets_bp = Blueprint("tickets", __name__, template_folder="templates")

from app.tickets import tickets_routes
