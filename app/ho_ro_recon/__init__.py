from flask import Blueprint

ho_ro_recon_bp = Blueprint("ho_ro_recon", __name__, template_folder="templates")

from app.ho_ro_recon import ho_ro_recon_routes
