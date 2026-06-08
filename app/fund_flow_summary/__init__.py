from flask import Blueprint

ff_summary_bp = Blueprint("ff_summary_bp", __name__, template_folder="templates")

from app.fund_flow_summary import routes
