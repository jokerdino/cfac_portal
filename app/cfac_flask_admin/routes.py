from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink

from flask_admin_models import DefaultModelView

from app.cfac_flask_admin.model_views import BRSView, UserView

from extensions import admin, db
from app.brs.models import BRS, BRS_month, Outstanding
from app.coinsurance.coinsurance_model import (
    Coinsurance,
    Settlement,
    Remarks,
    Coinsurance_log,
    CoinsuranceBalances,
)
from app.contacts.contacts_model import Contacts
from app.contracts.contracts_model import Contracts
from app.users.user_model import User, Log_user
from app.tickets.tickets_model import Tickets, TicketRemarks

admin.add_link(MenuLink(name="Go to main app", category="", url="/"))

admin.add_sub_category(name="Users", parent_name="Users")
admin.add_sub_category(name="BRS", parent_name="BRS")
admin.add_sub_category(name="Coinsurance", parent_name="Coinsurance")
admin.add_sub_category(name="Tickets", parent_name="Tickets")

# User models
admin.add_view(UserView(User, db.session, category="Users"))  # , name="User"))
admin.add_view(
    DefaultModelView(Log_user, db.session, endpoint="log_user_", category="Users")
)

# BRS models
admin.add_view(BRSView(BRS, db.session, endpoint="brs_", category="BRS"))
admin.add_view(
    DefaultModelView(BRS_month, db.session, endpoint="brs_month_", category="BRS")
)
admin.add_view(
    ModelView(Outstanding, db.session, endpoint="outstanding_", category="BRS")
)

# coinsurance models
admin.add_view(
    ModelView(Coinsurance, db.session, endpoint="coinsurance_", category="Coinsurance")
)
admin.add_view(
    ModelView(Settlement, db.session, endpoint="settlement_", category="Coinsurance")
)
admin.add_view(
    ModelView(Remarks, db.session, endpoint="remarks_", category="Coinsurance")
)
admin.add_view(
    ModelView(
        Coinsurance_log, db.session, endpoint="coinsurance_log_", category="Coinsurance"
    )
)
admin.add_view(
    ModelView(
        CoinsuranceBalances,
        db.session,
        endpoint="coinsurance_balances_",
        category="Coinsurance",
    )
)

# tickets models
admin.add_view(
    DefaultModelView(Tickets, db.session, endpoint="tickets_", category="Tickets")
)
admin.add_view(
    DefaultModelView(
        TicketRemarks, db.session, endpoint="tickets_remarks_", category="Tickets"
    )
)

# contacts models
admin.add_view(ModelView(Contacts, db.session, endpoint="contacts_"))

# contracts models
admin.add_view(ModelView(Contracts, db.session, endpoint="contracts_"))
