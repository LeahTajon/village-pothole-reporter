from app import app
from extensions import db
from models import Pothole

with app.app_context():
    db.create_all()
    print("Database and tables created successfully!")