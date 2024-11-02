from flask import Blueprint

leave_mgmt_bp = Blueprint("leave_management", __name__, template_folder="templates")

from . import leave_routes
