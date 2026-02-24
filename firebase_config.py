import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

def get_db():
    """Initializes and returns a Firestore client."""
    print("🔍 Diagnostic: Starting Firestore initialization...")
    service_account_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    
    try:
        if not firebase_admin._apps:
            if service_account_json:
                print("🔍 Diagnostic: FIREBASE_SERVICE_ACCOUNT_JSON found in environment.")
                cred_dict = json.loads(service_account_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("✅ Connected to Firestore successfully!")
            else:
                print("🔍 Diagnostic: FIREBASE_SERVICE_ACCOUNT_JSON not found. Checking local key...")
                # Fallback for local development if serviceAccountKey.json exists
                if os.path.exists("serviceAccountKey.json"):
                    cred = credentials.Certificate("serviceAccountKey.json")
                    firebase_admin.initialize_app(cred)
                    print("✅ Connected to Firestore via local key!")
                else:
                    print("❌ Firebase credentials not found.")
                    return None
        return firestore.client()
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return None

db = get_db()
