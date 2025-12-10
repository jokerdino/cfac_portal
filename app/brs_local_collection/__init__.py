from flask import Blueprint

brs_local_collection = Blueprint("brs_local", __name__, template_folder="templates")

from app.brs_local_collection import routes
