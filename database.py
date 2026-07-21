import sqlite3
from datetime import datetime

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME")
# ==========================================
# Create Database
# ==========================================

def create_database():
    
    import os
    print("Database path:", os.path.abspath(DATABASE_NAME))

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    # ==========================================
    # Detection Table
    # ==========================================

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS detections(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            image TEXT,

            result TEXT,

            persons INTEGER,

            hardhat INTEGER,

            no_hardhat INTEGER,

            vest INTEGER,

            no_vest INTEGER,

            status TEXT,

            datetime TEXT

        )

    """)

    # ==========================================
    # Settings Table
    # ==========================================

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS settings(

      id INTEGER PRIMARY KEY,

      alert_email TEXT,

      admin_username TEXT,

      admin_password TEXT

    )

    """)

    # ==========================================
    # Default Email
    # ==========================================

    cursor.execute("""

    INSERT OR IGNORE INTO settings(

    id,
    alert_email,
    admin_username,
    admin_password

    )

    VALUES(

    1,
    'your_email@gmail.com',
    'admin',
    'admin123'

    )

    """)

    connection.commit()

    connection.close()

# ==========================================
# Save Detection
# ==========================================

def save_detection(

    image,
    result,
    persons,
    hardhat,
    no_hardhat,
    vest,
    no_vest,
    status

):

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""

        INSERT INTO detections(

            image,
            result,
            persons,
            hardhat,
            no_hardhat,
            vest,
            no_vest,
            status,
            datetime

        )

        VALUES(?,?,?,?,?,?,?,?,?)

    """, (

        image,
        result,
        persons,
        hardhat,
        no_hardhat,
        vest,
        no_vest,
        status,
        current_time

    ))

    connection.commit()

    connection.close()

# ==========================================
# Get All Detections
# ==========================================

def get_all_detections():

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""

        SELECT *

        FROM detections

        ORDER BY id DESC

    """)

    rows = cursor.fetchall()

    connection.close()

    return rows

def get_dashboard_data():

    import sqlite3

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    # Total detections
    cursor.execute("SELECT COUNT(*) FROM detections")
    total = cursor.fetchone()[0]

    # Safe detections
    cursor.execute("SELECT COUNT(*) FROM detections WHERE status='SAFE'")
    safe = cursor.fetchone()[0]

    # Unsafe detections
    cursor.execute("SELECT COUNT(*) FROM detections WHERE status='UNSAFE'")
    unsafe = cursor.fetchone()[0]

    # Total persons
    cursor.execute("SELECT SUM(persons) FROM detections")
    persons = cursor.fetchone()[0]

    if persons is None:
        persons = 0

    # Helmet violations
    cursor.execute("SELECT SUM(no_hardhat) FROM detections")
    helmet = cursor.fetchone()[0]

    if helmet is None:
        helmet = 0

    # Vest violations
    cursor.execute("SELECT SUM(no_vest) FROM detections")
    vest = cursor.fetchone()[0]

    if vest is None:
        vest = 0

    connection.close()

    return {
        "total": total,
        "safe": safe,
        "unsafe": unsafe,
        "persons": persons,
        "helmet": helmet,
        "vest": vest
    }

def get_chart_data():

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    # ---------------------------------
    # Total detections
    # ---------------------------------

    cursor.execute("SELECT COUNT(*) FROM detections")
    total = cursor.fetchone()[0]

    # ---------------------------------
    # SAFE detections
    # ---------------------------------

    cursor.execute("SELECT COUNT(*) FROM detections WHERE status='SAFE'")
    safe = cursor.fetchone()[0]

    # ---------------------------------
    # UNSAFE detections
    # ---------------------------------

    cursor.execute("SELECT COUNT(*) FROM detections WHERE status='UNSAFE'")
    unsafe = cursor.fetchone()[0]

    # ---------------------------------
    # Total persons
    # ---------------------------------

    cursor.execute("SELECT SUM(persons) FROM detections")
    persons = cursor.fetchone()[0]

    if persons is None:
        persons = 0

    # ---------------------------------
    # Helmet violations
    # ---------------------------------

    cursor.execute("SELECT SUM(no_hardhat) FROM detections")
    helmet = cursor.fetchone()[0]

    if helmet is None:
        helmet = 0

    # ---------------------------------
    # Vest violations
    # ---------------------------------

    cursor.execute("SELECT SUM(no_vest) FROM detections")
    vest = cursor.fetchone()[0]

    if vest is None:
        vest = 0

    connection.close()

    return {

        "total": total,

        "persons": persons,

        "safe": safe,

        "unsafe": unsafe,

        "helmet": helmet,

        "vest": vest

    }

def get_detection_by_id(detection_id):

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""

        SELECT *

        FROM detections

        WHERE id=?

    """,(detection_id,))

    data = cursor.fetchone()

    connection.close()

    return data

def delete_detection(detection_id):

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM detections WHERE id=?",
        (detection_id,)
    )

    connection.commit()

    connection.close()

# ==========================================
# Get Alert Email
# ==========================================

def get_alert_email():

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""

        SELECT alert_email

        FROM settings

        WHERE id=1

    """)

    row = cursor.fetchone()

    connection.close()

    if row:

        return row[0]

    return ""


# ==========================================
# Update Alert Email
# ==========================================

def update_alert_email(email):

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""

        UPDATE settings

        SET alert_email=?

        WHERE id=1

    """, (email,))

    connection.commit()

    connection.close()

# ==========================================
# Get Admin Credentials
# ==========================================

def get_admin_credentials():

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""

        SELECT admin_username, admin_password

        FROM settings

        WHERE id=1

    """)

    row = cursor.fetchone()

    connection.close()

    if row:

        return row

    return ("admin", "admin123")


# ==========================================
# Update Admin Credentials
# ==========================================

def update_admin_credentials(username, password):

    connection = sqlite3.connect(DATABASE_NAME)

    cursor = connection.cursor()

    cursor.execute("""

        UPDATE settings

        SET admin_username=?,
            admin_password=?

        WHERE id=1

    """, (

        username,
        password

    ))

    connection.commit()

    connection.close()