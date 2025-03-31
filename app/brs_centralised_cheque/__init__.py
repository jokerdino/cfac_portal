from flask import Blueprint

brs_cc_bp = Blueprint("brs_cc", __name__, template_folder="templates")

from app.brs_centralised_cheque import routes
