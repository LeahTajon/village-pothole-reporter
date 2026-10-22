
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class Pothole(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Exact pin location
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    # Readable location information
    street_name = db.Column(db.String(255), nullable=True)
    location_address = db.Column(db.String(500), nullable=True)

    # Details provided by the resident
    description = db.Column(db.Text, nullable=False)

    # Low, Medium, or High
    severity = db.Column(
        db.String(20),
        nullable=False,
        default="Medium"
    )

    # Optional photo filename
    photo = db.Column(db.String(255), nullable=True)

    # Current repair progress
    status = db.Column(
        db.String(30),
        nullable=False,
        default="Submitted"
    )

    # When the report was submitted
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    # When the report was last updated
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now
    )

    # Photo uploaded after the pothole is repaired
    repair_photo = db.Column(
        db.String(255),
        nullable=True
    )

    # Date and time the repair was completed
    repair_completed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    # Optional notes about the repair
    repair_notes = db.Column(
        db.Text,
        nullable=True
    )

    @property
    def created_at_guam(self):
        if self.created_at is None:
            return None

        timestamp = self.created_at

        # SQLite may return a datetime without timezone information.
        # Stored timestamps are treated as UTC.
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return timestamp.astimezone(ZoneInfo("Pacific/Guam"))

    @property
    def updated_at_guam(self):
        if self.updated_at is None:
            return None

        timestamp = self.updated_at

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return timestamp.astimezone(ZoneInfo("Pacific/Guam"))

    def __repr__(self):
        return f"<Pothole {self.id}: {self.status}>"


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Admin {self.username}>"
