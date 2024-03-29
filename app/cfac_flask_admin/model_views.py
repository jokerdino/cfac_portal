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
