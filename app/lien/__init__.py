from flask import Blueprint

lien_bp = Blueprint("lien", __name__, template_folder="templates")

from app.lien import lien_routes
