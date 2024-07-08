from datetime import datetime
import calendar

from babel.numbers import format_decimal
import humanize

from flask import Flask

from waitress import serve

from app.portal_admin.admin_routes import admin_check
from app.users.user_model import User
from config import Config
from extensions import db, lm, migrate, admin


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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

    app.config["FLASK_ADMIN_SWATCH"] = "cerulean"

    admin.init_app(app)

    # Register blueprints here
    from app.main import main_bp

    app.register_blueprint(main_bp, url_prefix="/")

    from app.users import user_bp

    app.register_blueprint(user_bp, url_prefix="/user")

    from app.portal_admin import admin_bp

    app.register_blueprint(admin_bp, url_prefix="/portal_admin")

    from app.coinsurance import coinsurance_bp

    app.register_blueprint(coinsurance_bp, url_prefix="/coinsurance")

    from app.brs import brs_bp

    app.register_blueprint(brs_bp, url_prefix="/brs")

    from app.contracts import contracts_bp

    app.register_blueprint(contracts_bp, url_prefix="/contracts")

    from app.contacts import contacts_bp

    app.register_blueprint(contacts_bp, url_prefix="/contacts")

    from app.tickets import tickets_bp

    app.register_blueprint(tickets_bp, url_prefix="/tickets")

    from app.knowledge_base import knowledge_base_bp

    app.register_blueprint(knowledge_base_bp, url_prefix="/knowledge_base")

    from app.bank_guarantee import bg_bp

    app.register_blueprint(bg_bp, url_prefix="/bg")

    from app.outstanding_expenses import os_bp

    app.register_blueprint(os_bp, url_prefix="/os")

    from app.funds import funds_bp

    app.register_blueprint(funds_bp, url_prefix="/funds")

    from app.announcements import announcements_bp

    app.register_blueprint(announcements_bp, url_prefix="/announcements")

    from app.mis_tracker import mis_bp

    app.register_blueprint(mis_bp, url_prefix="/mis")

    from app.ho_accounts import ho_accounts_bp

    app.register_blueprint(ho_accounts_bp, url_prefix="/ho_accounts")

    from app.ho_ro_recon import ho_ro_recon_bp

    app.register_blueprint(ho_ro_recon_bp, url_prefix="/recon")

    from app.errors import errors_bp

    app.register_blueprint(errors_bp, url_prefix="/error")

    from app.cfac_flask_admin import flask_admin_bp

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
