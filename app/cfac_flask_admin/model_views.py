from flask_admin_models import DefaultModelView


class UserView(DefaultModelView):
    column_exclude_list = [
        "password",
    ]
    form_excluded_columns = ["password"]
    column_editable_list = ["reset_password", "oo_code", "username"]
    can_export = True
    column_filters = ["user_type"]


class BRSView(DefaultModelView):
    column_searchable_list = ["uiic_office_code", "month"]
    column_filters = ["uiic_office_code", "month"]
    can_export = True


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
