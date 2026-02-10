from flask import Blueprint

direct_debits_bp = Blueprint("direct_debit", __name__, template_folder="templates")

from app.direct_debits import routes
