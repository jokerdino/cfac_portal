from flask import Blueprint

brs_bp = Blueprint("brs", __name__, template_folder="templates")

from app.brs import routes
