
from sqlalchemy import inspect, text
from app import app, db

with app.app_context():
    inspector = inspect(db.engine)

    columns = {
        column["name"]
        for column in inspector.get_columns("pothole")
    }

    new_columns = {
        "repair_photo": "VARCHAR(255)",
        "repair_completed_at": "DATETIME",
        "repair_notes": "TEXT",
    }

    with db.engine.begin() as connection:
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE pothole "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )
                print(f"Added column: {column_name}")
            else:
                print(f"Already exists: {column_name}")

    print("Repair fields migration completed.")
