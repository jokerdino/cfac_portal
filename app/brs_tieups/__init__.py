from flask import Blueprint

brs_tieups_bp = Blueprint("brs_tieups", __name__, template_folder="templates")

from app.brs_tieups import routes
