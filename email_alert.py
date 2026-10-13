# import yagmail
# from database import get_alert_email
# from dotenv import load_dotenv
# import os

# load_dotenv()

# EMAIL = os.getenv("EMAIL")
# PASSWORD = os.getenv("EMAIL_PASSWORD")

# if not EMAIL or not PASSWORD:
#     raise ValueError("EMAIL or EMAIL_PASSWORD not found in .env")


# def send_violation_email(image_path, persons, no_hardhat, no_vest):

#     # Get recipient email from database
#     receiver_email = get_alert_email()

#     yag = yagmail.SMTP(EMAIL, PASSWORD)

#     subject = "🚨 PPE Safety Violation"

#     body = f"""
# PPE Safety Alert

# Workers          : {persons}

# No Hardhat       : {no_hardhat}

# No Safety Vest   : {no_vest}

# Status           : UNSAFE

# Please check immediately.
# """

#     yag.send(
#         to=receiver_email,
#         subject=subject,
#         contents=body,
#         attachments=image_path
#     )

#     yag.close()

import os
import yagmail
from dotenv import load_dotenv
from database import get_alert_email

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("EMAIL_PASSWORD")


def send_violation_email(image_path, persons, no_hardhat, no_vest):

    # Check sender credentials
    if not EMAIL or not PASSWORD:
        raise ValueError(
            "EMAIL or EMAIL_PASSWORD is missing from .env"
        )

    # Get recipient from database
    receiver_email = get_alert_email()

    if not receiver_email or not receiver_email.strip():
        raise ValueError(
            "Alert recipient email is missing from Email Settings"
        )

    # Check violation image
    if not os.path.isfile(image_path):
        raise FileNotFoundError(
            f"Violation image not found: {image_path}"
        )

    yag = None

    try:
        yag = yagmail.SMTP(EMAIL, PASSWORD)

        subject = "PPE Safety Violation Alert"

        body = f"""
PPE Safety Alert

Workers          : {persons}
No Hardhat       : {no_hardhat}
No Safety Vest   : {no_vest}

Status           : UNSAFE

Please check the safety violation immediately.
"""

        yag.send(
            to=receiver_email.strip(),
            subject=subject,
            contents=body,
            attachments=image_path
        )

        print("Email send request completed successfully.")

    finally:
        if yag is not None:
            yag.close()