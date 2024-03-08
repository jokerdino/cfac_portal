from flask import redirect, url_for
from flask_login import current_user

from flask_admin.contrib import sqla
from flask_admin import expose, AdminIndexView


class DefaultModelView(sqla.ModelView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_type

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for("users.login_page"))


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_type

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for("users.login_page"))

    @expose("/")
    def index(self):
        if not current_user.is_authenticated and current_user.user_type == "admin":
            return redirect(url_for("users.login_page"))

        if current_user.user_type == "admin":
            return super().index()
        else:
            return redirect(url_for("main.index"))
