from flask import Blueprint

pg_tieup_bp = Blueprint("pg_tieup", __name__, template_folder="templates")

from app.pg_tieup import pg_tieup_routes

# from flask import Blueprint

# pool_credits_bp = Blueprint("pool_credits", __name__, template_folder="templates")

# from app.pool_credits import pool_credits_routes
