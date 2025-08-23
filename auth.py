import threading
import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
)

# My imports
from extensions import db, send_password_reset_email
from models import User, OTP

router = Blueprint("auth", __name__, url_prefix="/auth")


# --- ROUTES ---
@router.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"msg": "Username, email and password are required"}), 400
    
    if not User.validate_email(email):
        return jsonify({"msg": "Invalid email address"}), 400

    if User.check_email_exists(email):
        return jsonify({"msg": "User already exists"}), 400

    # Create new user
    new_user = User(
        username=username,
        email=email
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "User registered successfully"}), 201


@router.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid username or password"}), 401

    # Create JWT with expiry
    expires = datetime.timedelta(hours=48)
    access_token = create_access_token(
        identity=f"{user.id}", expires_delta=expires)
    return jsonify({
        "msg": "Logged in successfully",
        "access_token": access_token
    }), 200


@router.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(email=email).first()
    if not user:
        # If email does not exist, we still send 200 OK for security purposes.
        # We don't want people revealing emails registered to our platform
        # using this route
        return jsonify({"msg": "Password reset OTP sent to your email"}), 200

    # Create One-Time-Password (expires in 15 mins)
    new_otp = OTP(
        email=email,
        otp=OTP.generate_otp(),
        expiry_time=datetime.datetime.now() + datetime.timedelta(minutes=15)
    )
    db.session.add(new_otp)
    db.session.commit()

    # Send reset token to users email
    threading.Thread(
        target=send_password_reset_email,
        args=(user.username, email, new_otp.otp,)
    ).start()

    return jsonify({
        "msg": "Password reset OTP sent to your email"
    }), 200


@router.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")
    confirm_new_password = data.get("confirm_new_password")

    if new_password != confirm_new_password:
        return jsonify({"msg": "New Password and Confirm New Password do NOT match"}), 400

    # Find valid OTP
    otp_record: OTP | None = OTP.query.filter(
        OTP.email == email,
        OTP.otp == otp,
        OTP.expiry_time > datetime.datetime.now(),
        OTP.is_used == False
    ).first()

    if otp_record is None:
        return jsonify({"msg": "Invalid or expired OTP"}), 400

    # Find user
    user = User.query.filter_by(email=email).first()
    if user is None:
        return jsonify({"msg": "No account found with this email"}), 400

    # Change user's password
    user.set_password(new_password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"msg": "Password reset successfully"}), 200


@router.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user is None:
        message = "User not found"
    else:
        message = f"Logged in as {user.username}"

    return jsonify({
        "msg": message
    }), 200
