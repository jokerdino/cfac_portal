from flask import Blueprint

leave_balance_bp = Blueprint(
    "employee_leave_balance", __name__, template_folder="templates"
)

from . import routes
