import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
)
from extensions import db
from models import User

router = Blueprint("auth", __name__, url_prefix="/auth")


# --- ROUTES ---
@router.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Username, email and password are required"}), 400

    if User.check_email_exists(email):
        return jsonify({"error": "User already exists"}), 400

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
        return jsonify({"error": "Invalid username or password"}), 401

    # Create JWT with expiry
    expires = datetime.timedelta(hours=48)
    access_token = create_access_token(identity=f"{user.id}", expires_delta=expires)
    return jsonify({
        "msg": "Logged in successfully",
        "access_token": access_token
    }), 200


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
