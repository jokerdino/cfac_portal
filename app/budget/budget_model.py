from extensions import db


class BudgetAllocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    str_financial_year = db.Column(db.String)
    str_type = db.Column(db.String)  # original, revised
    str_ro_code = db.Column(db.String)

    str_expense_head = db.Column(db.String)
    int_budget_allocated = db.Column(db.Numeric(15, 2))

    # meta data
    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)


class BudgetUtilization(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    str_financial_year = db.Column(db.String)
    str_quarter = db.Column(db.String)  # first, second, third, fourth
    str_ro_code = db.Column(db.String)

    str_expense_head = db.Column(db.String)
    int_budget_utilized = db.Column(db.Numeric(15, 2))

    # meta data
    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)
