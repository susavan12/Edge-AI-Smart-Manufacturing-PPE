import yagmail
from database import get_alert_email
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")

if not EMAIL or not PASSWORD:
    raise ValueError("EMAIL or EMAIL_PASSWORD not found in .env")


def send_violation_email(image_path, persons, no_hardhat, no_vest):

    # Get recipient email from database
    receiver_email = get_alert_email()

    yag = yagmail.SMTP(EMAIL, PASSWORD)

    subject = "🚨 PPE Safety Violation"

    body = f"""
PPE Safety Alert

Workers          : {persons}

No Hardhat       : {no_hardhat}

No Safety Vest   : {no_vest}

Status           : UNSAFE

Please check immediately.
"""

    yag.send(
        to=receiver_email,
        subject=subject,
        contents=body,
        attachments=image_path
    )

    yag.close()