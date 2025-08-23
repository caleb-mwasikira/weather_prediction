import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
jwt = JWTManager()


def send_password_reset_email(username: str, email: str, otp: str):
    try:
        load_dotenv()

        sender_email = os.getenv("SMTP_EMAIL")
        # use App Password, not your Gmail password
        app_password = os.getenv("SMTP_PASSWORD")

        subject = "Password Reset Request"
        body = f"""
        Hello {username},

        You requested a password reset on your AgriTech account. Please enter the OTP below:

        {otp}

        This OTP is valid for 15 minutes.

        If you did not request this, please ignore this email.
        """

        dev_mode = os.getenv("DEVELOPMENT")
        if dev_mode is None or dev_mode == "True":
            # App is in DEVELOPMENT; print message to console
            print(body)
            return

        # Build email
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, email, msg.as_string())

    except Exception as e:
        print(f"Error sending email to {email}; {str(e)}")
