from flask import Blueprint, request, jsonify
from firebase_config import db
from middleware import token_required
from utils import calculate_distance
import datetime

hospitals_bp = Blueprint('hospitals', __name__)

AVERAGE_DELIVERY_SPEED_KMH = 50 

@hospitals_bp.route("/hospital/supply", methods=["POST"])
@token_required
def hospital_supply():
    data = request.get_json()
    request_id = data.get("request_id")
    available_quantity = int(data.get("available_quantity", 0))
    hospital_id = request.hospital_id
    
    if not request_id or available_quantity <= 0:
        return jsonify({"message": "Missing required fields"}), 400

    req_doc = db.collection("BloodRequests").document(request_id).get()
    if not req_doc.exists:
        return jsonify({"message": "Request not found"}), 404
    
    req_data = req_doc.to_dict()
    if req_data['status'] != 'open':
        return jsonify({"message": "Request is no longer open"}), 400

    # Get info of requesting hospital
    requesting_hospital_id = req_data['hospital_id']
    req_h_doc = db.collection("Hospitals").document(requesting_hospital_id).get()
    supplying_h_doc = db.collection("Hospitals").document(hospital_id).get()
    
    if not req_h_doc.exists or not supplying_h_doc.exists:
        return jsonify({"message": "Hospital data mismatch"}), 404
    
    req_h_data = req_h_doc.to_dict()
    supplying_h_data = supplying_h_doc.to_dict()
    
    # Calculate delivery time
    dist = calculate_distance(
        float(req_h_data['latitude']), float(req_h_data['longitude']),
        float(supplying_h_data['latitude']), float(supplying_h_data['longitude'])
    )
    delivery_time_mins = (dist / AVERAGE_DELIVERY_SPEED_KMH) * 60

    # Business Logic: Check if within requested time
    if delivery_time_mins > int(req_data['required_time_minutes']):
         return jsonify({"message": "Delivery time exceeds requirements", "estimated_mins": round(delivery_time_mins, 1)}), 400
    
    new_confirmed = req_data.get('quantity_confirmed', 0) + available_quantity
    status = "fulfilled" if new_confirmed >= int(req_data['quantity_required']) else "open"
    
    db.collection("BloodRequests").document(request_id).update({
        "quantity_confirmed": new_confirmed,
        "status": status,
        "supplied_by_hospital": hospital_id if status == "fulfilled" else None
    })
    
    # Audit Log
    db.collection("AuditLogs").add({
        "action": "HOSPITAL_SUPPLY_SUCCESS",
        "hospital_id": hospital_id,
        "request_id": request_id,
        "quantity": available_quantity,
        "estimated_arrival": round(delivery_time_mins, 1),
        "timestamp": str(datetime.datetime.now())
    })

    return jsonify({
        "status": "success", 
        "new_confirmed": new_confirmed, 
        "status": status,
        "estimated_arrival_mins": round(delivery_time_mins, 1)
    })

@hospitals_bp.route("/dashboard/summary", methods=["GET"])
@token_required
def dashboard_summary():
    hospital_id = request.hospital_id
    
    # 1. Active Requests Count
    active_reqs = db.collection("BloodRequests")\
                   .where("hospital_id", "==", hospital_id)\
                   .where("status", "==", "open").get()
    
    # 2. Fulfilled Today (Client-side filter to avoid composite index error)
    today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    fulfilled_docs = db.collection("BloodRequests")\
                        .where("hospital_id", "==", hospital_id)\
                        .where("status", "==", "fulfilled").stream()
    
    fulfilled_today_count = 0
    for doc in fulfilled_docs:
        d = doc.to_dict()
        if 'fulfilled_at' in d:
            try:
                # Assuming fulfilled_at is a string from datetime.datetime.now()
                f_time = datetime.datetime.fromisoformat(d['fulfilled_at'])
                if f_time >= today_start:
                    fulfilled_today_count += 1
            except:
                pass

    # 3. Nearby Blood Bank Hospitals
    # Get current hospital location
    h_doc = db.collection("Hospitals").document(hospital_id).get()
    h_data = h_doc.to_dict()
    h_lat = float(h_data['latitude'])
    h_lon = float(h_data['longitude'])
    
    nearby_hospitals = 0
    all_hospitals = db.collection("Hospitals").where("has_blood_bank", "==", True).stream()
    for h in all_hospitals:
        if h.id == hospital_id: continue
        data = h.to_dict()
        dist = calculate_distance(h_lat, h_lon, float(data['latitude']), float(data['longitude']))
        if dist <= 20: # 20km radius for neighboring hospitals
            nearby_hospitals += 1

    # 4. Donors Available Within Radius (Default 10km)
    nearby_donors = 0
    all_donors = db.collection("DonorLocation").stream()
    for d in all_donors:
        data = d.to_dict()
        dist = calculate_distance(h_lat, h_lon, float(data.get('lat', 0)), float(data.get('lon', 0)))
        if dist <= 10:
            nearby_donors += 1

    return jsonify({
        "active_requests": len(active_reqs),
        "fulfilled_today": fulfilled_today_count,
        "nearby_blood_banks": nearby_hospitals,
        "nearby_donors": nearby_donors,
        "avg_response_time": "12 mins" # Placeholder for now
    })
