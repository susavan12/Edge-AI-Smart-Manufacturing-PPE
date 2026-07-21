# ==========================================
# IMPORTS
# ==========================================

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    send_file
)

from werkzeug.utils import secure_filename

import os
import io
import cv2
import uuid
import time
import base64
import numpy as np
from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME", "ppe.db")

from PIL import Image

from datetime import datetime

from openpyxl import Workbook

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ==========================================
# PROJECT IMPORTS
# ==========================================

from detector import PPEDetector

from report import generate_report

from email_alert import send_violation_email

from database import (

    create_database,

    save_detection,

    get_all_detections,

    get_dashboard_data,

    get_chart_data,

    get_alert_email,

    update_alert_email,

    get_admin_credentials,

    update_admin_credentials,

    delete_detection,

    get_detection_by_id

)

# ==========================================
# FLASK APP
# ==========================================

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

# ==========================================
# DATABASE
# ==========================================

create_database()

# ==========================================
# FOLDERS
# ==========================================

UPLOAD_FOLDER = "static/uploads"

RESULT_FOLDER = "static/results"

VIOLATION_FOLDER = "static/violations"

REPORT_FOLDER = "static/reports"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

os.makedirs(RESULT_FOLDER, exist_ok=True)

os.makedirs(VIOLATION_FOLDER, exist_ok=True)

os.makedirs(REPORT_FOLDER, exist_ok=True)

# ==========================================
# LOAD YOLO MODEL
# ==========================================

detector = PPEDetector()

# ==========================================
# GLOBAL VARIABLES
# ==========================================

last_status = "SAFE"

last_save_time = 0

# Prevent false alarms

unsafe_counter = 0

safe_counter = 0

MIN_UNSAFE_FRAMES = 3

MIN_SAFE_FRAMES = 2

# ==========================================
# IMAGE SETTINGS
# ==========================================

JPEG_QUALITY = 80

FRAME_WIDTH = 416

FRAME_HEIGHT = 416

# =====================================
# ROI (Region Of Interest)
# =====================================

ROI_X1 = 50
ROI_Y1 = 80

ROI_X2 = 590
ROI_Y2 = 470

# ==========================================
# HELPER FUNCTION
# ==========================================

def encode_image(image):

    """
    Convert OpenCV image to Base64 JPEG.
    """

    encode_param = [

        int(cv2.IMWRITE_JPEG_QUALITY),

        JPEG_QUALITY

    ]

    success, buffer = cv2.imencode(

        ".jpg",

        image,

        encode_param

    )

    if not success:

        return ""

    return base64.b64encode(buffer).decode()

# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return render_template("index.html")


# ==========================================
# HISTORY
# ==========================================

@app.route("/history")
def history():

    if not session.get("admin"):

        return redirect("/login")

    detections = get_all_detections()

    return render_template(

        "history.html",

        detections=detections

    )


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()

        password = request.form["password"].strip()

        db_username, db_password = get_admin_credentials()

        if username == db_username and password == db_password:

            session["admin"] = True

            return redirect("/admin")

        return render_template(

            "login.html",

            error="Invalid Username or Password"

        )

    return render_template("login.html")


# ==========================================
# ADMIN PANEL
# ==========================================

@app.route("/admin")
def admin():

    if not session.get("admin"):

        return redirect("/login")

    dashboard = get_dashboard_data()

    current_email = get_alert_email()

    return render_template(

        "admin.html",

        dashboard=dashboard,

        current_email=current_email

    )


# ==========================================
# SETTINGS
# ==========================================

@app.route("/settings")
def settings():

    if not session.get("admin"):

        return redirect("/login")

    return render_template("settings.html")


# ==========================================
# EMAIL SETTINGS
# ==========================================

@app.route("/email_settings", methods=["GET", "POST"])
def email_settings():

    if not session.get("admin"):

        return redirect("/login")

    if request.method == "POST":

        email = request.form["email"].strip()

        update_alert_email(email)

        return redirect("/admin")

    return render_template(

        "email_settings.html",

        email=get_alert_email()

    )


# ==========================================
# ADMIN CREDENTIALS
# ==========================================

@app.route("/admin_credentials", methods=["GET", "POST"])
def admin_credentials():

    if not session.get("admin"):

        return redirect("/login")

    if request.method == "POST":

        username = request.form["username"].strip()

        password = request.form["password"]

        confirm = request.form["confirm_password"]

        if password != confirm:

            return render_template(

                "admin_credentials.html",

                username=username,

                error="Passwords do not match."

            )

        update_admin_credentials(

            username,

            password

        )

        return redirect("/settings")

    username, _ = get_admin_credentials()

    return render_template(

        "admin_credentials.html",

        username=username

    )


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if not session.get("admin"):

        return redirect("/login")

    return render_template(

        "dashboard.html",

        data=get_dashboard_data()

    )


# ==========================================
# DASHBOARD API
# ==========================================

@app.route("/dashboard_data")
def dashboard_data():

    return jsonify(

        get_dashboard_data()

    )


@app.route("/chart_data")
def chart_data():

    return jsonify(

        get_chart_data()

    )


# ==========================================
# RECENT VIOLATIONS
# ==========================================

@app.route("/get_violations")
def get_violations():

    violations = []

    if os.path.exists(VIOLATION_FOLDER):

        files = sorted(

            os.listdir(VIOLATION_FOLDER),

            reverse=True

        )

        for file in files[:10]:

            violations.append({

                "name": file,

                "path": f"/static/violations/{file}"

            })

    return jsonify(

        violations

    )


# ==========================================
# LIVE CAMERA
# ==========================================

@app.route("/camera")
def camera():

    return render_template("camera.html")

def box_iou(boxA, boxB):

    ax1, ay1, ax2, ay2 = boxA
    bx1, by1, bx2, by2 = boxB

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_width = max(0, inter_x2 - inter_x1)
    inter_height = max(0, inter_y2 - inter_y1)

    inter_area = inter_width * inter_height

    areaA = (ax2 - ax1) * (ay2 - ay1)
    areaB = (bx2 - bx1) * (by2 - by1)

    union = areaA + areaB - inter_area

    if union == 0:
        return 0

    return inter_area / union

# =====================================
# Check whether center of one box
# lies inside another box
# =====================================

def center_inside(region_box, object_box):

    rx1, ry1, rx2, ry2 = region_box
    ox1, oy1, ox2, oy2 = object_box

    center_x = (ox1 + ox2) / 2
    center_y = (oy1 + oy2) / 2

    return (
        rx1 <= center_x <= rx2 and
        ry1 <= center_y <= ry2
    )

# ==========================================
# Live Camera Detection
# ==========================================

@app.route("/detect", methods=["POST"])
def detect():

    global last_status
    global last_save_time
    global unsafe_counter
    global safe_counter

    # =====================================
    # Receive Image
    # =====================================

    data = request.json.get("image")

    if not data:
        return jsonify({"error": "No image"}), 400

    try:

        encoded = data.split(",", 1)[1]

        image_bytes = base64.b64decode(encoded)

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        frame = np.array(image)

        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    except Exception:

        return jsonify({"error": "Invalid Image"}), 400

    # =====================================
    # Resize
    # =====================================

    frame = cv2.resize(
        frame,
        (FRAME_WIDTH, FRAME_HEIGHT),
        interpolation=cv2.INTER_AREA
    )

    # =====================================
    # YOLO Detection
    # =====================================

    results = detector.detect(frame)

    result = results[0]

    print("\n========== YOLO DETECTIONS ==========")

    for box in result.boxes:

        cls = int(box.cls[0])
        conf = float(box.conf[0])

        print(result.names[cls], round(conf, 2))

    print("=====================================\n")

    output = result.plot()

    names = result.names

    boxes = result.boxes

    # =====================================
    # Counters
    # =====================================

    person = 0
    hardhat = 0
    vest = 0

    no_hardhat = 0
    no_vest = 0

    workers_without_helmet = 0
    workers_without_vest = 0

    # =====================================
    # Bounding Box Lists
    # =====================================

    person_boxes = []
    helmet_boxes = []
    vest_boxes = []

    # =====================================
    # Read Detection
    # =====================================

    for box in boxes:

        conf = float(box.conf[0])

        cls = int(box.cls[0])

        label = names[cls]

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        w = x2 - x1
        h = y2 - y1

        if w < 20 or h < 20:
            continue

        # ------------------------------
        # ROI only for Person
        # ------------------------------

        if label == "Person":

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            inside_roi = (

                ROI_X1 <= center_x <= ROI_X2 and
                ROI_Y1 <= center_y <= ROI_Y2

            )

            if not inside_roi:
                continue

        # ------------------------------
        # Store detections
        # ------------------------------

        if label == "Person" and conf >= 0.45:

            person += 1

            person_boxes.append((x1, y1, x2, y2))

        elif label == "Hardhat" and conf >= 0.45:

            hardhat += 1

            helmet_boxes.append((x1, y1, x2, y2))

        elif label == "Safety Vest" and conf >= 0.45:

            vest += 1

            vest_boxes.append((x1, y1, x2, y2))

        elif label == "NO-Hardhat" and conf >= 0.55:

            no_hardhat += 1

        elif label == "NO-Safety Vest" and conf >= 0.55:

            no_vest += 1

    # =====================================
    # NO PERSON
    # =====================================

    if person == 0:

        status = "NO PERSON"

        current_status = "NO PERSON"

        unsafe_counter = 0
        safe_counter = 0

        last_status = "NO PERSON"

    else:

        unsafe_person = 0
        
        print("---------------------")

        for box in result.boxes:

            cls = int(box.cls[0])

            conf = float(box.conf[0])

            print(result.names[cls], round(conf, 2))

        # =====================================
        # PPE Verification
        # =====================================
        
        print("Starting PPE verification...")

        for px1, py1, px2, py2 in person_boxes:

            helmet_found = False
            vest_found = False

            # ------------------------------
            # Head Region
            # ------------------------------

            head_box = (

                px1,
                py1,
                px2,
                py1 + int((py2 - py1) * 0.35)

            )

            for hx1, hy1, hx2, hy2 in helmet_boxes:

                if center_inside(

                    head_box,

                    (hx1, hy1, hx2, hy2)

                ):

                    helmet_found = True
                    break

            # ------------------------------
            # Body Region
            # ------------------------------

            body_box = (

                px1,
                py1 + int((py2 - py1) * 0.25),

                px2,

                py1 + int((py2 - py1) * 0.85)

            )

            for vx1, vy1, vx2, vy2 in vest_boxes:

                if center_inside(

                    body_box,

                    (vx1, vy1, vx2, vy2)

                ):

                    vest_found = True
                    break

            print(
                "Helmet:",
                helmet_found,
                "Vest:",
                vest_found
            )

            if not helmet_found:

                workers_without_helmet += 1

            if not vest_found:

                workers_without_vest += 1

            if (not helmet_found) or (not vest_found):

                unsafe_person += 1

        print("unsafe_person =", unsafe_person)
        print("workers_without_helmet =", workers_without_helmet)
        print("workers_without_vest =", workers_without_vest)

        current_status = "SAFE" if unsafe_person == 0 else "UNSAFE"
        print("Current Status =", current_status)

        # =====================================
        # Temporal Filtering
        # =====================================

        if current_status == "UNSAFE":

            unsafe_counter += 1
            safe_counter = 0

            if unsafe_counter >= MIN_UNSAFE_FRAMES:
                status = "UNSAFE"
            else:
                status = last_status

        elif current_status == "SAFE":

            safe_counter += 1
            unsafe_counter = 0

            if safe_counter >= MIN_SAFE_FRAMES:
                status = "SAFE"
            else:
                status = last_status

        else:

            status = "NO PERSON"
            unsafe_counter = 0
            safe_counter = 0

        last_status = status

        print("Final Status =", status)

    # =====================================
    # Draw Detection
    # =====================================

    output = result.plot()

    # =====================================
    # Draw ROI
    # =====================================

    cv2.rectangle(
        output,
        (ROI_X1, ROI_Y1),
        (ROI_X2, ROI_Y2),
        (255, 255, 0),
        2
    )

    cv2.putText(
        output,
        "WORK AREA",
        (ROI_X1 + 5, ROI_Y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2
    )

    # =====================================
    # Status Color
    # =====================================

    if status == "SAFE":

        banner_color = (0, 170, 0)
        text_color = (0, 255, 0)

    elif status == "UNSAFE":

        banner_color = (0, 0, 255)
        text_color = (0, 0, 255)

    else:

        banner_color = (0, 170, 170)
        text_color = (0, 255, 255)

    # =====================================
    # Top Banner
    # =====================================

    cv2.rectangle(
        output,
        (0, 0),
        (output.shape[1], 45),
        banner_color,
        -1
    )

    if status == "SAFE":

        banner_text = "SAFE : ALL WORKERS WEARING PPE"

    elif status == "UNSAFE":

        banner_text = "WARNING : PPE VIOLATION DETECTED"

    else:

        banner_text = "NO WORKER DETECTED"

    cv2.putText(
        output,
        banner_text,
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    # =====================================
    # Information Panel
    # =====================================

    cv2.rectangle(
        output,
        (10, 55),
        (360, 235),
        (35, 35, 35),
        -1
    )

    cv2.putText(
        output,
        f"STATUS : {status}",
        (25, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        text_color,
        2
    )

    cv2.putText(
        output,
        f"Workers : {person}",
        (25, 115),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        output,
        f"Helmet : {hardhat}",
        (25, 145),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        output,
        f"Without Helmet : {workers_without_helmet}",
        (25, 175),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 0, 255),
        2
    )

    cv2.putText(
        output,
        f"Vest : {vest}",
        (25, 205),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )

    cv2.putText(
        output,
        f"Without Vest : {workers_without_vest}",
        (25, 235),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (0, 0, 255),
        2
    )
    # =====================================
    # Save Violations
    # =====================================

    current_time = time.time()
    save_event = False

    if status == "UNSAFE" and person > 0:

        if last_status != "UNSAFE":

            save_event = True

        elif current_time - last_save_time >= 10:

            save_event = True

    if save_event:

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"violation_{timestamp}.jpg"

        violation_path = os.path.join(
            VIOLATION_FOLDER,
            filename
        )

        cv2.imwrite(
            violation_path,
            output
        )

        save_detection(
            image=filename,
            result=filename,
            persons=person,
            hardhat=hardhat,
            no_hardhat=workers_without_helmet,
            vest=vest,
            no_vest=workers_without_vest,
            status=status
        )

        try:

            send_violation_email(
                image_path=violation_path,
                persons=person,
                no_hardhat=workers_without_helmet,
                no_vest=workers_without_vest
            )

            print("✓ Email Sent")

        except Exception as e:

            print("Email Error :", e)

        last_save_time = current_time

    # =====================================
    # Update Last Status
    # =====================================

    last_status = status

    # =====================================
    # Encode Image
    # =====================================

    image_string = encode_image(output)

    # =====================================
    # Count Saved Violations
    # =====================================

    try:

        violation_count = len(os.listdir(VIOLATION_FOLDER))

    except Exception:

        violation_count = 0

    # =====================================
    # Debug
    # =====================================

    print("Returned Status :", status)
    print(
        f"Workers={person}, "
        f"Helmet={hardhat}, "
        f"NoHelmet={workers_without_helmet}, "
        f"Vest={vest}, "
        f"NoVest={workers_without_vest}"
    )

    # =====================================
    # Return JSON
    # =====================================

    return jsonify({

        "image": "data:image/jpeg;base64," + image_string,

        "status": status,

        "person": person,

        "hardhat": hardhat,

        "no_hardhat": workers_without_helmet,

        "vest": vest,

        "no_vest": workers_without_vest,

        "violations": violation_count

    })
# ==========================================
# Prediction
# ==========================================

@app.route("/predict", methods=["POST"])
def predict():

    # ----------------------------------
    # Validate Upload
    # ----------------------------------

    if "image" not in request.files:
        return "No image uploaded."

    file = request.files["image"]

    if file.filename == "":
        return "No file selected."

    # ----------------------------------
    # Generate Unique File Name
    # ----------------------------------

    filename = secure_filename(file.filename)

    extension = os.path.splitext(filename)[1]

    unique_name = f"{uuid.uuid4().hex}{extension}"

    upload_path = os.path.join(
        UPLOAD_FOLDER,
        unique_name
    )

    result_path = os.path.join(
        RESULT_FOLDER,
        unique_name
    )

    # ----------------------------------
    # Save Uploaded Image
    # ----------------------------------

    file.save(upload_path)

    image = cv2.imread(upload_path)

    if image is None:
     return "Invalid Image"

    image = cv2.resize(

        image,

        (FRAME_WIDTH, FRAME_HEIGHT)

    )

    # =====================================
    # YOLO Prediction
    # =====================================

    results = detector.detect(image)

    result = results[0]

    annotated = result.plot()

    cv2.imwrite(
        result_path,
        annotated
    )

    names = result.names
    boxes = result.boxes

    # =====================================
    # Debug
    # =====================================

    print("====================================")
    print("Total detections :", len(boxes))

    # =====================================
    # Counters
    # =====================================

    person = 0
    hardhat = 0
    no_hardhat = 0
    vest = 0
    no_vest = 0

    # =====================================
    # Bounding Box Lists
    # =====================================

    person_boxes = []
    helmet_boxes = []
    vest_boxes = []

    # =====================================
    # Read Detections
    # =====================================

    for box in boxes:

        confidence = float(box.conf[0])
        cls = int(box.cls[0])
        label = names[cls]

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        width = x2 - x1
        height = y2 - y1

        # Ignore tiny detections
        if width < 25 or height < 25:
            continue

        print(
            f"{label} | Conf={confidence:.2f} | Box=({x1},{y1},{x2},{y2})"
        )

        if label == "Person":

            if confidence >= 0.25:

                person += 1
                person_boxes.append((x1, y1, x2, y2))

        elif label == "Hardhat":

            if confidence >= 0.40:

                hardhat += 1
                helmet_boxes.append((x1, y1, x2, y2))

        elif label == "Safety Vest":

            if confidence >= 0.40:

                vest += 1
                vest_boxes.append((x1, y1, x2, y2))

        elif label == "NO-Hardhat":

            if confidence >= 0.45:

                no_hardhat += 1

        elif label == "NO-Safety Vest":

            if confidence >= 0.45:

                no_vest += 1

    print("------------------------------------")
    print("Persons :", person)
    print("Helmet  :", hardhat)
    print("Vest    :", vest)
    print("NoHelmet:", no_hardhat)
    print("NoVest  :", no_vest)
    print("------------------------------------")

    print("Person Boxes:", len(person_boxes))
    print("Helmet Boxes:", len(helmet_boxes))
    print("Vest Boxes:", len(vest_boxes))
    # =====================================
    # Decide Status
    # =====================================

    if person == 0:

        status = "NO PERSON"

    elif no_hardhat > 0 or no_vest > 0:

        status = "UNSAFE"

    else:

        status = "SAFE"
    # ======================================
    # Save Detection to Database
    # ======================================

    # =====================================
    # Save Detection
    # =====================================

    save_detection(

    image=unique_name,
    result=unique_name,
    persons=person,
    hardhat=hardhat,
    no_hardhat=no_hardhat,
    vest=vest,
    no_vest=no_vest,
    status=status

   )

    return render_template(

    "result.html",

    original_image="/" + upload_path,

    detected_image="/" + result_path,

    person=person,

    hardhat=hardhat,

    no_hardhat=no_hardhat,

    vest=vest,

    no_vest=no_vest,

    status=status

    )

# ==========================================
# Generate PDF Report
# ==========================================

@app.route("/download_report")
def download_report():

    if not session.get("admin"):

        return redirect("/login")

    dashboard = get_dashboard_data()

    history = get_all_detections()

    report_path = os.path.join(
        REPORT_FOLDER,
        "PPE_Report.pdf"
    )

    generate_report(

        dashboard=dashboard,

        history=history,

        violation_folder=VIOLATION_FOLDER,

        output_path=report_path

    )

    return send_file(

        report_path,

        as_attachment=True

    )

@app.route("/details/<int:detection_id>")
def details(detection_id):

    detection = get_detection_by_id(detection_id)

    return render_template(
        "details.html",
        detection=detection
    )

@app.route("/delete/<int:detection_id>")
def delete_record(detection_id):

    if not session.get("admin"):
        return redirect("/login")

    delete_detection(detection_id)

    return redirect("/history")


@app.route("/export_excel")
def export_excel():

    if not session.get("admin"):
        return redirect("/login")

    detections = get_all_detections()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "PPE Detection History"

    # Header
    sheet.append([
        "ID",
        "Status",
        "Persons",
        "Hardhat",
        "No Hardhat",
        "Vest",
        "No Vest",
        "Date"
    ])

    # Data
    for row in detections:

        sheet.append([

            row[0],   # ID
            row[8],   # Status
            row[3],   # Persons
            row[4],   # Hardhat
            row[5],   # No Hardhat
            row[6],   # Vest
            row[7],   # No Vest
            row[9]    # Date

        ])

    filename = os.path.join(
        REPORT_FOLDER,
        "PPE_Detection_History.xlsx"
    )

    workbook.save(filename)

    return send_file(
        filename,
        as_attachment=True
    )


# ==========================================
# Clear All Data
# ==========================================

@app.route("/clear_data")
def clear_data():
    
    # -----------------------------
    # Admin Login Required
    # -----------------------------
    if not session.get("admin"):
        return redirect("/login")

    import glob
    import sqlite3
    import os

    # -----------------------------
    # Delete Result Images
    # -----------------------------
    for file in glob.glob(os.path.join(RESULT_FOLDER, "*")):

        try:
            os.remove(file)
        except:
            pass

    # -----------------------------
    # Delete Violation Images
    # -----------------------------
    for file in glob.glob(os.path.join(VIOLATION_FOLDER, "*")):

        try:
            os.remove(file)
        except:
            pass

    # -----------------------------
    # Delete Generated Reports
    # -----------------------------
    for file in glob.glob(os.path.join(REPORT_FOLDER, "*")):

        try:
            os.remove(file)
        except:
            pass

    # -----------------------------
    # Clear Database
    # -----------------------------
    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("DELETE FROM detections")

    cursor.execute(
        "DELETE FROM sqlite_sequence WHERE name='detections'"
    )

    connection.commit()

    connection.close()

    # -----------------------------
    # Return to Admin Panel
    # -----------------------------
    return redirect(url_for("admin"))

# ==========================================
# Logout
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# ==========================================
# Run Flask Application
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
