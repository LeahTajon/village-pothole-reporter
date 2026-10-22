from getpass import getpass

from app import app
from extensions import db
from models import Admin

def create_admin():
    print("\n=== Create Administrator Account ===\n")

    username = input("Enter admin username: ").strip()

    if not username:
        print("Username cannot be empty.")
        return

    if len(username) > 80:
        print("Username must be 80 characters or fewer.")
        return 

    with app.app_context():
        existing_admin = Admin.query.filter_by(
            username=username
        ).first()

        if existing_admin:
            print("That username already exist.")
            return 

        password = getpass("Enter admin password: ")
        confirm_password = getpass("Confirm admin password: ")

        if len(password) < 12:
            print("Password must be at least 12 characters.")
            return

        if password != confirm_password:
            print("Password do not match.")
            return 

        admin = Admin(username=username)
        admin.set_password(password)

        try:
            db.session.add(admin)
            db.session.commit()
            print(f"\nAdmin account '{username}' created successfully!")

        except Exception:
            db.session.rollback()
            print("Could not create the admin account.")
            raise 


if __name__ == "__main__":
    create_admin()