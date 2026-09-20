from flask import Blueprint

fund_intimation_bp = Blueprint("fund_intimation", __name__, template_folder="templates")

from app.fund_intimation import routes
