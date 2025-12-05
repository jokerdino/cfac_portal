from datetime import date, timedelta


from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from app.main import main_bp


from app.announcements.announcements_model import Announcements
from app.mis_tracker.mis_model import MisTracker

from extensions import db


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        announcements = db.session.scalars(
            db.select(Announcements).order_by(Announcements.created_on.desc()).limit(3)
        )

        prev_month = date.today().replace(day=1) - timedelta(days=1)
        prev_month_string = prev_month.strftime("%B-%Y")

        mis = db.session.scalars(
            db.select(MisTracker)
            .where(MisTracker.txt_period == prev_month_string)
            .order_by(MisTracker.txt_mis_type.asc())
        )
        return render_template(
            "index.html",
            announcements=announcements,
            mis=mis,
        )
    else:
        return redirect(url_for("users.login_page"))


@main_bp.route("/pos")
@login_required
def pos_dashboard():
    return render_template("pos_dashboard.html")
