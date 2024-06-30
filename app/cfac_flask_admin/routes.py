from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink

from flask_admin_models import DefaultModelView

from app.cfac_flask_admin.model_views import (
    BRSView,
    UserView,
    OSView,
    FundBankStatementView,
)

from extensions import admin, db
from app.brs.models import BRS, BRS_month, Outstanding, DeleteEntries
from app.coinsurance.coinsurance_model import (
    Coinsurance,
    Settlement,
    Remarks,
    Coinsurance_log,
    CoinsuranceBalances,
    CoinsuranceCashCall,
)
from app.contacts.contacts_model import Contacts
from app.contracts.contracts_model import Contracts
from app.users.user_model import User, Log_user
from app.tickets.tickets_model import Tickets, TicketRemarks
from app.knowledge_base.knowledge_base_model import KnowledgeBase
from app.bank_guarantee.bg_models import BankGuarantee
from app.outstanding_expenses.os_model import OutstandingExpenses

from app.funds.funds_model import (
    FundAmountGivenToInvestment,
    FundBankAccountNumbers,
    FundBankStatement,
    FundDailyOutflow,
    FundDailySheet,
    FundFlagSheet,
    FundMajorOutgo,
    FundJournalVoucherFlagSheet,
)

from app.mis_tracker.mis_model import MisTracker
from app.announcements.announcements_model import Announcements
from app.ho_accounts.ho_accounts_model import HeadOfficeAccountsTracker, HeadOfficeBankReconTracker

admin.add_link(MenuLink(name="Go to main app", category="", url="/"))

admin.add_sub_category(name="Users", parent_name="Users")
admin.add_sub_category(name="BRS", parent_name="BRS")
admin.add_sub_category(name="Coinsurance", parent_name="Coinsurance")
admin.add_sub_category(name="Tickets", parent_name="Tickets")
admin.add_sub_category(name="Funds", parent_name="Funds")
admin.add_sub_category(name="HO_checklist", parent_name="HO_checklist")
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
admin.add_view(
    ModelView(DeleteEntries, db.session, endpoint="delete_entries_", category="BRS")
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
admin.add_view(
    ModelView(
        CoinsuranceCashCall,
        db.session,
        endpoint="coinsurance_cashcall",
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

# knowledge models
admin.add_view(ModelView(KnowledgeBase, db.session, endpoint="kb_"))
# bank guarantee models
admin.add_view(ModelView(BankGuarantee, db.session, endpoint="bg_"))
# outstanding expenses model
admin.add_view(OSView(OutstandingExpenses, db.session, endpoint="os_"))

# funds model

admin.add_view(
    DefaultModelView(
        FundAmountGivenToInvestment,
        db.session,
        endpoint="funds_investment",
        category="Funds",
    )
)
admin.add_view(
    DefaultModelView(
        FundBankAccountNumbers,
        db.session,
        endpoint="funds_bankaccountnumbers",
        category="Funds",
    )
)
admin.add_view(
    FundBankStatementView(
        FundBankStatement, db.session, endpoint="funds_bank_statement", category="Funds"
    )
)
admin.add_view(
    DefaultModelView(
        FundDailyOutflow, db.session, endpoint="funds_daily_outflow", category="Funds"
    )
)
admin.add_view(
    DefaultModelView(
        FundFlagSheet, db.session, endpoint="funds_flag_sheet", category="Funds"
    )
)
admin.add_view(
    DefaultModelView(
        FundMajorOutgo, db.session, endpoint="funds_major_outgo", category="Funds"
    )
)
admin.add_view(
    DefaultModelView(
        FundDailySheet, db.session, endpoint="funds_daily_sheet", category="Funds"
    )
)
admin.add_view(
    DefaultModelView(
        FundJournalVoucherFlagSheet, db.session, endpoint="funds_jv_flag_sheet", category="Funds"
    )
)

# misc models
admin.add_view(ModelView(MisTracker, db.session, endpoint="mistracker_"))
admin.add_view(ModelView(Announcements, db.session, endpoint="announcements_"))

# ho_checklist models
admin.add_view(DefaultModelView(HeadOfficeBankReconTracker, db.session, endpoint="recon", category="HO_checklist"))
admin.add_view(DefaultModelView(HeadOfficeAccountsTracker, db.session, endpoint="general", category="HO_checklist"))
