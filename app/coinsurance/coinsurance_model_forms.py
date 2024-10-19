from wtforms_sqlalchemy.orm import model_form

from .coinsurance_model import CoinsuranceReceipts

# from .coinsurance_form import CoinsuranceReceiptAddForm

ReceiptForm = model_form(
    CoinsuranceReceipts,
    #  base_class=CoinsuranceReceiptAddForm,
    # converter={"company_name": SelectField},
    only=[
        "company_name",
        "credit",
        "value_date",
        "reference_no",
        "transaction_code",
    ],
)
