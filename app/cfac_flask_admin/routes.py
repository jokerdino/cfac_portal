from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink

from app.announcements.announcements_model import Announcements
from app.bank_guarantee.bg_models import BankGuarantee
from app.brs.models import (
    BRS,
    BankReconAccountDetails,
    BankReconExcessCredit,
    BankReconShortCredit,
    BRSMonth,
    DeleteEntries,
    Outstanding,
)
from app.cfac_flask_admin.model_views import (
    BRSView,
    FundBankStatementView,
    OSView,
    ReconSummaryView,
    UserView,
    PoolCreditView,
    BudgetAllocationView,
    BudgetUtilizationView,
    LienView,
)
from app.coinsurance.coinsurance_model import (
    Coinsurance,
    CoinsuranceLog,
    CoinsuranceBalances,
    CoinsuranceBalanceGeneralLedgerCodeFlagSheet,
    CoinsuranceBalanceZoneFlagSheet,
    CoinsuranceCashCall,
    Remarks,
    Settlement,
    CoinsuranceBankMandate,
    CoinsuranceReceipts,
    CoinsuranceReceiptsJournalVoucher,
    CoinsuranceTokenRequestId,
)
from app.contacts.contacts_model import Contacts
from app.contracts.contracts_model import Contracts
from app.correspondence.models import Circular, OutwardDocument, InwardDocument
from app.escalation_matrix.models import EscalationMatrix
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
from app.pool_credits.pool_credits_model import (
    PoolCredits,
    PoolCreditsPortal,
    PoolCreditsJournalVoucher,
)
from app.tickets.tickets_model import TicketRemarks, Tickets
from app.users.user_model import LogUser, User
from app.budget.budget_model import BudgetAllocation, BudgetUtilization
from app.pg_tieup.pg_tieup_model import PaymentGatewayTieup


from app.leave_management.leave_model import (
    EmployeeData,
    LeaveBalance,
    LeaveApplication,
    AttendanceRegister,
    LeaveSubmissionData,
    PublicHoliday,
)
from app.lien.lien_model import Lien

from app.employee_leave_balance.model import PrivilegeLeaveBalance, SickLeaveBalance
from app.brs_centralised_cheque.models import (
    CentralisedChequeSummary,
    CentralisedChequeDetails,
    CentralisedChequeInstrumentStaleDetails,
    CentralisedChequeInstrumentUnencashedDetails,
    CentralisedChequeEnableDelete,
)

from app.refund_dqr.models import DqrRefund, DqrMachines
from extensions import admin, db
from flask_admin_models import DefaultModelView

admin.add_link(MenuLink(name="Go to main app", category="", url="/"))

admin.add_sub_category(name="BRS", parent_name="BRS")
admin.add_sub_category(name="BRS_CC", parent_name="BRS_CC")
admin.add_sub_category(name="Budget", parent_name="Budget")
admin.add_sub_category(name="Coinsurance", parent_name="Coinsurance")
admin.add_sub_category(name="Correspondence", parent_name="Correspondence")
admin.add_sub_category(name="Funds", parent_name="Funds")
admin.add_sub_category(name="HO_checklist", parent_name="HO_checklist")
admin.add_sub_category(name="HORO_recon", parent_name="HORORecon")
admin.add_sub_category(name="Leave management", parent_name="Leave management")
admin.add_sub_category(name="Leave balance", parent_name="Leave balance")
admin.add_sub_category(name="PoolCredits", parent_name="PoolCredits")
admin.add_sub_category(name="Refund - DQR", parent_name="Refund DQR")
admin.add_sub_category(name="Tickets", parent_name="Tickets")
admin.add_sub_category(name="Users", parent_name="Users")


# announcements
admin.add_view(ModelView(Announcements, db.session, endpoint="announcements_"))

# bank guarantee
admin.add_view(ModelView(BankGuarantee, db.session, endpoint="bg_"))

# BRS models
admin.add_view(BRSView(BRS, db.session, endpoint="brs_", category="BRS"))
admin.add_view(
    DefaultModelView(BRSMonth, db.session, endpoint="brs_month_", category="BRS")
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

# brs_cc

admin.add_view(
    ModelView(
        CentralisedChequeSummary, db.session, endpoint="cc_summary", category="BRS_CC"
    )
)
admin.add_view(
    ModelView(
        CentralisedChequeDetails, db.session, endpoint="cc_details", category="BRS_CC"
    )
)
admin.add_view(
    ModelView(
        CentralisedChequeInstrumentStaleDetails,
        db.session,
        endpoint="cc_stale",
        category="BRS_CC",
    )
)
admin.add_view(
    ModelView(
        CentralisedChequeInstrumentUnencashedDetails,
        db.session,
        endpoint="cc_unencashed",
        category="BRS_CC",
    )
)
admin.add_view(
    ModelView(
        CentralisedChequeEnableDelete,
        db.session,
        endpoint="cc_delete",
        category="BRS_CC",
    )
)

# budget
admin.add_view(
    BudgetAllocationView(
        BudgetAllocation,
        db.session,
        endpoint="budget_allocation_",
        category="Budget",
    )
)

admin.add_view(
    BudgetUtilizationView(
        BudgetUtilization,
        db.session,
        endpoint="budget_utilization_",
        category="Budget",
    )
)

# coinsurance
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
        CoinsuranceLog, db.session, endpoint="coinsurance_log_", category="Coinsurance"
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
        CoinsuranceBalanceGeneralLedgerCodeFlagSheet,
        db.session,
        endpoint="coinsurance_balances_gl_code",
        category="Coinsurance",
    )
)
admin.add_view(
    ModelView(
        CoinsuranceBalanceZoneFlagSheet,
        db.session,
        endpoint="coinsurance_balances_zone",
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
admin.add_view(
    ModelView(
        CoinsuranceReceiptsJournalVoucher,
        db.session,
        endpoint="coinsurance_receipts_jv",
        category="Coinsurance",
    )
)

admin.add_view(
    ModelView(
        CoinsuranceTokenRequestId,
        db.session,
        endpoint="coinsurance_token_request_id",
        category="Coinsurance",
    )
)

# contacts
admin.add_view(ModelView(Contacts, db.session, endpoint="contacts_"))

# contracts
admin.add_view(ModelView(Contracts, db.session, endpoint="contracts_"))

# Correspondence
admin.add_view(
    ModelView(Circular, db.session, endpoint="circular_", category="Correspondence")
)
admin.add_view(
    ModelView(InwardDocument, db.session, endpoint="inward_", category="Correspondence")
)
admin.add_view(
    ModelView(
        OutwardDocument, db.session, endpoint="outward_", category="Correspondence"
    )
)
# escalation matrix
admin.add_view(ModelView(EscalationMatrix, db.session, endpoint="em_"))
# funds
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

# ho checklist
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

# horo recon
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

# knowledge base
admin.add_view(ModelView(KnowledgeBase, db.session, endpoint="kb_"))


# leave management
admin.add_view(
    DefaultModelView(
        EmployeeData,
        db.session,
        endpoint="employee_data",
        category="Leave management",
    )
)

admin.add_view(
    DefaultModelView(
        AttendanceRegister,
        db.session,
        endpoint="attendance_register",
        category="Leave management",
    )
)


admin.add_view(
    DefaultModelView(
        LeaveBalance,
        db.session,
        endpoint="leave_balance",
        category="Leave management",
    )
)

admin.add_view(
    DefaultModelView(
        LeaveApplication,
        db.session,
        endpoint="leave_application",
        category="Leave management",
    )
)


admin.add_view(
    DefaultModelView(
        LeaveSubmissionData,
        db.session,
        endpoint="leave_submission",
        category="Leave management",
    )
)

admin.add_view(
    DefaultModelView(
        PublicHoliday,
        db.session,
        endpoint="public_holiday",
        category="Leave management",
    )
)

# leave balance
admin.add_view(
    DefaultModelView(
        PrivilegeLeaveBalance,
        db.session,
        endpoint="PL",
        category="Leave balance",
    )
)

admin.add_view(
    DefaultModelView(
        SickLeaveBalance,
        db.session,
        endpoint="SL",
        category="Leave balance",
    )
)

# lien
admin.add_view(
    LienView(
        Lien,
        db.session,
        endpoint="lien_",
    )
)

# mis tracker
admin.add_view(ModelView(MisTracker, db.session, endpoint="mistracker_"))

# outstanding expenses
admin.add_view(OSView(OutstandingExpenses, db.session, endpoint="os_"))

# pg tieup
admin.add_view(
    DefaultModelView(
        PaymentGatewayTieup,
        db.session,
        endpoint="pg_tieup_",
    )
)

# pool credits
admin.add_view(
    PoolCreditView(
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

admin.add_view(
    DefaultModelView(
        PoolCreditsJournalVoucher,
        db.session,
        endpoint="pool_credits_jv_",
        category="Pool credits",
    )
)

# refund - dqr
admin.add_view(
    DefaultModelView(
        DqrRefund, db.session, endpoint="refund_dqr_", category="Refund DQR"
    )
)
admin.add_view(
    DefaultModelView(
        DqrMachines, db.session, endpoint="refund_dqr_machines", category="Refund DQR"
    )
)

# tickets
admin.add_view(
    DefaultModelView(Tickets, db.session, endpoint="tickets_", category="Tickets")
)
admin.add_view(
    DefaultModelView(
        TicketRemarks, db.session, endpoint="tickets_remarks_", category="Tickets"
    )
)

# users
admin.add_view(UserView(User, db.session, endpoint="user_", category="Users"))
admin.add_view(
    DefaultModelView(LogUser, db.session, endpoint="log_user_", category="Users")
)
