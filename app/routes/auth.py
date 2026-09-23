import re

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.model import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _request_data():
	return request.get_json(silent=True) or request.form


@auth_bp.post("/register")
def register():
	data = _request_data()
	username = (data.get("username") or "").strip()
	email = (data.get("email") or "").strip().lower()
	password = data.get("password") or ""

	if not username or not email or not password:
		return jsonify(error="username, email, and password are required"), 400
	if not 3 <= len(username) <= 50:
		return jsonify(error="username must be between 3 and 50 characters"), 400
	if len(password) < 8:
		return jsonify(error="password must be at least 8 characters"), 400
	if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
		return jsonify(error="a valid email is required"), 400
	if User.query.filter((User.username == username) | (User.email == email)).first():
		return jsonify(error="username or email already exists"), 409

	user = User(
		username=username,
		email=email,
		password=generate_password_hash(password),
	)
	db.session.add(user)
	db.session.commit()
	session["user_id"] = user.id
	return jsonify(message="registered", user_id=user.id), 201


@auth_bp.post("/login")
def login():
	data = _request_data()
	login_value = (data.get("username") or data.get("email") or "").strip()
	password = data.get("password") or ""
	user = User.query.filter(
		(User.username == login_value) | (User.email == login_value.lower())
	).first()

	if user is None or not check_password_hash(user.password, password):
		return jsonify(error="invalid credentials"), 401

	session["user_id"] = user.id
	return jsonify(message="logged in", user_id=user.id)


@auth_bp.post("/logout")
def logout():
	session.pop("user_id", None)
	return jsonify(message="logged out")
