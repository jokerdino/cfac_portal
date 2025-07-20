from flask import render_template, url_for, redirect

from flask_login import current_user, login_required

from app.escalation_matrix import em_bp
from .models import EscalationMatrix
from .forms import EscalationMatrixForm

from extensions import db
from set_view_permissions import admin_required


@em_bp.route("/")
@login_required
def list_escalation_matrix():
    list_escalation = db.session.scalars(db.select(EscalationMatrix))

    column_names = [column.name for column in EscalationMatrix.__table__.columns][1:9]
    enable_edit = True if current_user.user_type == "admin" else False

    return render_template(
        "em_list.html",
        list=list_escalation,
        enable_edit=enable_edit,
        column_names=column_names,
    )


@em_bp.route("/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_escalation_matrix():
    form = EscalationMatrixForm()

    if form.validate_on_submit():
        escalation = EscalationMatrix()
        form.populate_obj(escalation)
        db.session.add(escalation)
        db.session.commit()

        return redirect(url_for("escalation_matrix.list_escalation_matrix"))
    return render_template(
        "escalation_matrix_add.html", form=form, title="Add new escalation matrix"
    )


@em_bp.route("/edit/<int:key>/", methods=["GET", "POST"])
@login_required
@admin_required
def edit_escalation_matrix(key):
    escalation = db.get_or_404(EscalationMatrix, key)
    form = EscalationMatrixForm(obj=escalation)

    if form.validate_on_submit():
        form.populate_obj(escalation)
        db.session.commit()

        return redirect(url_for("escalation_matrix.list_escalation_matrix"))
    return render_template(
        "escalation_matrix_add.html", form=form, title="Edit escalation matrix"
    )
