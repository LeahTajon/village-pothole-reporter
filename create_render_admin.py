
import os

from app import app
from extensions import db
from models import Admin


def create_render_admin():
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")

    # Skip admin creation when credentials aren't configured.
    if not username or not password:
        print("Admin creation skipped: credentials not configured.")
        return

    if len(username) > 80:
        raise ValueError("ADMIN_USERNAME must be 80 characters or fewer.")

    if len(password) < 12:
        raise ValueError("ADMIN_PASSWORD must be at least 12 characters.")

    with app.app_context():
        existing_admin = Admin.query.filter_by(
            username=username
        ).first()

        if existing_admin:
            print("Configured admin account already exists.")
            return

        admin = Admin(username=username)
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        print("Configured admin account created successfully.")


if __name__ == "__main__":
    create_render_admin()
