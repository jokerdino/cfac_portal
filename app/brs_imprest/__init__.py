from flask import Blueprint

brs_imprest_bp = Blueprint("brs_imprest", __name__, template_folder="templates")

from app.brs_imprest import routes
