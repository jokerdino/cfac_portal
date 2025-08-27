from flask import Flask, request


from app.portal_admin.admin_routes import admin_check
from app.users.user_model import User
from config import Config, TestConfig
from extensions import admin, db, lm, migrate, toolbar

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
from app.lien import lien_bp
from app.escalation_matrix import em_bp

from app.leave_management import leave_mgmt_bp
from app.employee_leave_balance import leave_balance_bp

from app.mis_tracker import mis_bp

from app.brs_centralised_cheque import brs_cc_bp

from app.ri_page import ri_page_bp

from app.errors import errors_bp
from app.cfac_flask_admin import flask_admin_bp

from utils import datetime_format, humanize_datetime, indian_number_format


@lm.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.jinja_env.filters["datetime_format"] = datetime_format
    app.jinja_env.filters["humanize_datetime"] = humanize_datetime
    app.jinja_env.filters["indian_number_format"] = indian_number_format

    @app.context_processor
    def inject_active_page():
        return {"active_page": request.endpoint, "view_args": request.view_args or {}}

    # Initialize Flask extensions here

    lm.init_app(app)
    lm.login_view = "users.login_page"
    db.init_app(app)
    migrate.init_app(app, db)

    admin.init_app(app)

    toolbar.init_app(app)
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
    app.register_blueprint(lien_bp, url_prefix="/lien")
    app.register_blueprint(leave_mgmt_bp, url_prefix="/leave")
    app.register_blueprint(leave_balance_bp, url_prefix="/leave_balance")
    app.register_blueprint(brs_cc_bp, url_prefix="/brs_cc")
    app.register_blueprint(em_bp, url_prefix="/escalation_matrix")
    app.register_blueprint(ri_page_bp, url_prefix="/ri")

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
