# import logging
from logging.config import dictConfig


from flask import Flask, request, current_app, g
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from app.portal_admin.admin_routes import admin_check
from app.users.user_model import User
from app.todo.models import Notification
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
from app.todo import todo_bp

from app.leave_management import leave_mgmt_bp
from app.employee_leave_balance import leave_balance_bp

from app.mis_tracker import mis_bp

from app.brs_centralised_cheque import brs_cc_bp
from app.correspondence import correspondence_bp
from app.refund_dqr import refund_dqr_bp
from app.ri_page import ri_page_bp

from app.ci_changes import ci_bp

from app.errors import errors_bp
from app.cfac_flask_admin import flask_admin_bp

from utils import datetime_format, humanize_datetime, indian_number_format
from reset_table_id import reset_id


dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
        "loggers": {"werkzeug": {"level": "WARNING", "propagate": False}},
    }
)


@lm.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Trust the proxy headers from nginx
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    @app.before_request
    def log_request_metadata_only():
        log = current_app.logger
        # Safe username retrieval
        if current_user.is_authenticated:
            user = current_user.username  # or current_user.get_id()
        else:
            user = "anonymous"
        if request.files:
            files_info = []
            for field, storage in request.files.items():
                # Try to get size from stream
                try:
                    # Move cursor to end to find size
                    pos = storage.stream.tell()
                    storage.stream.seek(0, 2)  # Go to end of file
                    size = storage.stream.tell()
                    storage.stream.seek(pos)  # Reset the cursor
                except Exception:
                    size = None

                files_info.append(
                    {
                        "field": field,
                        "filename": storage.filename,
                        "size": size,
                        "mimetype": storage.mimetype,
                    }
                )

            log.info(
                f"File upload detected | "
                f"IP: {request.remote_addr} | "
                f"User: {user} | "
                f"Method: {request.method} | "
                f"Path: {request.path} | "
                f"Files: {files_info}"
            )

        else:
            log.info(
                f"Request | "
                f"IP: {request.remote_addr} | "
                f"User: {user} | "
                f"Method: {request.method} | "
                f"Path: {request.path} | "
                f"Args: {request.args.to_dict()}"
            )

    @app.before_request
    def load_notifications():
        if current_user.is_authenticated:
            g.notifications = db.session.scalars(
                db.select(Notification)
                .where(
                    Notification.user_id == current_user.id,
                    # Notification.is_read.is_(False),
                )
                .order_by(Notification.created_on.desc())
                .limit(15)
            ).all()

            g.unread_count = sum(1 for n in g.notifications if not n.is_read)
        else:
            g.notifications = []
            g.unread_count = 0

    @app.errorhandler(Exception)
    def handle_exception(e):
        log = current_app.logger

        # Safe username retrieval
        if current_user.is_authenticated:
            user = current_user.username  # or current_user.get_id()
        else:
            user = "anonymous"

        # Collect file metadata if any
        files_info = []
        if request.files:
            for field, storage in request.files.items():
                try:
                    # Measure size from stream
                    pos = storage.stream.tell()
                    storage.stream.seek(0, 2)  # move to end
                    size_bytes = storage.stream.tell()
                    storage.stream.seek(pos)  # reset cursor
                except Exception:
                    size_bytes = None

                files_info.append(
                    {
                        "field": field,
                        "filename": storage.filename,
                        "size": size_bytes,  # size in bytes
                        "mimetype": storage.mimetype,
                    }
                )

        # Structured log
        log.exception(
            f"Unhandled Exception | "
            f"IP: {request.remote_addr} | "
            f"User: {user} | "
            f"Method: {request.method} | "
            f"Path: {request.path} | "
            f"Args: {request.args.to_dict()} | "
            f"Files: {files_info} | "
            f"Error: {e}"
        )

        return "An internal error occurred", 500

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

    app.cli.add_command(reset_id)
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
    app.register_blueprint(correspondence_bp, url_prefix="/correspondence")
    app.register_blueprint(refund_dqr_bp, url_prefix="/refund_dqr")
    app.register_blueprint(ri_page_bp, url_prefix="/ri")
    app.register_blueprint(todo_bp, url_prefix="/todo")
    app.register_blueprint(ci_bp, url_prefix="/ci")

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
