from flask import Blueprint

ho_accounts_bp = Blueprint("ho_accounts", __name__, template_folder="templates")

from app.ho_accounts import ho_accounts_routes
