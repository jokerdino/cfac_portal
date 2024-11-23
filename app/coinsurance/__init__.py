from flask import Blueprint

coinsurance_bp = Blueprint("coinsurance", __name__, template_folder="templates")

from app.coinsurance import coinsurance_routes, coinsurance_balances
