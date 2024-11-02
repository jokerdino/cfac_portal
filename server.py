import calendar
from datetime import datetime

import humanize
from babel.numbers import format_decimal
from flask import Flask

from app.portal_admin.admin_routes import admin_check
from app.users.user_model import User
from config import Config, TestConfig
from extensions import admin, db, lm, migrate

from app.main import main_bp
from app.users import user_bp
from app.portal_admin import admin_bp
from app.coinsurance import coinsurance_bp
from app.brs import brs_bp
from app.contracts import contracts_bp
from app.contacts import contacts_bp
from app.tickets import tickets_bp
from app.bank_guarantee import bg_bp
from app.outstanding_expenses import os_bp
from app.funds import funds_bp
from app.announcements import announcements_bp
from app.knowledge_base import knowledge_base_bp
from app.ho_accounts import ho_accounts_bp
from app.ho_ro_recon import ho_ro_recon_bp
from app.pool_credits import pool_credits_bp
from app.budget import budget_bp
from app.pg_tieup import pg_tieup_bp

# from app.leave_management import leave_mgmt_bp

from app.mis_tracker import mis_bp

from app.errors import errors_bp
from app.cfac_flask_admin import flask_admin_bp


@lm.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def indian_number_format(input_number):
    return format_decimal(input_number, format="#####,##,##,##0.00", locale="en_IN")


def humanize_datetime(input_datetime):
    return humanize.naturaltime(datetime.now() - input_datetime)


def datetime_format(value, format="%H:%M %d-%m-%y", result="default"):
    return_value = datetime.strptime(value, format)
    if result == "default":
        return return_value
    elif result == "current":
        res = calendar.monthrange(return_value.year, return_value.month)
        date_string = f"{res[1]}/{return_value.month:02}/{return_value.year}"
        return date_string
    elif result == "previous":
        date_string = f"01/{return_value.month:02}/{return_value.year}"
        # if return_value.month - 1 == 0:
        #     res = calendar.monthrange(return_value.year - 1, 12)
        #     date_string = f"{res[1]}/12/{return_value.year-1}"
        # else:
        #     res = calendar.monthrange(return_value.year, return_value.month - 1)
        #     date_string = f"{res[1]}/{return_value.month - 1:02}/{return_value.year}"
        return date_string


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.jinja_env.filters["datetime_format"] = datetime_format
    app.jinja_env.filters["humanize_datetime"] = humanize_datetime
    app.jinja_env.filters["indian_number_format"] = indian_number_format

    # Initialize Flask extensions here

    lm.init_app(app)
    lm.login_view = "users.login_page"
    db.init_app(app)
    migrate.init_app(app, db)

    admin.init_app(app)

    # Register blueprints here

    app.register_blueprint(main_bp, url_prefix="/")

    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(admin_bp, url_prefix="/portal_admin")
    app.register_blueprint(coinsurance_bp, url_prefix="/coinsurance")
    app.register_blueprint(brs_bp, url_prefix="/brs")
    app.register_blueprint(contracts_bp, url_prefix="/contracts")
    app.register_blueprint(contacts_bp, url_prefix="/contacts")
    app.register_blueprint(tickets_bp, url_prefix="/tickets")
    app.register_blueprint(knowledge_base_bp, url_prefix="/knowledge_base")
    app.register_blueprint(bg_bp, url_prefix="/bg")
    app.register_blueprint(os_bp, url_prefix="/os")
    app.register_blueprint(funds_bp, url_prefix="/funds")
    app.register_blueprint(announcements_bp, url_prefix="/announcements")
    app.register_blueprint(mis_bp, url_prefix="/mis")
    app.register_blueprint(ho_accounts_bp, url_prefix="/ho_accounts")
    app.register_blueprint(ho_ro_recon_bp, url_prefix="/recon")
    app.register_blueprint(pool_credits_bp, url_prefix="/pool_credits")
    app.register_blueprint(budget_bp, url_prefix="/budget")
    app.register_blueprint(pg_tieup_bp, url_prefix="/pg_tieup")
    #   app.register_blueprint(leave_mgmt_bp, url_prefix="/leave")

    app.register_blueprint(errors_bp, url_prefix="/error")
    app.register_blueprint(flask_admin_bp, url_prefix="/admin")

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        #  db.drop_all()
        db.create_all()
        admin_check()
    #    app.run(debug=True)
    serve(app, host="0.0.0.0", port=8080)
    # app.run(debug=True, port=8080)
