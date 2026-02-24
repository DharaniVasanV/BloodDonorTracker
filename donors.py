from flask import Blueprint, request, jsonify
from firebase_config import db
import datetime

donors_bp = Blueprint('donors', __name__)

@donors_bp.route("/save_info", methods=["POST"])
def save_info():
    try:
        data = request.get_json()
        phone = data.get("phone")
        if not phone:
            return jsonify({"status": "error", "message": "Phone number is required"}), 400

        db.collection("DonorInfo").document(phone).set({
            "fName": data.get("firstName"),
            "lName": data.get("lastName"),
            "fullName": data.get("fullName"),
            "blood_group": data.get("blood_group"), # Added blood group for matching
            "dob": data.get("dob"),
            "gender": data.get("gender"),
            "phone": phone,
            "address": data.get("address")
        })
        return jsonify({"status": "success", "message": "Personal info saved"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@donors_bp.route("/update_location", methods=["POST"])
def update_location():
    data = request.form if request.form else request.get_json(silent=True) or {}
    phone = data.get("phone")
    if not phone:
        return jsonify({"status":"error","message":"Phone number required"}), 400

    try:
        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
    except (TypeError, ValueError):
        return jsonify({"status":"error","message":"Invalid latitude/longitude"}), 400

    try:
        db.collection("DonorLocation").document(phone).set({
            "lat": lat,
            "lon": lon,
            "emergency": data.get("emergency"),
            "timestamp": str(datetime.datetime.now())
        }, merge=True)
        return jsonify({"status":"ok"})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 500

@donors_bp.route("/receive_sms", methods=["POST"])
def receive_sms():
    data = request.get_json()
    phone = data.get("phone") or data.get("sender")
    if not phone:
        return {"status": "error", "message": "Phone number required"}, 400

    try:
        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
    except (TypeError, ValueError):
        return {"status": "error", "message": "Invalid latitude/longitude"}, 400

    try:
        db.collection("DonorLocation").document(phone).set({
            "lat": lat,
            "lon": lon,
            "emergency": data.get("emergency"),
            "last_message": data.get("message"),
            "timestamp": str(datetime.datetime.now())
        }, merge=True)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@donors_bp.route("/latest_data")
def latest_data():
    all_data = {}
    if db:
        try:
            loc_docs = db.collection("DonorLocation").stream()
            for doc in loc_docs:
                loc_data = doc.to_dict()
                phone = doc.id
                
                all_data[phone] = {
                    'name': 'Unknown',
                    'phone': phone,
                    'lat': loc_data.get('lat', 0),
                    'lon': loc_data.get('lon', 0),
                    'emergency': loc_data.get('emergency', False),
                    'timestamp': loc_data.get('timestamp', '')
                }

                try:
                    info_doc = db.collection("DonorInfo").document(phone).get()
                    if info_doc.exists:
                        info_data = info_doc.to_dict()
                        fullname = info_data.get("fullName") or f"{info_data.get('fName', '')} {info_data.get('lName', '')}".strip()
                        if fullname:
                            all_data[phone]['name'] = fullname
                except Exception:
                    pass
            return jsonify(all_data)
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({})
