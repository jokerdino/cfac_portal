from app.errors import errors_bp
from flask import render_template, redirect, url_for
from flask_login import current_user

@errors_bp.app_errorhandler(404)
def not_found_error(e):
    if current_user.is_authenticated:
        return render_template("404.html"), 404
    else:
        return redirect(url_for("users.login_page"))
