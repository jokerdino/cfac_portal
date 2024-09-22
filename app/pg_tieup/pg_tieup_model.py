from sqlalchemy.orm import ColumnProperty, class_mapper

from extensions import db


class PaymentGatewayTieup(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name_of_head_office_department = db.Column(db.String)
    date_of_request_from_head_office_department = db.Column(db.Date)
    name_of_tieup_partner = db.Column(db.String)
    similar_request_from_other_department = db.Column(db.Boolean)
    nodal_office_agree_for_pg_vender = db.Column(db.Boolean)
    mou_validity_date = db.Column(db.Date)
    ro_code = db.Column(db.String)
    nodal_office_code = db.Column(db.String)
    nodal_office_name = db.Column(db.String)
    tieup_partner_id_for_bank_mandate = db.Column(db.String)
    date_informed_to_bank_for_bank_mandate = db.Column(db.Date)
    date_of_receipt_of_bank_mandate_with_bank_seal = db.Column(db.Date)
    date_bank_mandate_shared_with_pg_vendor = db.Column(db.Date)
    mid_or_similar_id_as_per_pg_vendor = db.Column(db.String)
    old_mid_name = db.Column(db.String)
    date_of_receipt_of_staging_details = db.Column(db.Date)
    date_of_sharing_staging_details_to_head_office_dept = db.Column(db.Date)
    staging_details = db.Column(db.String)
    date_of_receipt_of_production_details = db.Column(db.Date)
    production_details = db.Column(db.String)
    bank_account_details_where_credit_is_expected = db.Column(db.String)
    bank_name = db.Column(db.String)
    bank_account_number = db.Column(db.String)
    whether_t_plus_one_transfer_happening = db.Column(db.Boolean)
    brs_done_upto = db.Column(db.Date)
    spoc_name = db.Column(db.String)
    spoc_employee_number = db.Column(db.String)
    ro_spoc_email_address = db.Column(db.String)
    nodal_office_spoc_email_address = db.Column(db.String)
    nodal_office_gst_address = db.Column(db.String)
    date_of_bank_charges_jv_passed_to_nodal_office = db.Column(db.Date)
    #   WHETHER  ANYOTHER DEPT HAS SOUGHT FOR SIMILAR APPROVAL FOR SAME TIE UP PARTNER

    #  meta data

    current_status = db.Column(db.String)

    date_created_date = db.Column(db.DateTime)
    date_updated_date = db.Column(db.DateTime)
    date_deleted_date = db.Column(db.DateTime)

    created_by = db.Column(db.String)
    updated_by = db.Column(db.String)
    deleted_by = db.Column(db.String)

    def columns(self):
        """Return the actual columns of a SQLAlchemy-mapped object"""
        return [
            prop.key
            for prop in class_mapper(self.__class__).iterate_properties
            if isinstance(prop, ColumnProperty)
        ]
