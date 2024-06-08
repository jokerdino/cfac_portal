import datetime

from flask import redirect, render_template, url_for

from flask_login import current_user, login_required

from app.tickets.tickets_routes import humanize_datetime

from app.announcements import announcements_bp
from app.announcements.announcements_model import Announcements
from app.announcements.announcements_form import AnnouncementsForm

@announcements_bp.route("/add_message", methods=["GET", "POST"])
@login_required
def add_announcement():
    from extensions import db
    form = AnnouncementsForm()

    if form.validate_on_submit():
        title = form.data["title"]
        message = form.data["message"]
        created_by = current_user.username
        created_on = datetime.datetime.now()
        announcement = Announcements(txt_title=title, txt_message=message, created_by=created_by, created_on=created_on)
        db.session.add(announcement)
        db.session.commit()
        return redirect(url_for("announcements.view_announcements"))
    return render_template("add_announcement.html", form=form)

@announcements_bp.route("/view_announcements")
@login_required
def view_announcements():
    from extensions import db
    list = Announcements.query.order_by(Announcements.created_on.desc())
    return render_template("view_announcements.html", list=list, humanize_datetime=humanize_datetime)
