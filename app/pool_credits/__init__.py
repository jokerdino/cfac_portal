from flask import Blueprint

pool_credits_bp = Blueprint("pool_credits", __name__, template_folder="templates")

from app.pool_credits import pool_credits_routes
