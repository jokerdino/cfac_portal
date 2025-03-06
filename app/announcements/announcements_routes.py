from flask import redirect, render_template, url_for

from flask_login import login_required

from set_view_permissions import admin_required

from app.announcements import announcements_bp
from app.announcements.announcements_model import Announcements
from app.announcements.announcements_form import AnnouncementsForm


@announcements_bp.route("/add/", methods=["GET", "POST"])
@login_required
@admin_required
def add_announcement():
    from extensions import db

    form = AnnouncementsForm()

    if form.validate_on_submit():
        announcement = Announcements()
        form.populate_obj(announcement)
        db.session.add(announcement)
        db.session.commit()

        return redirect(url_for("announcements.view_announcements"))
    return render_template("add_announcement.html", form=form)


@announcements_bp.route("/")
@login_required
def view_announcements():
    from extensions import db

    list = db.session.scalars(
        db.select(Announcements).order_by(Announcements.created_on.desc())
    )
    return render_template(
        "view_announcements.html",
        list=list,
    )
