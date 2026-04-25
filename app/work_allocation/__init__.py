from flask import Blueprint

work_allocation_bp = Blueprint("work_allocation", __name__, template_folder="templates")

from app.work_allocation import routes
