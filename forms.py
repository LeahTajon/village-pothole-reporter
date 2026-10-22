from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    TextAreaField, 
    SelectField, 
    SubmitField,
    StringField,
    PasswordField)

from wtforms.validators import (
    DataRequired, 
    Length)


class PotholeReportForm(FlaskForm):
    description = TextAreaField(
        "Pothole Description",
        validators=[
            DataRequired(message="Please describe the pothole."),
            Length(
                max=2000,
                message="Description must be 2,000 characters or fewer."
            ),
        ],
    )

    severity = SelectField(
        "Severity",
        choices=[
            ("Low", "Low — Minor road damage"),
            ("Medium", "Medium — Noticeable road hazard"),
            ("High", "High — Serious safety concern"),
        ],
        validators=[DataRequired(message="Please select a severity level.")],
    )

    photo = FileField(
        "Upload a Photo (Optional)",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Please upload a JPG, PNG, or WebP image.",
            )
        ]
    )

    submit = SubmitField("Submit Pothole Report")

class AdminLoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Please enter your username."),
            Length(max=80),
        ],
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please enter your password.")
        ],
    )

    submit = SubmitField("Log In")

class AdminStatusForm(FlaskForm):
    status = SelectField(
        "Report Status",
        choices=[
            ("Submitted", "Submitted"),
            ("Under Review", "Under Review"),
            ("In Progress", "In Progress"),
            ("Repaired", "Repaired"),
        ],
        validators=[DataRequired()],
    )

    repair_photo = FileField(
        "After-Repair Photo",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Please upload a JPG, PNG, or WebP image."
            )
        ],
    )

    repair_notes = TextAreaField(
        "Repair Notes",
        default="Pothole repaired and road surface patched.",
        validators=[
            Length(
                max=2000,
                message="Repair notes must be 2,000 characters or fewer."
            )
        ],
    )

    submit = SubmitField("Update Status")

class BulkAreaStatusForm(FlaskForm):
    status = SelectField(
        "Report Status",
        choices=[
            ("Submitted", "Submitted"),
            ("Under Review", "Under Review"),
            ("In Progress", "In Progress"),
            ("Repaired", "Repaired")
        ],
        validators=[DataRequired()],
    )

    repair_photo = FileField(
        "Shared After-Repair Photo",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "webp"],
                "Please upload a JPG, PNG, or WebP image.",
            )
        ],
    )

    repair_notes = TextAreaField(
        "Repair Notes",
        default="Pothole repaired and road surface patched.",
        validators=[
            Length(
                max=2000,
                message="Repair notes must be 2,000 characters or fewer.",
            )
        ],
    )

    submit = SubmitField("Update All Reports")

class DeleteReportForm(FlaskForm):
    pass 