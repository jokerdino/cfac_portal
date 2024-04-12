from flask import (
    redirect,
    render_template,
    url_for,
)

from flask_login import current_user, login_required


from app.bank_guarantee import bg_bp
from app.bank_guarantee.bg_models import BankGuarantee
from app.bank_guarantee.bg_form import BGForm


@bg_bp.route("/", methods=["POST", "GET"])
@login_required
def bg_homepage():
    bg_query = BankGuarantee.query.order_by(BankGuarantee.id)
    if current_user.user_type in ["oo_user"]:
        bg_query = bg_query.filter(BankGuarantee.oo_code == current_user.oo_code)
    elif current_user.user_type == "ro_user":
        bg_query = bg_query.filter(BankGuarantee.ro_code == current_user.ro_code)

    return render_template("bg_home.html", bg_query=bg_query)


@bg_bp.route("/add", methods=["POST", "GET"])
@login_required
def add_bg_entry():
    from extensions import db

    form = BGForm()
    if form.validate_on_submit():
        if current_user.user_type == "oo_user":
            ro_code = current_user.ro_code
            oo_code = current_user.oo_code
        elif current_user.user_type == "ro_user":
            ro_code = current_user.ro_code
            oo_code = form.data["office_code"]

        elif current_user.user_type == "admin":
            ro_code = form.data["regional_code"]
            oo_code = form.data["office_code"]

        #  ro_code = form.data["regional_code"]
        # oo_code = form.data["office_code"]
        customer_name = form.data["customer_name"]
        customer_id = form.data["customer_id"]
        debit_amount = form.data["debit_amount"]
        credit_amount = form.data["credit_amount"]
        payment_id = form.data["payment_id"]
        date_of_payment = form.data["date_of_payment"]
        reason = form.data["reason"]
        course_of_action = form.data["course_of_action"]
        bg = BankGuarantee(
            ro_code=ro_code,
            oo_code=oo_code,
            customer_name=customer_name,
            customer_id=customer_id,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            payment_id=payment_id,
            date_of_payment=date_of_payment,
            reason=reason,
            course_of_action=course_of_action,
        )
        db.session.add(bg)
        db.session.commit()
        return redirect(url_for("bg.view_bg_entry", bg_key=bg.id))
    return render_template(
        "add_bg_entry.html", form=form, title="Add Bank guarantee entry"
    )


@bg_bp.route("/edit/<int:bg_key>", methods=["POST", "GET"])
@login_required
def edit_bg_entry(bg_key):
    from extensions import db

    bg = BankGuarantee.query.get_or_404(bg_key)
    form = BGForm()

    if form.validate_on_submit():
        if current_user.user_type == "admin":
            bg.ro_code = form.data["regional_code"]
            bg.oo_code = form.data["office_code"]
        elif current_user.user_type == "ro_user":
            bg.ro_code = current_user.ro_code
            bg.oo_code = form.data["office_code"]
        elif current_user.user_type == "oo_user":
            bg.ro_code = current_user.ro_code
            bg.oo_code = current_user.oo_code
        bg.customer_name = form.data["customer_name"]
        bg.customer_id = form.data["customer_id"]
        bg.debit_amount = form.data["debit_amount"]
        bg.credit_amount = form.data["credit_amount"]
        bg.payment_id = form.data["payment_id"]
        bg.date_of_payment = form.data["date_of_payment"]
        bg.reason = form.data["reason"]
        bg.course_of_action = form.data["course_of_action"]
        db.session.commit()
        return redirect(url_for("bg.view_bg_entry", bg_key=bg.id))

    form.regional_code.data = bg.ro_code
    form.office_code.data = bg.oo_code
    form.customer_name.data = bg.customer_name
    form.customer_id.data = bg.customer_id
    form.debit_amount.data = bg.debit_amount
    form.credit_amount.data = bg.credit_amount
    form.payment_id.data = bg.payment_id
    form.date_of_payment.data = bg.date_of_payment
    form.reason.data = bg.reason
    form.course_of_action.data = bg.course_of_action

    return render_template(
        "add_bg_entry.html", bg=bg, form=form, title="Edit bank guarantee entry"
    )


@bg_bp.route("/view/<int:bg_key>")
@login_required
def view_bg_entry(bg_key):
    bg = BankGuarantee.query.get_or_404(bg_key)
    return render_template("view_bg_entry.html", bg=bg)
