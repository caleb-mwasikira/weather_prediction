from werkzeug.security import generate_password_hash, check_password_hash
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

    def check_email(self, email):
        return email.__contains__("@") and email.__contains__(".com")

    @staticmethod
    def check_email_exists(email):
        """Check if an email is already in use"""
        return User.query.filter_by(email=email).first() is not None
