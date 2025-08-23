import random
from werkzeug.security import generate_password_hash, check_password_hash

# My imports
from extensions import db


# --- User Model ---
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def validate_email(email):
        return email.__contains__("@") and email.__contains__(".com")

    @staticmethod
    def check_email_exists(email):
        """Check if an email is already in use"""
        return User.query.filter_by(email=email).first() is not None

    def __repr__(self):
        return f"<User(username={self.username}, email='xxxxxx', password_hash='{self.password_hash}')>"


class OTP(db.Model):
    __tablename__ = "password_reset_otps"

    id = db.Column(db.Integer, primary_key=True, index=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    otp = db.Column(db.String(5), nullable=False)
    expiry_time = db.Column(db.DateTime(timezone=True), nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        otp = ""
        for _ in range(length):
            # Generate a random number from 1 - 9 (inclusive)
            random_number = random.randint(1, 9)
            otp += f"{random_number}"
        return otp

    def __repr__(self):
        return f"<OTPRecord(email='{self.email}', otp='xxxxx', expiry_time='{self.expiry_time}', is_used='{self.is_used}')>"
