from flask import Blueprint

knowledge_base_bp = Blueprint("knowledge_base", __name__, template_folder="templates")

from app.knowledge_base import knowledge_base_routes
