from flask import redirect, render_template, url_for
from flask_login import current_user

from app.main import main_bp


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html")
    else:
        return redirect(url_for("users.login_page"))
