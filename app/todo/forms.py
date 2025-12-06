from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    SelectField,
    DateField,
    SubmitField,
    SelectMultipleField,
)
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import CheckboxInput, ListWidget


class TaskForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField(validators=[Optional()])
    priority = SelectField(
        choices=[(1, "Low"), (2, "Medium"), (3, "High")],
        default="1",
    )

    due_date = DateField("Due Date", validators=[Optional()])
    assigned_to_id = SelectField("Assign To", validators=[Optional()])
    subscribers = SelectMultipleField(
        "Subscribers",
        validators=[Optional()],
        coerce=int,  # Ensure the submitted IDs are converted to integers
        option_widget=CheckboxInput(),  # Renders each option as a checkbox input
        widget=ListWidget(prefix_label=False),  # Renders the options in a list (ul/ol)
        render_kw={
            "style": "max-height: 200px; overflow-y: auto;",
            "class": "list-unstyled",
        },
    )

    submit = SubmitField("Save")
