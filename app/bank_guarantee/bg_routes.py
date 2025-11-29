from flask import (
    abort,
    redirect,
    render_template,
    url_for,
)

from flask_login import current_user, login_required


from . import bg_bp
from .bg_models import BankGuarantee
from .bg_form import BGForm

from extensions import db
from set_view_permissions import oo_user_only


@bg_bp.route("/")
@login_required
@oo_user_only
def bg_homepage():
    if current_user.user_type not in ["admin", "ro_user", "oo_user"]:
        abort(404)
    stmt = db.Select(BankGuarantee).order_by(BankGuarantee.id)
    if current_user.user_type in ["oo_user"]:
        stmt = stmt.where(BankGuarantee.oo_code == current_user.oo_code)
    elif current_user.user_type == "ro_user":
        stmt = stmt.where(BankGuarantee.ro_code == current_user.ro_code)

    bg_query = db.session.scalars(stmt).all()
    return render_template("bg_home.html", bg_query=bg_query)


@bg_bp.route("/add", methods=["GET"])
@login_required
@oo_user_only
def add_bg_entry():
    form = BGForm()
    # --- Prepopulate fields based on user type ---
    if current_user.user_type == "oo_user":
        form.ro_code.data = current_user.ro_code
        form.oo_code.data = current_user.oo_code

    elif current_user.user_type == "ro_user":
        form.ro_code.data = current_user.ro_code

    if form.validate_on_submit():
        bg = BankGuarantee()

        form.populate_obj(bg)
        db.session.add(bg)
        db.session.commit()
        return redirect(url_for("bg.view_bg_entry", bg_key=bg.id))
    return render_template(
        "add_bg_entry.html", form=form, title="Add Bank guarantee entry"
    )


@bg_bp.route("/edit/<int:bg_key>/", methods=["GET"])
@login_required
@oo_user_only
def edit_bg_entry(bg_key):
    bg = db.get_or_404(BankGuarantee, bg_key)
    bg.require_access(current_user)
    form = BGForm(obj=bg)

    if form.validate_on_submit():
        form.populate_obj(bg)
        db.session.commit()
        return redirect(url_for("bg.view_bg_entry", bg_key=bg.id))

    return render_template(
        "add_bg_entry.html", bg=bg, form=form, title="Edit bank guarantee entry"
    )


@bg_bp.route("/view/<int:bg_key>/")
@login_required
@oo_user_only
def view_bg_entry(bg_key):
    bg = db.get_or_404(BankGuarantee, bg_key)
    bg.require_access(current_user)
    return render_template("view_bg_entry.html", bg=bg)
