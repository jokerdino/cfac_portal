from flask_admin_models import DefaultModelView


class LienView(DefaultModelView):
    can_export = True


class UserView(DefaultModelView):
    column_exclude_list = [
        "password",
    ]
    form_excluded_columns = ["password"]
    column_editable_list = ["reset_password", "oo_code", "username", "display_name"]
    can_export = True
    column_filters = ["user_type"]


class BRSView(DefaultModelView):
    column_searchable_list = ["uiic_office_code", "month"]
    column_filters = ["uiic_office_code", "month"]
    can_export = True
    column_editable_list = [
        "cash_bank",
        "cheque_bank",
        "pos_bank",
        "pg_bank",
        "bbps_bank",
        "dqr_bank",
        "local_collection_bank",
    ]
    form_excluded_columns = ("brs_month", "timestamp")


class BRSCCDetailView(DefaultModelView):
    column_editable_list = ["brs_status"]
    form_excluded_columns = ("unencashed_cheques", "stale_cheques")


class OSView(DefaultModelView):
    column_searchable_list = ["str_operating_office_code"]
    column_filters = ["str_operating_office_code"]


class FundBankStatementView(DefaultModelView):
    column_searchable_list = ["flag_description", "description"]


class ReconSummaryView(DefaultModelView):
    can_export = True
    column_editable_list = [
        "input_float_ro_balance",
        "input_float_ho_balance",
        "input_ro_balance_dr_cr",
        "input_ho_balance_dr_cr",
    ]
    column_searchable_list = ["str_period", "str_regional_office_code"]


class PoolCreditView(DefaultModelView):
    column_searchable_list = ["description"]


class BudgetAllocationView(DefaultModelView):
    column_searchable_list = ["str_expense_head", "str_ro_code"]
    column_filters = ["str_expense_head", "str_ro_code"]


class BudgetUtilizationView(DefaultModelView):
    column_searchable_list = ["str_expense_head", "str_ro_code"]
    column_filters = ["str_expense_head", "str_ro_code"]
