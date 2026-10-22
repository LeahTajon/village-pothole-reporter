# Village Pothole Reporter

A responsive web application that allows residents of Dededo, Guam, to report potholes, view reported road issues on an interactive map, and track repair progress.

This project was built as a portfolio project to demonstrate web development skills using Python, Flask, databases, mapping tools, and responsive web design.

## Features

- **Submit pothole reports** without creating an account.
- **Interactive map** with street and satellite views.
- **Location selection** by searching for a place or selecting a point on the map.
- **Report details** including description, severity, street name, location, and photo.
- **Browse and filter reports** by severity, status, and street.
- **Affected-area grouping** to organize nearby reports and help identify areas that may need attention.
- **Administrative dashboard** for reviewing reports and managing their status.
- **Repair updates** with repair notes and after-repair photos.
- **Email notifications** for new reports.
- **Responsive interface** for desktop and mobile devices.

## Built With

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- Flask-WTF
- Flask-Login
- HTML, CSS, and JavaScript
- Bootstrap
- Leaflet
- OpenStreetMap
- Esri World Imagery
- Resend for email notifications

## Project Purpose

The goal of this project is to explore how a simple web application can help a community document road issues, make reports easier to access, and provide a clearer view of reported potholes and their repair progress.

The application focuses on Dededo, Guam, as a portfolio demonstration.

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/LeahTajon/village-pothole-reporter.git
cd village-pothole-reporter
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. Add the environment variables required by the application:

```env
SECRET_KEY=your-secret-key
RESEND_API_KEY=your-resend-api-key
```

Replace the example values with your own. **Never commit your `.env` file or publish secret keys.**

### 5. Initialize the database

Follow the database setup instructions in `create_db.py` and any project-specific setup steps before starting the application.

### 6. Run the application

```bash
flask --app app run --debug
```

Open the local address shown in your terminal, usually `http://127.0.0.1:5000`.

## Notes

- This project is intended as a portfolio demonstration, not an official municipal reporting system.
- Use fictional or sample data for public demonstrations.
- Local SQLite data and uploaded files may not persist when deployed on hosting services with an ephemeral filesystem.
- Map tiles, geocoding, and email notifications depend on their respective external services and configuration.

## Author

**Leah Tajon**

GitHub: [LeahTajon](https://github.com/LeahTajon)
