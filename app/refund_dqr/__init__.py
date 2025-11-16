from flask import Blueprint

refund_dqr_bp = Blueprint("refund_dqr", __name__, template_folder="templates")

from app.refund_dqr import routes
