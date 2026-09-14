import os

print("Running app.py from:")
print(os.path.abspath(__file__))
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

    get_detection_by_id,

    add_employee,

    delete_employee_db,

    get_employee_details

)
from face_recognition import EmployeeRecognizer
from database import add_employee as save_employee
from database import get_all_employees
from flask import send_from_directory
from database import employee_exists

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

print(detector.model.names)

recognizer = EmployeeRecognizer()

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

# =====================================
# Face Recognition Memory
# =====================================

last_employee_name = "Unidentified Worker"
last_seen_time = 0
IDENTITY_MEMORY_SECONDS = 3

# ==========================================
# IMAGE SETTINGS
# ==========================================

JPEG_QUALITY = 80

FRAME_WIDTH = 1280

FRAME_HEIGHT = 720

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

# ======================================
# Employee Management Page
# ======================================

@app.route("/employee_management")
def employee_management():

    employees = get_all_employees()

    return render_template(

        "employee_management.html",

        employees=employees

    )


# ======================================
# Add Employee
# ======================================

@app.route("/add_employee", methods=["POST"])
def add_employee():

    employee_id = request.form["employee_id"]
    employee_name = request.form["employee_name"]
    department = request.form["department"]

    if employee_exists(employee_id):

        return """
        <h2 style='color:red;'>❌ Employee ID already exists.</h2>
        <br>
        <a href="/employee_management">Go Back</a>
        """

    image = request.files["employee_image"]

    if image.filename == "":
        return "No image selected."

    os.makedirs("employee_faces", exist_ok=True)

    filename = secure_filename(employee_id + ".jpg")

    image_path = os.path.join("employee_faces", filename)

    image.save(image_path)
    
    print("=" * 50)
    print("Saving image...")
    print("Path:", image_path)
    print("Exists after save:", os.path.exists(image_path))
    print("=" * 50)

    # Save employee information into database
    success = save_employee(
        employee_id,
        employee_name,
        department,
        filename
    )

    if not success:

        return """
        <h2 style='color:red;'>❌ Employee ID already exists.</h2>
        <br>
        <a href="/employee_management">Go Back</a>
        """
    # Reload employee database

    recognizer.load_database()

    print("Face database reloaded.")

    print("--------------------------------")
    print("Employee Saved")
    print("ID :", employee_id)
    print("Name :", employee_name)
    print("Department :", department)
    print("Image :", image_path)
    print("--------------------------------")

    return """
    <h2>Employee Saved Successfully.</h2>
    <br>
    <a href="/employee_management">Add Another Employee</a>
    """

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
    def calculate_iou(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)

        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])

        union = area1 + area2 - inter

        if union == 0:
            return 0

        return inter / union


    def is_duplicate_person(new_box, person_boxes, threshold=0.65):

        for person in person_boxes:

            old_box = person["box"]

            if calculate_iou(new_box, old_box) > threshold:
                return True

        return False


    def center_inside(region_box, object_box):

        rx1, ry1, rx2, ry2 = region_box
        ox1, oy1, ox2, oy2 = object_box

        center_x = (ox1 + ox2) / 2
        center_y = (oy1 + oy2) / 2

        return (
            rx1 <= center_x <= rx2 and
            ry1 <= center_y <= ry2
        )

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

    global last_employee_name
    global last_seen_time
    start_time = time.time()

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
    print("YOLO time:", round(time.time() - start_time, 3), "seconds")
    print("=================================")
    print("Total boxes:", len(results[0].boxes))

    for box in results[0].boxes:

        cls = int(box.cls[0])
        conf = float(box.conf[0])

        print(results[0].names[cls], conf)

    print("=================================")

    result = results[0]

    print("\n========== YOLO DETECTIONS ==========")

    for box in result.boxes:

        cls = int(box.cls[0])
        conf = float(box.conf[0])

        print(result.names[cls], round(conf, 2))

    print("=====================================\n")

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

    voice_messages = []

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

        frame_h, frame_w = frame.shape[:2]

        width = x2 - x1
        height = y2 - y1

        if label == "Person":
            print(
                "PERSON DETECTION:",
                "conf =", round(conf, 3),
                "width =", width,
                "height =", height,
                "box =", (x1, y1, x2, y2)
            )

        min_width = int(frame_w * 0.04)
        min_height = int(frame_h * 0.12)

        if width < min_width or height < min_height:
            continue

        employee_name = "Unknown"

        # -----------------------------
        # Face Recognition
        # -----------------------------

        if label == "Person":

            head_y2 = y1 + int((y2 - y1) * 0.45)

            face_crop = frame[y1:head_y2, x1:x2]

            # Check that the crop is valid
            if face_crop.size != 0:

                try:

                    employee_name = recognizer.recognize(face_crop)

                    if employee_name is None:
                        employee_name = "Unknown"

                except Exception as e:

                    print("Recognition Error:", e)
                    employee_name = "Unknown"

                # ------------------------------------
                # Identity Memory
                # ------------------------------------

                if employee_name not in ["Unknown", "Unidentified Worker"]:

                    last_employee_name = employee_name
                    last_seen_time = time.time()

                else:

                    if last_seen_time and time.time() - last_seen_time < IDENTITY_MEMORY_SECONDS:

                        employee_name = last_employee_name

                    else:

                        employee_name = "Unidentified Worker"

                print("Recognized:", employee_name)

        # -----------------------------
        # ROI Filtering
        # -----------------------------

        # if label == "Person":

        #     center_x = (x1 + x2) // 2
        #     center_y = (y1 + y2) // 2

        #     inside_roi = (
        #         ROI_X1 <= center_x <= ROI_X2 and
        #         ROI_Y1 <= center_y <= ROI_Y2
        #     )

        #     if not inside_roi:
        #         continue

        # -----------------------------
        # Save detections
        # -----------------------------

        if label == "Person" and conf >= 0.25:

            person += 1

            person_boxes.append({

                "box": (x1, y1, x2, y2),

                "name": employee_name

            })

            if employee_name not in ["Unknown", "Unidentified Worker"]:

                employee = get_employee_details(employee_name)

                if employee:

                    person_boxes[-1]["employee_id"] = employee[0]
                    person_boxes[-1]["department"] = employee[2]

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

        employee_ids = []
        employee_names = []
        departments = []
                
        print("Starting PPE verification...")

        for person_data in person_boxes:

            px1, py1, px2, py2 = person_data["box"]

            employee_name = person_data["name"]

            print("Checking PPE for:", employee_name)

            # ------------------------------------------
            # Get Employee Details
            # ------------------------------------------

            if employee_name not in ["Unknown", "Unidentified Worker"]:

                employee = get_employee_details(employee_name)

                if employee:

                    employee_id = employee[0]
                    employee_name_db = employee[1]
                    department = employee[2]

                else:

                    employee_id = "NA"
                    employee_name_db = employee_name
                    department = "NA"

            else:

                employee_id = "NA"
                employee_name_db = "Unidentified Worker"
                department = "NA"

            employee_ids.append(employee_id)

            employee_names.append(employee_name_db)

            departments.append(department)

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

                if center_inside(head_box, (hx1, hy1, hx2, hy2)):
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

                if center_inside(body_box, (vx1, vy1, vx2, vy2)):
                    vest_found = True
                    break

            print("Helmet:", helmet_found, "Vest:", vest_found)

            if not helmet_found:
                workers_without_helmet += 1

            if not vest_found:
                workers_without_vest += 1

            if (not helmet_found) or (not vest_found):
                unsafe_person += 1

            # ------------------------------
            # Voice Messages
            # ------------------------------

            if not helmet_found and not vest_found:

                if employee_name != "Unidentified Worker":
                    voice_messages.append(
                        f"{employee_name} is not wearing helmet and safety vest."
                    )

                else:

                    voice_messages.append(
                        "An unidentified worker is not wearing helmet and safety vest."
                    )

            elif not helmet_found:

                if employee_name != "Unidentified Worker":

                    voice_messages.append(
                        f"{employee_name} is not wearing helmet."
                    )

                else:

                    voice_messages.append(
                        "An unidentified worker is not wearing helmet."
                    )

            elif not vest_found:

                if employee_name != "Unidentified Worker":

                    voice_messages.append(
                        f"{employee_name} is not wearing safety vest."
                    )

                else:

                    voice_messages.append(
                        "An unidentified worker is not wearing safety vest."
                    )

        print("unsafe_person =", unsafe_person)
        print("workers_without_helmet =", workers_without_helmet)
        print("workers_without_vest =", workers_without_vest)

        current_status = "SAFE" if unsafe_person == 0 else "UNSAFE"
        print("Current Status =", current_status)

        print("Before temporal filter")
        print("person =", person)
        print("current_status =", current_status)
        print("last_status =", last_status)
        print("unsafe_counter =", unsafe_counter)
        print("safe_counter =", safe_counter)

        # =====================================
        # Temporal Filtering
        # =====================================

        if current_status == "UNSAFE":

            unsafe_counter += 1
            safe_counter = 0

            if unsafe_counter >= MIN_UNSAFE_FRAMES:
                status = "UNSAFE"
            else:
                status = "UNSAFE"

        elif current_status == "SAFE":

            safe_counter += 1
            unsafe_counter = 0

            if safe_counter >= MIN_SAFE_FRAMES:
                status = "SAFE"
            else:
                status = "SAFE"

        else:

            status = "NO PERSON"

            unsafe_counter = 0
            safe_counter = 0

    # =====================================
    # Draw Detection
    # =====================================

    output = result.plot()

    # =====================================
    # Draw Employee Names
    # =====================================

    for person_data in person_boxes:

        px1, py1, px2, py2 = person_data["box"]

        employee_name = person_data["name"]

        cv2.putText(
            output,
            employee_name,
            (px1, py1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

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

        print("Employee IDs:", employee_ids)
        print("Employee Names:", employee_names)
        print("Departments:", departments)

        save_detection(

            image=filename,

            result=filename,

            persons=person,

            hardhat=hardhat,

            no_hardhat=workers_without_helmet,

            vest=vest,

            no_vest=workers_without_vest,

            status=status,

            employee_id=", ".join(employee_ids),

            employee_name=", ".join(employee_names),

            department=", ".join(departments)

        )

        last_save_time = current_time

    # =====================================
    # Update Last Status
    # =====================================

    last_status = status

    encode_start = time.time()

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
    # Build Voice Message
    # =====================================

    if len(voice_messages) > 0:
        voice_message = " Warning! ".join(voice_messages)
        voice_message = "Warning! " + voice_message
    else:
        voice_message = ""
    
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

    "violations": violation_count,

    "voice": voice_message

    })
# ==========================================
# Prediction
# ==========================================

@app.route("/predict", methods=["POST"])
def predict():

    global last_employee_name, last_seen_time
    # ----------------------------------
    # Validate Upload
    # ----------------------------------
    if "image" not in request.files:
        return "No image uploaded."

    file = request.files["image"]

    if file.filename == "":
        return "No file selected."

    # ----------------------------------
    # Save Uploaded Image
    # ----------------------------------

    filename = secure_filename(file.filename)
    extension = os.path.splitext(filename)[1]

    unique_name = f"{uuid.uuid4().hex}{extension}"

    upload_path = os.path.join(UPLOAD_FOLDER, unique_name)
    result_path = os.path.join(RESULT_FOLDER, unique_name)

    file.save(upload_path)

    image = cv2.imread(upload_path)

    if image is None:
        return "Invalid Image"

    image = cv2.resize(
        image,
        (FRAME_WIDTH, FRAME_HEIGHT)
    )

    # ----------------------------------
    # YOLO Detection
    # ----------------------------------

    results = detector.detect(image)

    result = results[0]

    names = result.names
    boxes = result.boxes

    person = 0
    hardhat = 0
    vest = 0
    no_hardhat = 0
    no_vest = 0

    person_boxes = []
    helmet_boxes = []
    vest_boxes = []

    print("=================================")
    print("Total Detections :", len(boxes))

    # ----------------------------------
    # Read Detection
    # ----------------------------------

    for box in boxes:

        confidence = float(box.conf[0])
        cls = int(box.cls[0])

        label = names[cls]

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        if (x2 - x1) < 25 or (y2 - y1) < 25:
            continue

        employee_name = "Unknown"

        # --------------------------
        # Face Recognition
        # --------------------------
        if label == "Person" and confidence >= 0.25:

            head_y2 = y1 + int((y2 - y1) * 0.50)

            face_crop = image[y1:head_y2, x1:x2]

            employee_name = "Unknown"

            if face_crop.size != 0:

                try:

                    employee_name = recognizer.recognize(face_crop)

                    if employee_name is None:
                        employee_name = "Unknown"

                except Exception as e:

                    print("Recognition Error:", e)
                    employee_name = "Unknown"

            # -----------------------------
            # Identity Memory
            # -----------------------------

            if employee_name != "Unknown":

                last_employee_name = employee_name
                last_seen_time = time.time()

            else:

                if last_seen_time and time.time() - last_seen_time < IDENTITY_MEMORY_SECONDS:

                    employee_name = last_employee_name

                else:

                    employee_name = "Unidentified Worker"

            print("Recognized:", employee_name)

            if confidence >= 0.25:

                person += 1

                person_boxes.append({

                    "box": (x1, y1, x2, y2),

                    "name": employee_name,

                    "employee_id": "NA",

                    "department": "NA"
                })

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

    # ----------------------------------
    # Draw Detection
    # ----------------------------------

    annotated = result.plot()

    for person_data in person_boxes:

        px1, py1, px2, py2 = person_data["box"]

        cv2.putText(

            annotated,

            person_data["name"],

            (px1, py1 - 10),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.7,

            (0,255,0),

            2

        )

    cv2.imwrite(result_path, annotated)

    # ----------------------------------
    # Status
    # ----------------------------------

    if person == 0:

        status = "NO PERSON"

    elif no_hardhat > 0 or no_vest > 0:

        status = "UNSAFE"

    else:

        status = "SAFE"

    # ----------------------------------
    # Save Detection
    # ----------------------------------

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

        "Detection ID",

        "Employee ID",

        "Employee Name",

        "Department",

        "Status",

        "Persons",

        "Hardhat",

        "No Hardhat",

        "Vest",

        "No Vest",

        "Date"

    ])

    print("First Detection Row:")
    print(detections[0])

    for row in detections:

        sheet.append([

            row[0],   # Detection ID

            row[10],  # Employee ID

            row[11],  # Employee Name

            row[12],  # Department

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

    # ==========================================
    # Delete Result Images
    # ==========================================

    for file in glob.glob(os.path.join(RESULT_FOLDER, "*")):

        try:
            if os.path.isfile(file):
                os.remove(file)
        except Exception as e:
            print("Error deleting result file:", e)

    # ==========================================
    # Delete Violation Images
    # ==========================================

    for file in glob.glob(os.path.join(VIOLATION_FOLDER, "*")):

        try:
            if os.path.isfile(file):
                os.remove(file)
        except Exception as e:
            print("Error deleting violation file:", e)

    # ==========================================
    # Delete Uploaded Images
    # ==========================================

    for file in glob.glob(os.path.join(UPLOAD_FOLDER, "*")):

        try:
            if os.path.isfile(file):
                os.remove(file)
        except Exception as e:
            print("Error deleting uploaded file:", e)

    # ==========================================
    # Delete Generated Reports
    # ==========================================

    for file in glob.glob(os.path.join(REPORT_FOLDER, "*")):

        try:
            if os.path.isfile(file):
                os.remove(file)
        except Exception as e:
            print("Error deleting report file:", e)

    # ==========================================
    # Clear Detection Database
    # ==========================================

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("DELETE FROM detections")

    # Reset Detection ID numbering
    cursor.execute(
        "DELETE FROM sqlite_sequence WHERE name='detections'"
    )

    connection.commit()

    connection.close()

    # ==========================================
    # Return to Admin Panel
    # ==========================================

    return redirect(url_for("admin"))
# ==========================================
# Logout
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/employee_registration")
def employee_registration():

    return render_template(

        "employee_registration.html"

    )

@app.route("/delete_employee/<int:employee_id>")
def delete_employee(employee_id):

    delete_employee_db(employee_id)

    recognizer.load_database()

    return redirect(url_for("employee_management"))

@app.route("/employee_faces/<path:filename>")
def employee_face(filename):

    import os

    folder = os.path.abspath("employee_faces")
    file_path = os.path.join(folder, filename)

    print("Serving:", file_path)
    print("Exists:", os.path.exists(file_path))

    return send_from_directory(folder, filename)
# ==========================================
# Run Flask Application
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
