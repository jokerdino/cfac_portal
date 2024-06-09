from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from app.main import main_bp

from app.tickets.tickets_routes import humanize_datetime
from app.announcements.announcements_model import Announcements
from app.mis_tracker.mis_model import MisTracker

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        query = Announcements.query.order_by(Announcements.created_on.desc()).limit(10)
        list = MisTracker.query.order_by(MisTracker.created_on.desc()).order_by(MisTracker.created_on.desc(), MisTracker.id.asc()).limit(19)
        return render_template("index.html", query=query, humanize_datetime=humanize_datetime, list=list)
    else:
        return redirect(url_for("users.login_page"))


@main_bp.route("/pos")
@login_required
def pos_dashboard():
    return render_template("pos_dashboard.html")
