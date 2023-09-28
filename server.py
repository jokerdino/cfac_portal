from flask import Flask
from waitress import serve

from app.admin.admin_routes import admin_check
from app.users.user_model import User
from config import Config
from extensions import db, lm, migrate


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions here

    lm.init_app(app)
    lm.login_view = "login_page"
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints here
    from app.main import main_bp

    app.register_blueprint(main_bp, url_prefix="/")

    from app.users import user_bp

    app.register_blueprint(user_bp, url_prefix="/user")

    from app.admin import admin_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.coinsurance import coinsurance_bp

    app.register_blueprint(coinsurance_bp, url_prefix="/coinsurance")

    from app.brs import brs_bp

    app.register_blueprint(brs_bp, url_prefix="/brs")

    #    @app.route('/test/')
    #    def test_page():
    #        return "Hello"

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        #  db.drop_all()
        db.create_all()
        admin_check()
    #    app.run(debug=True)
#    serve(app, host="0.0.0.0", port=8080)
    app.run(debug=True, port=8080)
