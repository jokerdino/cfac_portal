from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from app.main import main_bp


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html")
    else:
        return redirect(url_for("users.login_page"))


@main_bp.route("/pos")
@login_required
def pos_dashboard():
    return render_template("pos_dashboard.html")
