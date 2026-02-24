from flask import Blueprint, request, jsonify
from firebase_config import db
from middleware import token_required
from utils import calculate_distance
import datetime
import uuid

requests_bp = Blueprint('requests', __name__)

AVERAGE_SPEED_KMH = 40 # Standard for urban traffic

@requests_bp.route("/requests/create", methods=["POST"])
@token_required
def create_request():
    data = request.get_json()
    hospital_id = request.hospital_id
    blood_group = data.get("blood_group")
    quantity_required = data.get("quantity_required")
    required_time_minutes = data.get("required_time_minutes")
    critical_level = data.get("critical_level", "normal")
    
    if not blood_group or not quantity_required or not required_time_minutes:
        return jsonify({"message": "Missing required fields"}), 400

    # Calculate radius with critical level multipliers
    multiplier = 1.0
    if critical_level == 'urgent': multiplier = 1.5
    elif critical_level == 'critical': multiplier = 2.0
    
    radius_km = (AVERAGE_SPEED_KMH * (int(required_time_minutes) / 60)) * multiplier
    
    # Get hospital location
    hospital_doc = db.collection("Hospitals").document(hospital_id).get()
    if not hospital_doc.exists:
        return jsonify({"message": "Hospital profile not found"}), 404
    
    h_data = hospital_doc.to_dict()
    h_lat = float(h_data.get("latitude"))
    h_lon = float(h_data.get("longitude"))

    # Fetch donors within radius (Simplified: fetching all then filtering for now)
    # Optimized: You'd use GeoFirestore, but here we do business logic filter
    matched_donors = []
    
    # Join DonorLocation with DonorInfo (filtering by blood group)
    # NOTE: Assuming 'blood_group' is stored in DonorInfo or we'll need it there
    # User might need to update DonorInfo schema if it doesn't have blood_group
    donors_info = db.collection("DonorInfo").where("blood_group", "==", blood_group).stream()
    
    for donor in donors_info:
        donor_data = donor.to_dict()
        phone = donor.id
        
        # Get location
        loc_doc = db.collection("DonorLocation").document(phone).get()
        if loc_doc.exists:
            loc_data = loc_doc.to_dict()
            d_lat = float(loc_data.get("lat"))
            d_lon = float(loc_data.get("lon"))
            
            dist = calculate_distance(h_lat, h_lon, d_lat, d_lon)
            if dist <= radius_km:
                matched_donors.append({
                    "phone": phone,
                    "distance_km": round(dist, 2),
                    "name": donor_data.get("fullName", "Donor")
                })

    request_id = str(uuid.uuid4())
    request_data = {
        "request_id": request_id,
        "hospital_id": hospital_id,
        "blood_group": blood_group,
        "quantity_required": quantity_required,
        "quantity_confirmed": 0,
        "required_time_minutes": required_time_minutes,
        "critical_level": critical_level,
        "radius_calculated": round(radius_km, 2),
        "status": "open",
        "created_at": str(datetime.datetime.now()),
        "matched_donors_count": len(matched_donors)
    }
    
    db.collection("BloodRequests").document(request_id).set(request_data)
    
    # Audit Log
    db.collection("AuditLogs").add({
        "action": "REQUEST_CREATED",
        "hospital_id": hospital_id,
        "request_id": request_id,
        "timestamp": str(datetime.datetime.now())
    })

    return jsonify({
        "message": "Blood request created",
        "request_id": request_id,
        "matched_donors": matched_donors
    }), 201

@requests_bp.route("/requests/list", methods=["GET"])
@token_required
def list_requests():
    hospital_id = request.hospital_id
    docs = db.collection("BloodRequests").where("hospital_id", "==", hospital_id).stream()
    requests = []
    for doc in docs:
        d = doc.to_dict()
        requests.append(d)
    
    # Sort by created_at descending (string sort works for ISO-like timestamps)
    requests.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(requests)

@requests_bp.route("/requests/respond", methods=["POST"])
def respond_request():
    data = request.get_json()
    request_id = data.get("request_id")
    phone = data.get("phone")
    action = data.get("action") # 'accept' or 'decline'
    
    if not request_id or not phone or not action:
        return jsonify({"message": "Missing required fields"}), 400

    # Avoid duplicate responses
    existing = db.collection("RequestResponses")\
                 .where("request_id", "==", request_id)\
                 .where("donor_phone", "==", phone).limit(1).get()
    
    if len(existing) > 0:
        return jsonify({"message": "Response already recorded"}), 400

    req_doc = db.collection("BloodRequests").document(request_id).get()
    if not req_doc.exists:
        return jsonify({"message": "Request not found"}), 404
    
    req_data = req_doc.to_dict()
    if req_data['status'] != 'open':
        return jsonify({"message": "Request is no longer open"}), 400

    if action == 'accept':
        # Store response
        db.collection("RequestResponses").add({
            "request_id": request_id,
            "donor_phone": phone,
            "accepted_at": str(datetime.datetime.now())
        })
        
        # Update quantity confirmed
        new_confirmed = req_data.get('quantity_confirmed', 0) + 1
        db.collection("BloodRequests").document(request_id).update({
            "quantity_confirmed": new_confirmed
        })
        
        # Auto fulfillment check
        if new_confirmed >= int(req_data['quantity_required']):
            db.collection("BloodRequests").document(request_id).update({
                "status": "fulfilled",
                "fulfilled_at": str(datetime.datetime.now())
            })
            
            # Audit Log
            db.collection("AuditLogs").add({
                "action": "REQUEST_FULFILLED",
                "request_id": request_id,
                "timestamp": str(datetime.datetime.now())
            })

    return jsonify({"status": "success"})

@requests_bp.route("/requests/<request_id>/donors", methods=["GET"])
@token_required
def list_accepted_donors(request_id):
    docs = db.collection("RequestResponses").where("request_id", "==", request_id).stream()
    accepted = []
    for doc in docs:
        d = doc.to_dict()
        # Fetch donor name from DonorInfo
        donor_info = db.collection("DonorInfo").document(d['donor_phone']).get()
        name = donor_info.to_dict().get('fullName', 'Donor') if donor_info.exists else 'Unknown'
        
        # Get live location for distance calc
        loc_doc = db.collection("DonorLocation").document(d['donor_phone']).get()
        dist_str = "Unknown"
        if loc_doc.exists:
            # We would calc distance here if hospital loc was passed or stored in session
            pass 

        accepted.append({
            "phone": d['donor_phone'],
            "name": name,
            "accepted_at": d['accepted_at'],
            "status": d.get('status', 'on_the_way') # default status
        })
    return jsonify(accepted)

@requests_bp.route("/requests/confirm-arrival", methods=["POST"])
@token_required
def confirm_arrival():
    data = request.get_json()
    request_id = data.get("request_id")
    phone = data.get("phone")
    
    # Update response status
    responses = db.collection("RequestResponses")\
                  .where("request_id", "==", request_id)\
                  .where("donor_phone", "==", phone).limit(1).get()
    
    if len(responses) == 0:
        return jsonify({"message": "Response record not found"}), 404
        
    responses[0].reference.update({"status": "arrived", "arrived_at": str(datetime.datetime.now())})
    
    # Logic to check if we can close the request if enough have arrived?
    # For now, just mark the donor as arrived.
    
    return jsonify({"status": "success", "message": "Donor arrival confirmed"})

@requests_bp.route("/requests/cancel", methods=["POST"])
@token_required
def cancel_request():
    data = request.get_json()
    request_id = data.get("request_id")
    hospital_id = request.hospital_id
    
    req_doc = db.collection("BloodRequests").document(request_id).get()
    if not req_doc.exists:
        return jsonify({"message": "Request not found"}), 404
        
    req_data = req_doc.to_dict()
    if req_data['hospital_id'] != hospital_id:
        return jsonify({"message": "Unauthorized"}), 403
        
    db.collection("BloodRequests").document(request_id).update({
        "status": "cancelled",
        "cancelled_at": str(datetime.datetime.now())
    })
    
    # Audit Log
    db.collection("AuditLogs").add({
        "action": "REQUEST_CANCELLED",
        "hospital_id": hospital_id,
        "request_id": request_id,
        "timestamp": str(datetime.datetime.now())
    })
    
    return jsonify({"status": "success", "message": "Request cancelled"})
