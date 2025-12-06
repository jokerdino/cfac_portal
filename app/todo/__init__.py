from flask import Blueprint

todo_bp = Blueprint("todo", __name__, template_folder="templates")

from app.todo import routes
