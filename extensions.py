from flask_admin import Admin
from flask_admin.theme import Bootstrap4Theme
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase
from flask_debugtoolbar import DebugToolbarExtension

from flask_admin_models import MyAdminIndexView

migrate = Migrate(compare_type=True)
lm = LoginManager()


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


db = SQLAlchemy(model_class=Base)


admin = Admin(
    theme=Bootstrap4Theme(fluid=True, swatch="united"),
    name="CFAC portal",
    index_view=MyAdminIndexView(),
)

toolbar = DebugToolbarExtension()
