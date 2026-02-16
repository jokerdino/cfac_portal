from flask import redirect, render_template, url_for
from flask_login import login_required

from . import auditor_certificate_bp
from .model import AuditorCertificate
from .form import AuditorCertificateForm
from extensions import db

from set_view_permissions import admin_required


@auditor_certificate_bp.route("/add/", methods=["GET", "POST"])
@login_required
@admin_required
def auditor_certificate_add():
    form = AuditorCertificateForm()

    if form.validate_on_submit():
        ac = AuditorCertificate()
        form.populate_obj(ac)
        db.session.add(ac)
        db.session.commit()

        return redirect(url_for(".auditor_certificate_view", id=ac.id))

    return render_template(
        "auditor_certificate_edit.html",
        form=form,
        title="Add auditor certificate request details",
    )


@auditor_certificate_bp.route("/view/<int:id>/")
@login_required
@admin_required
def auditor_certificate_view(id):
    ac = db.get_or_404(AuditorCertificate, id)

    return render_template("auditor_certificate_view.html", ac=ac)


@auditor_certificate_bp.route("/edit/<int:id>/", methods=["POST", "GET"])
@login_required
@admin_required
def auditor_certificate_edit(id):
    ac = db.get_or_404(AuditorCertificate, id)
    form = AuditorCertificateForm(obj=ac)

    if form.validate_on_submit():
        form.populate_obj(ac)
        db.session.commit()
        return redirect(url_for(".auditor_certificate_view", id=ac.id))

    return render_template(
        "auditor_certificate_edit.html",
        form=form,
        title="Edit auditor certificate request details",
    )


@auditor_certificate_bp.route("/")
@login_required
@admin_required
def auditor_certificate_list():
    ac_list = db.session.scalars(db.select(AuditorCertificate))
    column_names = [
        "ro_code",
        "ro_name",
        "purpose",
        "date_of_request",
        "bid_closing_date",
        "certificate_issued_date",
        "invoice_received_date",
        "invoice_date",
        "disbursement_date",
        "request_id",
        "date_of_payment",
        "utr_number",
    ]

    return render_template(
        "auditor_certificate_list.html", ac_list=ac_list, column_names=column_names
    )
