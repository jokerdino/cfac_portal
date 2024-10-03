from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink

from app.announcements.announcements_model import Announcements
from app.bank_guarantee.bg_models import BankGuarantee
from app.brs.models import (
    BRS,
    BankReconAccountDetails,
    BankReconExcessCredit,
    BankReconShortCredit,
    BRS_month,
    DeleteEntries,
    Outstanding,
)
from app.cfac_flask_admin.model_views import (
    BRSView,
    FundBankStatementView,
    OSView,
    ReconSummaryView,
    UserView,
)
from app.coinsurance.coinsurance_model import (
    Coinsurance,
    Coinsurance_log,
    CoinsuranceBalances,
    CoinsuranceCashCall,
    Remarks,
    Settlement,
    CoinsuranceBankMandate,
    CoinsuranceReceipts,
)
from app.contacts.contacts_model import Contacts
from app.contracts.contracts_model import Contracts
from app.funds.funds_model import (
    FundAmountGivenToInvestment,
    FundBankAccountNumbers,
    FundBankStatement,
    FundDailyOutflow,
    FundDailySheet,
    FundFlagSheet,
    FundJournalVoucherFlagSheet,
    FundMajorOutgo,
)
from app.ho_accounts.ho_accounts_model import (
    HeadOfficeAccountsTracker,
    HeadOfficeBankReconTracker,
)
from app.ho_ro_recon.ho_ro_recon_model import ReconEntries, ReconSummary
from app.knowledge_base.knowledge_base_model import KnowledgeBase
from app.mis_tracker.mis_model import MisTracker
from app.outstanding_expenses.os_model import OutstandingExpenses
from app.pool_credits.pool_credits_model import PoolCredits, PoolCreditsPortal
from app.tickets.tickets_model import TicketRemarks, Tickets
from app.users.user_model import Log_user, User
from app.budget.budget_model import BudgetAllocation, BudgetUtilization
from app.pg_tieup.pg_tieup_model import PaymentGatewayTieup

from extensions import admin, db
from flask_admin_models import DefaultModelView

admin.add_link(MenuLink(name="Go to main app", category="", url="/"))

admin.add_sub_category(name="Users", parent_name="Users")
admin.add_sub_category(name="BRS", parent_name="BRS")
admin.add_sub_category(name="Coinsurance", parent_name="Coinsurance")
admin.add_sub_category(name="Tickets", parent_name="Tickets")
admin.add_sub_category(name="Funds", parent_name="Funds")
admin.add_sub_category(name="HO_checklist", parent_name="HO_checklist")
admin.add_sub_category(name="HORO_recon", parent_name="HORORecon")
admin.add_sub_category(name="PoolCredits", parent_name="PoolCredits")
admin.add_sub_category(name="Budget", parent_name="Budget")

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
admin.add_view(
    ModelView(
        BankReconExcessCredit,
        db.session,
        endpoint="excess_credit_entries_",
        category="BRS",
    )
)
admin.add_view(
    ModelView(
        BankReconShortCredit,
        db.session,
        endpoint="short_credit_entries_",
        category="BRS",
    )
)

admin.add_view(
    ModelView(
        BankReconAccountDetails, db.session, endpoint="bank_account_", category="BRS"
    )
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

admin.add_view(
    ModelView(
        CoinsuranceBankMandate,
        db.session,
        endpoint="coinsurance_bankmandate",
        category="Coinsurance",
    )
)

admin.add_view(
    ModelView(
        CoinsuranceReceipts,
        db.session,
        endpoint="coinsurance_receipts",
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
        FundJournalVoucherFlagSheet,
        db.session,
        endpoint="funds_jv_flag_sheet",
        category="Funds",
    )
)

# misc models
admin.add_view(ModelView(MisTracker, db.session, endpoint="mistracker_"))
admin.add_view(ModelView(Announcements, db.session, endpoint="announcements_"))

# ho_checklist models
admin.add_view(
    DefaultModelView(
        HeadOfficeBankReconTracker,
        db.session,
        endpoint="recon",
        category="HO_checklist",
    )
)
admin.add_view(
    DefaultModelView(
        HeadOfficeAccountsTracker,
        db.session,
        endpoint="general",
        category="HO_checklist",
    )
)


# HO RO recon models
admin.add_view(
    DefaultModelView(
        ReconEntries, db.session, endpoint="entries", category="HORO_recon"
    )
)
admin.add_view(
    ReconSummaryView(
        ReconSummary, db.session, endpoint="summary", category="HORO_recon"
    )
)

# Pool Credits module

admin.add_view(
    DefaultModelView(
        PoolCredits, db.session, endpoint="pool_credits_", category="Pool credits"
    )
)

admin.add_view(
    DefaultModelView(
        PoolCreditsPortal,
        db.session,
        endpoint="pool_credits_portal_",
        category="Pool credits",
    )
)


# Budget module
admin.add_view(
    DefaultModelView(
        BudgetAllocation,
        db.session,
        endpoint="budget_allocation_",
        category="Budget",
    )
)

admin.add_view(
    DefaultModelView(
        BudgetUtilization,
        db.session,
        endpoint="budget_utilization_",
        category="Budget",
    )
)

# PG tieup module
admin.add_view(
    DefaultModelView(
        PaymentGatewayTieup,
        db.session,
        endpoint="pg_tieup_",
    )
)
