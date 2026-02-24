import jwt
import datetime
import os
from functools import wraps
from flask import request, jsonify

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your_fallback_secret_key_for_dev")

def token_required(f):
    """Decorator to protect routes with JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            # In a real app, you might want to verify if the hospital still exists in DB
            request.hospital_id = data['hospital_id']
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(*args, **kwargs)

    return decorated

def generate_token(hospital_id):
    """Generates a JWT token for a hospital."""
    payload = {
        'hospital_id': hospital_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
