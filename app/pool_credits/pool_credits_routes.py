from datetime import datetime

from sqlalchemy import func, distinct, select, create_engine, case

from flask import abort, flash, redirect, render_template, url_for, request
from flask_login import current_user, login_required

from sqlalchemy import cast, String

from app.pool_credits import pool_credits_bp
from app.pool_credits.pool_credits_form import UpdatePoolCreditsForm
from app.pool_credits.pool_credits_model import PoolCredits


# @pool_credits_bp.route("/unidentified/")
# @login_required
# def pool_credits_list_unidentified():

#     from extensions import db

#     query = (
#         db.session.query(PoolCredits)
#         .filter(PoolCredits.str_regional_office_code.is_(None))
#         .order_by(PoolCredits.id.desc())
#     )
#     return render_template(
#         "pool_credits_list.html",
#         query=query,
#         title="HDFC Pool account - List of unidentified entries",
#     )


# @pool_credits_bp.route("/identified/")
# @login_required
# def pool_credits_list_identified():

#     from extensions import db

#     query = (
#         db.session.query(PoolCredits)
#         .filter(
#             (PoolCredits.str_regional_office_code.is_not(None))
#             & (PoolCredits.bool_jv_passed == False)
#         )
#         .order_by(PoolCredits.id.desc())
#     )
#     return render_template(
#         "pool_credits_list.html",
#         query=query,
#         title="HDFC Pool account - List of identified entries",
#     )


@pool_credits_bp.route("/list/<string:status>/", methods=["POST", "GET"])
@login_required
def pool_credits_list_identified_api(status):
    from extensions import db

    if request.method == "POST":

        list_pool_keys = request.form.getlist("pool_keys")
        updated_time = datetime.now()
        for key in list_pool_keys:
            pool_credit_entry = PoolCredits.query.get_or_404(key)
            pool_credit_entry.bool_jv_passed = True
            pool_credit_entry.jv_passed_by = current_user.username
            pool_credit_entry.jv_passed_on = updated_time
            db.session.commit()

    return render_template("pool_credits_list_ajax.html", status=status)


@pool_credits_bp.route("/api/data/<string:status>/", methods=["GET"])
def get_data(status):
    from extensions import db

    if status == "unidentified":
        entries = db.session.query(PoolCredits).filter(
            PoolCredits.str_regional_office_code.is_(None)
        )

    elif status == "identified":
        entries = db.session.query(PoolCredits).filter(
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed.is_(False))
        )
    elif status == "jv_passed":
        entries = db.session.query(PoolCredits).filter(
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed.is_(True))
        )

    entries_count = entries.count()

    # search filter
    # TODO: add more parameters for searching
    search = request.args.get("search[value]")
    if search:
        entries = entries.filter(
            db.or_(
                cast(PoolCredits.book_date, String).like(f"%{search}%"),
                PoolCredits.description.ilike(f"%{search}%"),
                cast(PoolCredits.credit, String).like(f"%{search}%"),
                cast(PoolCredits.debit, String).like(f"%{search}%"),
                cast(PoolCredits.value_date, String).like(f"%{search}%"),
                PoolCredits.reference_no.ilike(f"%{search}%"),
                cast(PoolCredits.str_regional_office_code, String).like(f"%{search}%"),
            )
        )

    total_filtered = entries.count()

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f"order[{i}][column]")
        if col_index is None:
            break
        col_name = request.args.get(f"columns[{col_index}][data]")
        descending = request.args.get(f"order[{i}][dir]") == "desc"
        col = getattr(PoolCredits, col_name)
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        entries = entries.order_by(*order)

    # pagination
    start = request.args.get("start", type=int)
    length = request.args.get("length", type=int)
    entries = entries.offset(start).limit(length)

    # response
    return {
        "data": [entry.to_dict() for entry in entries],
        "recordsFiltered": total_filtered,
        "recordsTotal": entries_count,
        "draw": request.args.get("draw", type=int),
    }


@pool_credits_bp.route("/edit/<int:id>/", methods=["POST", "GET"])
@login_required
def update_pool_credit(id):
    from extensions import db

    #    id = int(id)
    entry = db.session.query(PoolCredits).get_or_404(id)
    form = UpdatePoolCreditsForm()
    if current_user.user_type != "admin":
        form.str_regional_office_code.choices = [current_user.ro_code]
    if entry.bool_jv_passed == True:
        flash("JV has already been passed.")
    elif form.validate_on_submit():
        entry.date_updated_date = datetime.now()
        entry.updated_by = current_user.username
        entry.str_regional_office_code = form.str_regional_office_code.data
        entry.text_remarks = form.text_remarks.data
        db.session.commit()

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


@pool_credits_bp.route("/summary/")
@login_required
def view_pool_credit_summary():
    from extensions import db

    case_unidentified = case(
        (
            PoolCredits.str_regional_office_code.is_(None),
            PoolCredits.credit,
        ),
        else_=0,
    ).label("Unidentified")

    case_identified = case(
        (
            (PoolCredits.str_regional_office_code.is_not(None))
            & (PoolCredits.bool_jv_passed == False),
            PoolCredits.credit,
        ),
        else_=0,
    ).label("Identified")

    case_jv_passed = case(
        (
            PoolCredits.bool_jv_passed == True,
            PoolCredits.credit,
        ),
        else_=0,
    ).label("JV passed")

    summary_query = (
        db.session.query(PoolCredits)
        .with_entities(
            func.date_trunc("month", PoolCredits.value_date),
            func.date_trunc("year", PoolCredits.value_date),
            func.sum(case_unidentified),
            func.sum(case_identified),
            func.sum(case_jv_passed),
        )
        .group_by(
            func.date_trunc("month", PoolCredits.value_date),
            func.date_trunc("year", PoolCredits.value_date),
        )
        .order_by(
            func.date_trunc("month", PoolCredits.value_date).desc(),
            func.date_trunc("year", PoolCredits.value_date).desc(),
        )
    )

    return render_template("summary_view.html", query=summary_query)
