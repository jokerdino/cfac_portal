from flask import Blueprint

contacts_bp = Blueprint("contacts", __name__, template_folder="templates")

from app.contacts import contacts_routes
