from flask_wtf import FlaskForm, Form
from flask_wtf.file import FileRequired, FileAllowed, FileField

from wtforms import (
    DateField,
    DecimalField,
    FieldList,
    FormField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    NumberRange,
    ValidationError,
    Optional,
)
from .model import PrivilegeLeaveBalance, SickLeaveBalance


class PrivilegeLeaveForm(Form):
    employee_ro_code = StringField(render_kw={"readonly": True, "class": "input-like"})
    employee_oo_code = StringField(render_kw={"readonly": True, "class": "input-like"})
    employee_name = StringField(render_kw={"readonly": True, "class": "input-like"})
    employee_number = StringField(render_kw={"readonly": True, "class": "input-like"})
    employee_designation = StringField(
        render_kw={"readonly": True, "class": "input-like"}
    )

    opening_balance = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=270)],
        render_kw={"class": "input is-small"},
    )
    leave_accrued = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=270)],
        render_kw={"class": "input is-small"},
    )
    leave_availed = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=270)],
        render_kw={"class": "input is-small"},
    )
    leave_encashed = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=270)],
        render_kw={"class": "input is-small"},
    )
    leave_lapsed = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=270)],
        render_kw={"class": "input is-small"},
    )
    closing_balance = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=270)],
        render_kw={"class": "input is-small"},
    )
    id = HiddenField()


class PrivilegeLeaveBulkUpdateForm(FlaskForm):
    privilege_leave = FieldList(
        FormField(PrivilegeLeaveForm, default=PrivilegeLeaveBalance), min_entries=1
    )


class SickLeaveForm(Form):
    employee_ro_code = StringField(render_kw={"readonly": True, "class": "input-like"})
    employee_oo_code = StringField(render_kw={"readonly": True, "class": "input-like"})

    employee_name = StringField(render_kw={"readonly": True, "class": "input-like"})
    employee_number = StringField(render_kw={"readonly": True, "class": "input-like"})
    employee_designation = StringField(
        render_kw={"readonly": True, "class": "input-like"}
    )
    opening_balance = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=240)],
        render_kw={"class": "input is-small"},
    )
    leave_accrued = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=240)],
        render_kw={"class": "input is-small"},
    )
    leave_availed = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=240)],
        render_kw={"class": "input is-small"},
    )

    leave_lapsed = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=240)],
        render_kw={"class": "input is-small"},
    )
    closing_balance = DecimalField(
        validators=[Optional(), NumberRange(min=0, max=240)],
        render_kw={"class": "input is-small"},
    )
    id = HiddenField()


class SickLeaveBulkUpdateForm(FlaskForm):
    sick_leave = FieldList(
        FormField(SickLeaveForm, default=SickLeaveBalance), min_entries=1
    )


class UploadFileForm(FlaskForm):
    file_upload = FileField(
        "Upload document", validators=[FileRequired(), FileAllowed(["xlsx"])]
    )
    upload_document = SubmitField("Upload")
