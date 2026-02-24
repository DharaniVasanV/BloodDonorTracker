from flask import Blueprint, request, jsonify
import bcrypt
from firebase_config import db
from middleware import generate_token, token_required
import datetime
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/hospital/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("hospital_name")
    
    if not email or not password or not name:
        return jsonify({"message": "Missing required fields"}), 400

    # Check if hospital already exists
    docs = db.collection("Hospitals").where("email", "==", email).limit(1).get()
    if len(docs) > 0:
        return jsonify({"message": "Hospital already registered"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    hospital_id = str(uuid.uuid4())
    hospital_data = {
        "hospital_id": hospital_id,
        "hospital_name": name,
        "email": email,
        "phone": data.get("phone"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "has_blood_bank": data.get("has_blood_bank", False),
        "password_hash": hashed_password,
        "created_at": str(datetime.datetime.now())
    }
    
    db.collection("Hospitals").document(hospital_id).set(hospital_data)
    
    return jsonify({"message": "Hospital registered successfully", "hospital_id": hospital_id}), 201

@auth_bp.route("/hospital/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"message": "Missing email or password"}), 400

    docs = db.collection("Hospitals").where("email", "==", email).limit(1).get()
    if len(docs) == 0:
        return jsonify({"message": "Hospital not found"}), 404
    
    hospital_doc = docs[0]
    hospital_data = hospital_doc.to_dict()
    
    if bcrypt.checkpw(password.encode('utf-8'), hospital_data['password_hash'].encode('utf-8')):
        token = generate_token(hospital_data['hospital_id'])
        return jsonify({"token": token, "hospital_id": hospital_data['hospital_id']})
    
    return jsonify({"message": "Invalid credentials"}), 401

@auth_bp.route("/hospital/profile", methods=["GET"])
@token_required
def profile():
    hospital_id = request.hospital_id
    doc = db.collection("Hospitals").document(hospital_id).get()
    if not doc.exists:
        return jsonify({"message": "Hospital not found"}), 404
        
    hospital_data = doc.to_dict()
    del hospital_data['password_hash'] # Don't send hash
    return jsonify(hospital_data)
