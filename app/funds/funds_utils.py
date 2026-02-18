from datetime import date, datetime
# from typing import TYPE_CHECKING


from extensions import db

from .funds_model import (
    FundDailySheet,
    FundAmountGivenToInvestment,
    FundMajorOutgo,
    FundBankAccountNumbers,
    FundBankStatement,
    FundDailyOutflow,
    FundOutflowLabel,
    FundFlagSheet,
)


# if TYPE_CHECKING:
#     from datetime import datetime


def get_daily_sheet(input_date: date) -> FundDailySheet:
    daily_sheet = db.session.scalar(
        db.select(FundDailySheet).where(FundDailySheet.date_current_date == input_date)
    )
    return daily_sheet


def date_or_pending_filter(date_field, status_field, target_date):
    return db.or_(
        date_field == target_date,
        db.and_(status_field == "Pending", date_field < target_date),
    )


def get_outflow_data(param_date):
    daily_sheet = get_daily_sheet(param_date)

    investment_list = db.session.scalars(
        db.select(FundAmountGivenToInvestment).where(
            date_or_pending_filter(
                FundAmountGivenToInvestment.date_expected_date_of_return,
                FundAmountGivenToInvestment.current_status,
                param_date,
            )
        )
    ).all()

    list_outgo = db.session.scalars(
        db.select(FundMajorOutgo).where(
            date_or_pending_filter(
                FundMajorOutgo.date_of_outgo, FundMajorOutgo.current_status, param_date
            )
        )
    ).all()

    return daily_sheet, investment_list, list_outgo


def get_previous_day_closing_balance_refactored(input_date, requirement):
    daily_sheet = db.session.scalar(
        db.select(FundDailySheet)
        .where(FundDailySheet.date_current_date < input_date)
        .order_by(FundDailySheet.date_current_date.desc())
    )
    if not daily_sheet:
        return 0

    return get_requirement(daily_sheet, requirement)


def get_inflow(input_date, inflow_description=None):
    query = db.select(
        db.func.sum(FundBankStatement.credit),
        db.func.sum(FundBankStatement.debit),
        db.func.sum(FundBankStatement.ledger_balance),
    ).where(FundBankStatement.date_uploaded_date == input_date)

    if inflow_description:
        query = query.where(FundBankStatement.flag_description == inflow_description)

    results = db.session.execute(query).first()
    total_credit, total_debit, total_ledger = results

    # Special handling for balances
    if inflow_description in ("HDFC OPENING BAL", "HDFC CLOSING BAL"):
        return total_ledger or 0

    return total_credit or 0


def get_outflow(input_date, description=None):
    query = db.select(db.func.sum(FundDailyOutflow.outflow_amount)).where(
        FundDailyOutflow.outflow_date == input_date
    )

    if description:
        query = query.where(FundDailyOutflow.outflow_description == description)

    total_outflow = db.session.scalar(query)
    return total_outflow or 0


def get_daily_summary_refactored(input_date, requirement):
    daily_sheet = get_daily_sheet(input_date)
    if not daily_sheet:
        return 0

    return get_requirement(daily_sheet, requirement)


def get_requirement(daily_sheet, requirement):
    requirement_dict = {
        "net_investment": daily_sheet.get_net_investment,
        "hdfc_closing_balance": daily_sheet.float_amount_hdfc_closing_balance or 0,
        "investment_closing_balance": daily_sheet.float_amount_investment_closing_balance
        or 0,
        "investment_given": daily_sheet.float_amount_given_to_investments or 0,
        "investment_taken": daily_sheet.float_amount_taken_from_investments or 0,
    }

    return requirement_dict.get(requirement, 0)


def get_inflow_total(input_date):
    inflow_total = (
        (get_inflow(input_date) or 0)
        + (
            get_previous_day_closing_balance_refactored(
                input_date, "hdfc_closing_balance"
            )
            or 0
        )
        - (get_daily_summary_refactored(input_date, "investment_taken"))
    )

    return inflow_total or 0


def get_ibt_details(outflow_description):
    outflow = db.session.scalar(
        db.select(FundBankAccountNumbers).where(
            FundBankAccountNumbers.outflow_description == outflow_description
        )
    )

    return outflow


def handle_outflow_form_submission(form, param_date, daily_sheet):
    for key, amount in form.data.items():
        if ("amount" in key) and (amount is not None):
            create_or_update_outflow(param_date, key, amount)

    amount_given = form.data.get("given_to_investment", 0)
    expected_date = form.data.get("expected_date_of_return")

    if amount_given > 0 and expected_date:
        update_given_to_investment_entry(param_date, amount_given, expected_date)

    update_daily_sheet_with_outflow(daily_sheet, param_date, amount_given)
    db.session.commit()


def update_given_to_investment_entry(param_date, amount, expected_date):
    entry = db.session.scalar(
        db.select(FundAmountGivenToInvestment)
        .where(FundAmountGivenToInvestment.date_given_to_investment == param_date)
        .order_by(FundAmountGivenToInvestment.date_expected_date_of_return)
    )

    total_investment = db.session.scalar(
        db.select(
            db.func.coalesce(
                db.func.sum(
                    FundAmountGivenToInvestment.float_amount_given_to_investment
                ),
                0,
            )
        ).where(FundAmountGivenToInvestment.date_given_to_investment == param_date)
    )

    if not entry:
        new_entry = FundAmountGivenToInvestment(
            date_given_to_investment=param_date,
            float_amount_given_to_investment=amount,
            text_remarks=f"From daily sheet {param_date.strftime('%d/%m/%Y')}",
            date_expected_date_of_return=expected_date,
            current_status="Pending",
        )
        db.session.add(new_entry)
    elif total_investment != amount:
        entry.date_expected_date_of_return = expected_date
        entry.float_amount_given_to_investment += amount - total_investment


def update_daily_sheet_with_outflow(daily_sheet, param_date, amount_given):
    daily_sheet.float_amount_given_to_investments = amount_given
    drawn_amount = get_inflow(param_date, "Drawn from investment")
    daily_sheet.float_amount_taken_from_investments = drawn_amount

    daily_sheet.float_amount_investment_closing_balance = (
        get_previous_day_closing_balance_refactored(
            param_date, "investment_closing_balance"
        )
        + amount_given
        - drawn_amount
    )

    daily_sheet.float_amount_hdfc_closing_balance = (
        get_previous_day_closing_balance_refactored(param_date, "hdfc_closing_balance")
        + get_inflow(param_date)
        - get_outflow(param_date)
        - amount_given
    )


def populate_outflow_form_data(form, param_date, daily_sheet):
    # Fetch all outflows for the given date in one query
    outflow_entries = db.session.scalars(
        db.select(FundDailyOutflow).where(FundDailyOutflow.outflow_date == param_date)
    )

    # Build lookup dict: { "item_name": amount }
    outflow_map = {
        entry.outflow_description: entry.outflow_amount for entry in outflow_entries
    }

    outflow_labels = db.session.scalars(db.select(FundOutflowLabel.outflow_label)).all()
    outflow_amounts = [
        f"amount_{field.lower().replace(' ', '_')}" for field in outflow_labels
    ]

    # Populate form from the dict (no more DB hits)
    for item in outflow_amounts:
        form[item].data = outflow_map.get(item, 0)

    # form.given_to_investment.data = daily_sheet.float_amount_given_to_investments or 0
    form.given_to_investment.data = (
        getattr(daily_sheet, "float_amount_given_to_investments", 0) or 0
    )

    entry = db.session.scalar(
        db.select(FundAmountGivenToInvestment)
        .where(FundAmountGivenToInvestment.date_given_to_investment == param_date)
        .order_by(FundAmountGivenToInvestment.date_expected_date_of_return)
    )

    if entry:
        form.expected_date_of_return.data = entry.date_expected_date_of_return


def enable_update(input_date: datetime) -> bool:
    return date.today() == input_date.date()


def create_or_update_outflow(outflow_date, outflow_description, outflow_amount):
    outflow = db.session.scalar(
        db.select(FundDailyOutflow).where(
            (FundDailyOutflow.outflow_date == outflow_date)
            & (FundDailyOutflow.outflow_description == outflow_description)
        )
    )

    if not outflow:
        outflow = FundDailyOutflow(
            outflow_date=outflow_date,
            outflow_description=outflow_description,
        )

        db.session.add(outflow)
    outflow.outflow_amount = outflow_amount
    db.session.commit()


def fetch_flags():
    return db.select(
        FundFlagSheet.flag_description.distinct().label("flag_description")
    ).subquery()


def fetch_inflow(param_date):
    flags = fetch_flags()
    return db.session.execute(
        db.select(
            flags.c.flag_description.label("flag_description"),
            db.func.sum(db.func.coalesce(FundBankStatement.credit, 0)).label("amount"),
        )
        .select_from(flags)
        .outerjoin(
            FundBankStatement,
            db.and_(
                flags.c.flag_description == FundBankStatement.flag_description,
                FundBankStatement.date_uploaded_date == param_date,
            ),
        )
        .where(
            flags.c.flag_description.not_in(["HDFC CLOSING BAL", "HDFC OPENING BAL"]),
        )
        .group_by(flags.c.flag_description)
    ).all()


def fetch_outflow_labels():
    return db.session.scalars(db.select(FundOutflowLabel.outflow_label)).all()


def fetch_prev_daily_sheet(param_date):
    return db.session.scalar(
        db.select(FundDailySheet)
        .where(FundDailySheet.date_current_date < param_date)
        .order_by(FundDailySheet.date_current_date.desc())
    )
