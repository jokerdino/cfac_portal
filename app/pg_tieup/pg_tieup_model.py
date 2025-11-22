from datetime import date
from typing import Optional

from sqlalchemy.orm import Mapped

from extensions import db, IntPK, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn


class PaymentGatewayTieup(db.Model):
    id: Mapped[IntPK]

    name_of_head_office_department: Mapped[Optional[str]]
    date_of_request_from_head_office_department: Mapped[Optional[date]]
    name_of_tieup_partner: Mapped[Optional[str]]
    similar_request_from_other_department: Mapped[Optional[bool]]
    nodal_office_agree_for_pg_vender: Mapped[Optional[bool]]
    mou_validity_date: Mapped[Optional[date]]
    ro_code: Mapped[Optional[str]]
    nodal_office_code: Mapped[Optional[str]]
    nodal_office_name: Mapped[Optional[str]]
    tieup_partner_id_for_bank_mandate: Mapped[Optional[str]]
    date_informed_to_bank_for_bank_mandate: Mapped[Optional[date]]
    date_of_receipt_of_bank_mandate_with_bank_seal: Mapped[Optional[date]]
    date_bank_mandate_shared_with_pg_vendor: Mapped[Optional[date]]
    mid_or_similar_id_as_per_pg_vendor: Mapped[Optional[str]]
    old_mid_name: Mapped[Optional[str]]
    date_of_receipt_of_staging_details: Mapped[Optional[date]]
    date_of_sharing_staging_details_to_head_office_dept: Mapped[Optional[date]]
    staging_details: Mapped[Optional[str]]
    date_of_receipt_of_production_details: Mapped[Optional[date]]
    production_details: Mapped[Optional[str]]
    bank_account_details_where_credit_is_expected: Mapped[Optional[str]]
    bank_name: Mapped[Optional[str]]
    bank_account_number: Mapped[Optional[str]]
    whether_t_plus_one_transfer_happening: Mapped[Optional[bool]]
    brs_done_upto: Mapped[Optional[date]]
    spoc_name: Mapped[Optional[str]]
    spoc_employee_number: Mapped[Optional[str]]
    ro_spoc_email_address: Mapped[Optional[str]]
    nodal_office_spoc_email_address: Mapped[Optional[str]]
    nodal_office_gst_address: Mapped[Optional[str]]
    date_of_bank_charges_jv_passed_to_nodal_office: Mapped[Optional[date]]
    bank_mandate_file: Mapped[Optional[str]]

    current_status: Mapped[Optional[str]]

    date_created_date: Mapped[CreatedOn]
    date_updated_date: Mapped[UpdatedOn]

    created_by: Mapped[CreatedBy]
    updated_by: Mapped[UpdatedBy]
