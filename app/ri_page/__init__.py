from flask import Blueprint

ri_page_bp = Blueprint("ri_page", __name__, template_folder="templates")

from app.ri_page import routes
