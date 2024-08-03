from datetime import datetime

from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.pool_credits import pool_credits_bp
from app.pool_credits.pool_credits_form import UpdatePoolCreditsForm
from app.pool_credits.pool_credits_model import PoolCredits


@pool_credits_bp.route("/unidentified/")
@login_required
def pool_credits_list_unidentified():

    from extensions import db

    query = (
        db.session.query(PoolCredits)
        .filter(PoolCredits.str_regional_office_code.is_(None))
        .order_by(PoolCredits.id.desc())
    )
    return render_template(
        "pool_credits_list.html",
        query=query,
        title="HDFC Pool account - List of unidentified entries",
    )


@pool_credits_bp.route("/identified/")
@login_required
def pool_credits_list_identified():

    from extensions import db

    query = (
        db.session.query(PoolCredits)
        .filter(PoolCredits.str_regional_office_code.is_not(None))
        .order_by(PoolCredits.id.desc())
    )
    return render_template(
        "pool_credits_list.html",
        query=query,
        title="HDFC Pool account - List of identified entries",
    )


@pool_credits_bp.route("/edit/<int:id>/", methods=["POST", "GET"])
@login_required
def update_pool_credit(id):
    from extensions import db

    entry = db.session.query(PoolCredits).get_or_404(id)
    form = UpdatePoolCreditsForm()
    if form.validate_on_submit():
        entry.date_updated_date = datetime.now()
        entry.updated_by = current_user.username
        entry.str_regional_office_code = form.str_regional_office_code.data
        entry.text_remarks = form.text_remarks.data
        db.session.commit()
        # flash("Entry has been updated.")
        return redirect(url_for("pool_credits.view_pool_credit", id=id))
    form.str_regional_office_code.data = entry.str_regional_office_code
    form.text_remarks.data = entry.text_remarks
    return render_template("pool_credits_edit.html", entry=entry, form=form)


@pool_credits_bp.route("/view/<int:id>/")
@login_required
def view_pool_credit(id):
    from extensions import db

    entry = db.session.query(PoolCredits).get_or_404(id)

    return render_template("pool_credits_view.html", entry=entry)
