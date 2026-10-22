import os
import uuid 
import resend 

from werkzeug.utils import secure_filename
from extensions import db
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from html import escape
from dotenv import load_dotenv

from area_grouping import group_reports_by_area

from flask_login import (LoginManager,
                         login_user,
                         logout_user,
                         login_required,
                         current_user)
from flask import (Flask, 
                   render_template, 
                   request, 
                   redirect, 
                   url_for, 
                   flash,
                   jsonify,
                   current_app)

# Email
load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

if not app.config["SECRET)KEY"]:
    raise RuntimeError("SECRET_KEY environment variable is required.")

app.config["SQLALCHEMY_DATABASE_URI"] = ("sqlite:///" + os.path.join(app.instance_path, "potholes.db"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False 

app.config["UPLOAD_FOLDER"] = os.path.join(
    app.root_path, "static", "uploads"
)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB maximum

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.instance_path, exist_ok=True)

db.init_app(app)

from models import (Pothole,
                    Admin)
from forms import (PotholeReportForm, 
                   AdminLoginForm, 
                   AdminStatusForm,
                   BulkAreaStatusForm,
                   DeleteReportForm)

# Login
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "admin_login"
login_manager.login_message = "Please log in to access the admin area."
login_manager.login_message_category = "warning"

# Default repair notes
DEFAULT_REPAIR_NOTES = "Pothole repaired and road surface patched."



@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(Admin, int(user_id))
    except (ValueError, TypeError):
        return None

def send_new_report_notification(report):
    """Email the administrator when a new pothole report is submitted."""

    api_key = os.getenv("RESEND_API_KEY")
    admin_email = os.getenv("ADMIN_NOTIFICATION_EMAIL")

    if not api_key or not admin_email:
        app.logger.warning(
            "New report email skipped: email settings are missing."
        )
        return 

    try:
        resend.api_key = api_key

        app_url = os.getenv("APP_BASE_URL", "").rstrip("/")

        report_path = url_for(
            "admin_report_details",
            pothole_id=report.id
        )

        admin_link = f"{app_url}{report_path}" if app_url else report_path

        description = escape(report.description or "No description provided")
        severity = escape(report.severity or "Not specified")
        report_date = (
            report.created_at.strftime("%B %d, %Y at %I:%M %p")
            if report.created_at
            else "Not available"
        )

        resend.Emails.send({
            "from": os.getenv(
                "RESEND_FROM_EMAIL",
                "onboarding@resend.dev"
            ),
            "to": [admin_email],
            "subject": f"New Pothole Report #{report.id}",
            "html": f"""
                <h2>New Pothole Report Submitted</h2>

                <p>A resident has submitted a new pothole report.</p>

                <p><strong>Report ID:</strong> #{report.id}</p>
                <p><strong>Severity:</strong> {severity}</p>
                <p><strong>Description:</strong> {description}</p>
                <p><strong>Date submitted:</strong> {report_date}</p>
                <p><strong>Latitude:</strong> {report.latitude}</p>
                <p><strong>Longitude:</strong> {report.longitude}</p>

                <p>
                    <a href="{escape(admin_link, quote=True)}">
                        View Report Details
                    </a>
                </p>
                """
        })

        app.logger.info(
            "New report notification sent for report #%s.",
            report.id
        )

    except Exception:
        # Email failure must not undo a successfully saved report.
        app.logger.exception(
            "Email notification failed for report #%s.",
            report.id
        )

# Admin Login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    # If an administrator is already logged in, go to the dashboard.
    if current_user.is_authenticated:
        return redirect(url_for("admin_dashboard"))

    form = AdminLoginForm()

    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data 

        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            login_user(admin)
            next_page = request.args.get("next")

            # Only allow redirects to local application paths.
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)

            return redirect(url_for("admin_dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("admin/login.html", form=form)


# Admin Dashboard
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    # Get all reports, newest first.
    all_reports = Pothole.query.order_by(
        Pothole.created_at.desc()
    ).all()

    for report in all_reports:
        print(
            f"Report #{report.id} | "
            f"Street: {report.street_name!r} | "
            f"Lat: {report.latitude} |"
            f"Lon: {report.longitude} |"
        )

    # Keep the existing Recent Reports section limited to 10.
    recent_reports = all_reports[:10]

    # Group reports by street name and geographic proximity.
    all_area_groups = group_reports_by_area(all_reports)

    # Pagination settings
    per_page = 10
    total_areas = len(all_area_groups)
    total_pages = max(1, (total_areas + per_page - 1) // per_page)

    page = request.args.get("page", 1, type=int)
    page = max(1, min(page, total_pages))

    # Get only the areas for the current page.
    start = (page - 1) * per_page
    end = start + per_page 
    area_groups = all_area_groups[start:end]

    # Count urgent areas across ALL pages
    urgent_count = sum(
        area.get("priority_level") == "high"
        for area in all_area_groups
    )

    # Existing dashboard counts.
    total_reports = len(all_reports)

    submitted_count = sum(
        report.status == "Submitted"
        for report in all_reports
    )

    under_review_count = sum(
        report.status == "Under Review"
        for report in all_reports
    )

    in_progress_count = sum(
        report.status == "In Progress"
        for report in all_reports
    )

    repaired_count = sum(
        report.status == "Repaired"
        for report in all_reports
    )

    # Create a status form for each recent report.
    status_forms = {}

    for pothole in recent_reports:
        status_forms[pothole.id] = AdminStatusForm(
            status=pothole.status,
            repair_notes=(
                pothole.repair_notes or DEFAULT_REPAIR_NOTES
            ),
        )

    return render_template(
        "admin/dashboard.html",
        total_reports=total_reports,
        submitted_count=submitted_count,
        under_review_count=under_review_count,
        in_progress_count=in_progress_count,
        repaired_count=repaired_count,
        recent_reports=recent_reports,
        status_forms=status_forms,
        area_groups=area_groups,
        total_areas=total_areas,
        total_pages=total_pages,
        page=page,
        urgent_count=urgent_count,
    )

# Admin Report Details
@app.route("/admin/reports/<int:pothole_id>")
@login_required
def admin_report_details(pothole_id):
    area_id = request.args.get("area_id")
    pothole = db.get_or_404(Pothole, pothole_id)

    form = AdminStatusForm(
        status=pothole.status,
        repair_notes=(
            pothole.repair_notes or DEFAULT_REPAIR_NOTES
        ),
    )

    return render_template(
        "admin/report_details.html",
        pothole=pothole,
        form=form,
        area_id=area_id,
        delete_form=DeleteReportForm(),
    )

# Admin Bulk Update
@app.route("/admin/areas/<area_id>/status", methods=["POST"])
@login_required
def update_area_status(area_id):
    form = BulkAreaStatusForm()

    # Rebuild the area groups so we update the current reports
    # belonging to this affected area
    all_reports = Pothole.query.order_by(
        Pothole.created_at.desc()
    ).all()

    area_groups = group_reports_by_area(all_reports)

    area = next(
        (
            group
            for group in area_groups
            if group["area_id"] == area_id 
        ),
        None,
    )

    if area is None:
        flash(
            "This affected area has changed or is no longer available.",
            "warning",
        )
        return redirect(url_for("admin_dashboard"))

    if not form.validate_on_submit():
        flash(
            "Unable to update the reports. Please check the form and photo.",
            "danger",
        )
        return redirect(
            url_for("admin_area_details", area_id=area_id)
        )

    new_status = form.status.data
    uploaded_photo = form.repair_photo.data 
    has_new_photo = bool(
        uploaded_photo and uploaded_photo.filename
    )

    repair_filename = None
    repair_path = None 

    if has_new_photo:
        original_filename = secure_filename(
            uploaded_photo.filename 
        )

        if not original_filename or "." not in original_filename:
            flash("Please upload a valid image filename.", "danger")
            return redirect(
                url_for("admin_area_details", area_id=area_id)
            )

        extension = original_filename.rsplit(".", 1)[-1].lower()

        if extension not in {"jpg", "jpeg", "png", "webp"}:
            flash(
                "Please upload a JPG, PNG, or WebP image.",
                "danger",
            )
            return redirect(
                url_for("admin_area_details", area_id=area_id)
            )

        repair_filename = f"{uuid.uuid4().hex}.{extension}"
        repair_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            repair_filename,
        )

    reports_to_update = area["reports"]
    now = datetime.now(timezone.utc)

    try:
        # Save the shared image only once.
        if has_new_photo:
            uploaded_photo.save(repair_path)

        for report in reports_to_update:
            report.status = new_status
            report.updated_at = now 

            if new_status == "Repaired":
                if has_new_photo:
                    report.repair_photo = repair_filename

                report.repair_notes = (
                    (form.repair_notes.data or "").strip()
                    or DEFAULT_REPAIR_NOTES
                )

                # Preserve the original completion data if already repaired.
                if report.repair_completed_at is None:
                    report.repair_completed_at = now 

        db.session.commit()

    except Exception:
        db.session.rollback()

        if repair_path and os.path.exists(repair_path):
            os.remove(repair_path)

        app.logger.exception(
            "Failed to bulk-update affected-area reports."
        )

        flash(
            "An error occured while updating the reports."
            "No changes were saved.",
            "danger",
        )

        return redirect(
            url_for("admin_area_details", area_id=area_id)
        )

    if new_status == "Repaired" and has_new_photo:
        flash(
            f"Successfully marked {len(reports_to_update)} reports "
            "as Repaired. The after-repair photo was applied to all reports.",
            "success",
        )
    elif new_status == "Repaired":
        flash(
            f"Successfully marked {len(reports_to_update)} reports "
            "as Repaired. No new photo was uploaded; existing photos "
            "were preserved.",
            "success",
        )
    else:
        flash(
            f"Successfully updated {len(reports_to_update)} reports "
            f"to {new_status}.",
            "success",
        )

    return redirect(
        url_for("admin_area_details", area_id=area_id)
    )

# Admin Area Details
@app.route("/admin/areas/<area_id>")
@login_required
def admin_area_details(area_id):
    bulk_form = BulkAreaStatusForm()

    page = request.args.get("page", 1, type=int)
    page = max(page, 1)

    all_reports = Pothole.query.order_by(
        Pothole.created_at.desc()
    ).all()

    area_groups = group_reports_by_area(all_reports)

    area = next(
        (
            group for group in area_groups
            if group["area_id"] == area_id 
        ),
        None, 
    )

    if area is None:
        flash(
            "This affected area has changed or is no longer available."
            "Please select an area from the dashboard.",
            "warning",
        )
        return redirect(url_for("admin_dashboard"))

    per_page = 20
    total_reports = len(area["reports"])
    total_pages = max(1, (total_reports + per_page - 1) // per_page)

    if page > total_pages:
        page = total_pages

    start = (page - 1) * per_page 
    paginated_reports = area["reports"][start:start + per_page]

    return render_template(
        "admin/area_details.html",
        area=area,
        reports=paginated_reports,
        page=page,
        per_page=per_page,
        total_reports=total_reports,
        total_pages=total_pages,
        bulk_form=bulk_form,
    )

# Admin Logout
@app.route("/admin/logout", endpoint="logout")
@login_required
def admin_logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin_login"))

# Status Form
@app.route("/admin/reports/<int:pothole_id>/status", methods=["POST"])
@login_required
def update_report_status(pothole_id):
    pothole = db.get_or_404(Pothole, pothole_id)
    form = AdminStatusForm()

    if not form.validate_on_submit():
        flash(
            "Unable to update the report. Please check the form and photo.",
            "danger",
        )
        return redirect(url_for("admin_dashboard"))

    new_status = form.status.data
    uploaded_photo = form.repair_photo.data

    has_new_photo = (
        uploaded_photo is not None
        and uploaded_photo.filename
    )

    # A repaired report must have a repair photo.
    if (
        new_status == "Repaired"
        and not pothole.repair_photo
        and not has_new_photo
    ):
        flash(
            "Please upload an after-repair photo before marking "
            "this report as repaired.",
            "warning",
        )
        return redirect(url_for("admin_dashboard"))

    # Prepare a unique filename for a new repair photo.
    repair_filename = None
    repair_path = None

    if has_new_photo:
        original_filename = secure_filename(
            uploaded_photo.filename
        )

        if not original_filename or "." not in original_filename:
            flash("Please upload a valid image filename.", "danger")
            return redirect(url_for("admin_dashboard"))

        extension = original_filename.rsplit(".", 1)[-1].lower()

        if extension not in {"jpg", "jpeg", "png", "webp"}:
            flash(
                "Please upload a JPG, PNG, or WebP image.",
                "danger",
            )
            return redirect(url_for("admin_dashboard"))

        repair_filename = f"{uuid.uuid4().hex}.{extension}"
        repair_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            repair_filename,
        )

    old_status = pothole.status
    old_repair_photo = pothole.repair_photo
    old_repair_notes = pothole.repair_notes
    old_completed_at = pothole.repair_completed_at

    try:
        # Save the image before committing its filename.
        if has_new_photo:
            uploaded_photo.save(repair_path)
            pothole.repair_photo = repair_filename

        pothole.status = new_status
        pothole.updated_at = datetime.now(timezone.utc)

        if new_status == "Repaired":
            pothole.repair_notes = (
                form.repair_notes.data or ""
            ).strip() or DEFAULT_REPAIR_NOTES

            # Preserve the original completion timestamp if this
            # report was already marked repaired.
            if pothole.repair_completed_at is None:
                pothole.repair_completed_at = datetime.now(
                    timezone.utc
                )

        # Keep repair history when the status changes later.
        db.session.commit()

    except Exception:
        db.session.rollback()

        pothole.status = old_status
        pothole.repair_photo = old_repair_photo
        pothole.repair_notes = old_repair_notes
        pothole.repair_completed_at = old_completed_at

        if repair_path and os.path.exists(repair_path):
            os.remove(repair_path)

        app.logger.exception(
            "Failed to update pothole report status."
        )

        flash(
            "The report could not be updated. Please try again.",
            "danger",
        )
        return redirect(url_for("admin_dashboard"))

    flash("Report status updated successfully!", "success")
    return redirect(url_for("admin_dashboard"))

# Index
@app.route("/")
def index():
    form = PotholeReportForm()
    return render_template(
        "index.html",
        form=form
    )

# Submit Report Form
@app.route("/submit-report", methods=["POST"])
def submit_report():

    print("Received street name:", request.form.get("street_name"))
    print("Received full address:", request.form.get("location_address"))

    form = PotholeReportForm()

    # Validate the WTForms fields and CSRF token
    if not form.validate_on_submit():
        return render_template("index.html", form=form), 400

    # Read coordinates supplied by the map
    latitude = request.form.get("latitude", type=float)
    longitude = request.form.get("longitude", type=float)

    if latitude is None or longitude is None:
        flash(
            "Please select and confirm a pothole location on the map.",
            "danger",
        )
        return redirect(url_for("index") + "#report")

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        flash("The selected coordinates are invalid.", "danger")
        return redirect(url_for("index") + "#report")

    # Get validated WTForms data
    description = form.description.data.strip()
    severity = form.severity.data

    # Handle optional photo upload
    photo = form.photo.data
    photo_filename = None
    photo_path = None

    if photo and photo.filename:
        original_filename = secure_filename(photo.filename)

        if (
            not original_filename
            or "." not in original_filename
        ):
            flash("Please upload a valid image filename.", "danger")
            return redirect(url_for("index") + "#report")

        extension = original_filename.rsplit(".", 1)[-1].lower()

        if extension not in {"jpg", "jpeg", "png", "webp"}:
            flash(
                "Please upload a JPG, PNG, or WebP image.",
                "danger",
            )
            return redirect(url_for("index") + "#report")

        photo_filename = f"{uuid.uuid4().hex}.{extension}"

        photo_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            photo_filename,
        )

        photo.save(photo_path)

    # Read the street information returned by the map.
    street_name = (
        request.form.get("street_name", "").strip()[:255] or None 
    )

    location_address = (
        request.form.get("location_address", "").strip()[:500] or None 
    )

    # Create and save the pothole report.
    report = Pothole(
        latitude=latitude,
        longitude=longitude,
        street_name=street_name,
        location_address=location_address,
        description=description,
        severity=severity,
        photo=photo_filename,
    )
    
    try:
        db.session.add(report)
        db.session.commit()

    except Exception:
        db.session.rollback()

        # Remove the uploaded file if the database save fails
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)

        app.logger.exception("Failed to save pothole report.")

        flash(
            "We couldn't save your report. Please try again.",
            "danger",
        )
        return redirect(url_for("index") + "#report")

    # Notify the administrator after the report has been saved.
    send_new_report_notification(report)

    flash(
        "Your pothole report was submitted successfully!",
        "success",    
    )
    return redirect(url_for("index") + "#report")

# API: Get pothole reports for the map
@app.route("/api/potholes")
def api_potholes():
    potholes = Pothole.query.order_by(
        Pothole.created_at.desc()
    ).all()

    reports_data = []

    for pothole in potholes:
        reports_data.append({
            "id": pothole.id,
            "latitude": pothole.latitude,
            "longitude": pothole.longitude,
            "description": pothole.description,
            "severity": pothole.severity,
            "status": pothole.status,
            "created_at": (
                pothole.created_at.isoformat()
                if pothole.created_at
                else None
            ),
            "photo_url": (
                url_for(
                    "static",
                    filename=f"uploads/{pothole.photo}"
                )
                if pothole.photo 
                else None 
            ),
            "details_url": url_for(
                "report_details",
                pothole_id=pothole.id
            ),
        })

    return jsonify(reports_data)

# Reports
@app.route("/reports")
def reports():
    page = request.args.get("page", 1, type=int)

    # Read the selected filters from the URL
    severity = request.args.get("severity", "").strip()
    status = request.args.get("status", "").strip()
    street = request.args.get("street", "").strip()

    # Available filter options.
    severity_options = ["Low", "Medium", "High"]
    status_options = [
        "Submitted",
        "Under Review",
        "In Progress",
        "Repaired",
    ]

    # Get unique street names for the street dropdown.
    street_options = [
        row[0]
        for row in db.session.query(Pothole.street_name)
        .filter(
            Pothole.street_name.isnot(None),
            Pothole.street_name != "",
        )
        .distinct()
        .order_by(Pothole.street_name.asc())
        .all()
    ]

    # All reports for the map, regardless of selected filters.
    all_potholes = Pothole.query.order_by(
        Pothole.created_at.desc()
    ).all()

    # Hide repaired areas from the public map after 30 days
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=30)

    area_groups = group_reports_by_area(all_potholes)
    hidden_report_ids = set()

    for area in area_groups:
        # Only hide an area when every report has been repaired
        if area["unresolved_count"] != 0:
            continue

        area_reports = area["reports"]
        completion_dates = []

        # Require a completion timestamp for every report.
        for report in area_reports:
            completed_at = report.repair_completed_at

            if completed_at is None:
                completion_dates = []
                break 

            # SQLite may return a naive datetime. Treat it as UTC 
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(
                    tzinfo = timezone.utc 
                )
            else:
                completed_at = completed_at.astimezone(timezone.utc)

            completion_dates.append(completed_at)

        # Use the latest repair data for the entire area.
        if (
            completion_dates
            and len(completion_dates) == len(area_reports)
            and max(completion_dates) < cutoff_date
        ):
            hidden_report_ids.update(
                report.id for report in area_reports
            )

    # Only these reports will be displayed as markers on the public map.
    map_potholes = [
        report 
        for report in all_potholes
        if report.id not in hidden_report_ids
    ]

    # Build the query used for the report cards.
    reports_query = Pothole.query

    if severity in severity_options:
        reports_query = reports_query.filter_by(
            severity=severity 
        )
    else:
        severity = ""

    if status in status_options:
        reports_query = reports_query.filter_by(
            status=status 
        )
    else:
        status = ""

    if street in street_options:
        reports_query = reports_query.filter_by(
            street_name=street 
        )
    else:
        street = ""

    # Newest reports first; six report cards per page
    pagination = reports_query.order_by(
        Pothole.created_at.desc()
    ).paginate(
        page=page,
        per_page=6,
        error_out=False, 
    )

    return render_template(
        "reports.html",
        potholes=pagination.items,
        pagination=pagination,
        map_potholes=map_potholes,
        severity_options=severity_options,
        status_options=status_options,
        street_options=street_options,
        selected_severity=severity,
        selected_status=status,
        selected_street=street,
    )
        
# Report Details
@app.route("/reports/<int:pothole_id>")
def report_details(pothole_id):
    pothole = db.session.get(Pothole, pothole_id)

    if pothole is None:
        flash("Pothole report not found.", "warning")
        return redirect(url_for("reports"))

    return render_template(
        "report_details.html",
        pothole=pothole
    )


# Delete an individual report (admin only)
@app.route("/admin/report/<int:pothole_id>/delete", methods=["POST"])
@login_required
def delete_report(pothole_id):
    delete_form = DeleteReportForm()

    # Validate the form and CSRF token.
    if not delete_form.validate_on_submit():
        flash(
            "Invalid delete request. Please try again.",
            "danger"
        )
        return redirect(url_for("admin_dashboard"))

    pothole = db.session.get(Pothole, pothole_id)

    if pothole is None:
        flash("Report not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    report_id = pothole.id 

    # Save the photo filenames before deleting the database record
    photo_filenames = {
        filename 
        for filename in (pothole.photo, pothole.repair_photo)
        if filename 
    }

    # Delete the database record first
    try:
        db.session.delete(pothole)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to delete report #%s", report_id
        )
        flash(
            "Could not delete the report. Please try again.",
            "danger"
        )
        return redirect(url_for("admin_dashboard"))

    # Remove associated uploaded photos, if they exist.
    upload_folder = current_app.config.get(
        "UPLOAD_FOLDER",
        os.path.join(current_app.root_path, "static", "uploads")
    )

    for filename in photo_filenames:
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(upload_folder, safe_filename)

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except OSError:
            current_app.logger.exception(
                "Could not remove photo for report #%s",
                report_id
            )

    flash(
        f"Report #{report_id} was deleted successfully.",
        "success"
    )

    return redirect(url_for("admin_dashboard"))
# Debug
@app.route("/debug-time")
def debug_time():
    latest_report = Pothole.query.order_by(
        Pothole.id.desc()
    ).first()

    if latest_report is None:
        return "No reports found."

    return {
        "database_created_at": str(latest_report.created_at),
        "guam_created_at": str(latest_report.created_at_guam),
        "utc_now": str(datetime.now(timezone.utc)),
        "guam_now": str(
            datetime.now(ZoneInfo("Pacific/Guam"))
        )
    }

# Test Flask
@app.route("/test-flash")
def test_flash():
    flash("Test flash message is working!", "success")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)

    