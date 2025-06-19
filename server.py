from flask import Flask, request, jsonify, render_template, redirect, url_for
import firebase_admin
from firebase_admin import credentials, firestore, auth
import logging
from flask_cors import CORS
import requests
import json  # Add missing import for json

# ---------------------------------------------------
# 1. Firebase Initialization
# ---------------------------------------------------
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# -------------------------------
# Configuration & Logging Setup
# -------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
file_handler = logging.FileHandler("server_output.txt")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Initialize Firebase
if not firebase_admin._apps:
    # Use FIREBASE_CREDENTIALS env var (JSON string) if present (for Render)
    firebase_credentials_json = os.getenv('FIREBASE_CREDENTIALS')
    if firebase_credentials_json:
        logger.info("[DEBUG] FIREBASE_CREDENTIALS loaded successfully.")
        cred_dict = json.loads(firebase_credentials_json)
        cred = credentials.Certificate(cred_dict)
        logger.info(f"[DEBUG] Firebase project ID: {cred_dict.get('project_id')}")
    elif os.getenv('FIREBASE_PRIVATE_KEY'):
        cred_dict = {
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        cred = credentials.Certificate(cred_dict)
        logger.info(f"[DEBUG] Firebase project ID: {cred_dict.get('project_id')}")
    else:
        # Fallback to local JSON file
        logger.warning("[WARNING] FIREBASE_CREDENTIALS not set. Falling back to local JSON file.")
        cred = credentials.Certificate("starlink-48ae3-firebase-adminsdk-fbsvc-c263e8cc3f.json")
        logger.info("[DEBUG] Loaded Firebase credentials from local JSON file.")

    firebase_admin.initialize_app(cred)
    logger.info("[DEBUG] Firebase initialized successfully.")
    db = firestore.client()
    logger.info("[DEBUG] Firestore client initialized successfully.")

# ---------------------------------------------------
# 2. Flask App Setup
# ---------------------------------------------------
app = Flask(__name__, template_folder='templates', static_folder='static')
# NEW: Enable CORS for the entire Flask app
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Template Route Definitions ---
@app.route('/')
def home():
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def registration_page():
    return render_template('RegistrationPage.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/login.html')
def login_html_redirect():
    return redirect(url_for('login_page'))

@app.route('/RegistrationPage.html')
def registration_html_redirect():
    return redirect(url_for('registration_page'))

@app.route('/dashboard.html')
def dashboard_html_redirect():
    return redirect(url_for('dashboard_page'))

# Handle Chrome DevTools requests to prevent 404 errors
@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools():
    return app.send_static_file('.well-known/appspecific/com.chrome.devtools.json')

# ---------------------------------------------------
# 3. Helper Functions
# ---------------------------------------------------
def get_service_line(service_line_number: str) -> dict:
    doc = db.collection('service_lines').document(service_line_number).get()
    data = doc.to_dict()
    logger.info("SERVICE LINE DATA: %s", data)
    return data if doc.exists else None

def get_formatted_address(address_ref_id: str) -> str:
    doc = db.collection('addresses').document(address_ref_id).get()
    if doc.exists:
        return doc.to_dict().get("formattedAddress")
    return None

def get_user_terminal_by_service_line(service_line_number: str) -> dict:
    query = (
        db.collection("user_terminals")
          .where("serviceLineNumber", "==", service_line_number)
          .limit(1)
          .stream()
    )
    for doc in query:
        user_terminal = doc.to_dict()
        router_id = None
        if "routers" in user_terminal and isinstance(user_terminal["routers"], list):
            if len(user_terminal["routers"]) > 0:
                router_id = user_terminal["routers"][0].get("routerId")
        return {
            "kitSerialNumber": user_terminal.get("kitSerialNumber"),
            "userTerminalId": doc.id,
            "dishSerialNumber": user_terminal.get("dishSerialNumber"),
            "routerId": router_id
        }
    return None

# --- Helper Functions for Real Telemetry Data ---
def min_max_last(values):
    """
    Compute min, max, and last from a list of numeric (or semi-numeric) values.
    If no numeric data, returns None, else do standard min/max/last.
    """
    numeric_vals = [v for v in values if isinstance(v, (int, float))]
    if not numeric_vals:
        return {
            "min": None,
            "max": None,
            "last": values[-1] if values else None
        }
    return {
        "min": min(numeric_vals),
        "max": max(numeric_vals),
        "last": numeric_vals[-1]
    }

def get_device_doc_id(device_type: str, device_id: str) -> str:
    if not device_id:
        return ""

    if device_type == "u":
        if not device_id.startswith("ut"):
            return f"ut{device_id}"
        return device_id
    elif device_type == "r":
        if not device_id.startswith("Router-"):
            return f"Router-{device_id}"
        return device_id
    else:
        return device_id

def get_all_telemetry_records(device_type: str, device_id: str) -> dict:
    """
    Fetch all telemetry records for a device from Firebase and return structured data
    """
    doc_id = get_device_doc_id(device_type, device_id)
    if not doc_id:
        return {"allRecords": [], "aggregates": {}}

    records_ref = db.collection("telemetry_raw").document(doc_id).collection("records")
    all_docs = list(records_ref.order_by("UtcTimestampNs").stream())

    # Raw records
    all_records = []
    dish_ping_drop = []
    dish_ping_latency = []
    downlink = []
    uplink = []
    obstruction = []
    ping_drop_avg = []
    ping_latency_avg = []
    run_sw_ver = []
    signal_quality = []

    # router fields:
    internet_drop = []
    internet_lat = []
    wifi_hw_ver = []
    wifi_is_bypassed = []
    wifi_is_repeater = []
    wifi_pop_drop = []
    wifi_pop_lat = []
    wifi_sw_ver = []

    for snap in all_docs:
        data = snap.to_dict()
        all_records.append(data)

        # Fill user-terminal arrays if these fields exist:
        if "DishPingDropRate" in data: 
            dish_ping_drop.append(data["DishPingDropRate"])
        if "DishPingLatencyMs" in data:
            dish_ping_latency.append(data["DishPingLatencyMs"])
        if "DownlinkThroughput" in data:
            downlink.append(data["DownlinkThroughput"])
        if "UplinkThroughput" in data:
            uplink.append(data["UplinkThroughput"])
        if "ObstructionPercentTime" in data:
            obstruction.append(data["ObstructionPercentTime"])
        if "PingDropRateAvg" in data:
            ping_drop_avg.append(data["PingDropRateAvg"])
        if "PingLatencyMsAvg" in data:
            ping_latency_avg.append(data["PingLatencyMsAvg"])
        if "RunningSoftwareVersion" in data:
            run_sw_ver.append(data["RunningSoftwareVersion"])
        if "SignalQuality" in data:
            signal_quality.append(data["SignalQuality"])

        # Fill router arrays if these fields exist:
        if "InternetPingDropRate" in data:
            internet_drop.append(data["InternetPingDropRate"])
        if "InternetPingLatencyMs" in data:
            internet_lat.append(data["InternetPingLatencyMs"])
        if "WifiHardwareVersion" in data:
            wifi_hw_ver.append(data["WifiHardwareVersion"])
        if "WifiIsBypassed" in data:
            wifi_is_bypassed.append(data["WifiIsBypassed"])
        if "WifiIsRepeater" in data:
            wifi_is_repeater.append(data["WifiIsRepeater"])
        if "WifiPopPingDropRate" in data:
            wifi_pop_drop.append(data["WifiPopPingDropRate"])
        if "WifiPopPingLatencyMs" in data:
            wifi_pop_lat.append(data["WifiPopPingLatencyMs"])
        if "WifiSoftwareVersion" in data:
            wifi_sw_ver.append(data["WifiSoftwareVersion"])

    # Aggregates
    aggregates = {
        "DishPingDropRate": min_max_last(dish_ping_drop),
        "DishPingLatencyMs": min_max_last(dish_ping_latency),
        "DownlinkThroughput": min_max_last(downlink),
        "UplinkThroughput": min_max_last(uplink),
        "ObstructionPercentTime": min_max_last(obstruction),
        "PingDropRateAvg": min_max_last(ping_drop_avg),
        "PingLatencyMsAvg": min_max_last(ping_latency_avg),
        "RunningSoftwareVersion": min_max_last(run_sw_ver),
        "SignalQuality": min_max_last(signal_quality),

        "InternetPingDropRate": min_max_last(internet_drop),
        "InternetPingLatencyMs": min_max_last(internet_lat),
        "WifiHardwareVersion": min_max_last(wifi_hw_ver),
        "WifiIsBypassed": min_max_last(wifi_is_bypassed),
        "WifiIsRepeater": min_max_last(wifi_is_repeater),
        "WifiPopPingDropRate": min_max_last(wifi_pop_drop),
        "WifiPopPingLatencyMs": min_max_last(wifi_pop_lat),
        "WifiSoftwareVersion": min_max_last(wifi_sw_ver),
    }

    return {
        "allRecords": all_records,
        "aggregates": aggregates
    }

def get_telemetry_software_version(device_type: str, device_id: str) -> str:
    """
    Get software version for a device from telemetry data
    """
    doc_id = get_device_doc_id(device_type, device_id)
    
    query = db.collection("telemetry") \
            .where("DeviceType", "==", device_type) \
            .where("DeviceId", "==", doc_id) \
            .limit(1)

    for doc_snap in query.stream():
        data = doc_snap.to_dict()
        if device_type == "u":
            return data.get("RunningSoftwareVersion")
        elif device_type == "r":
            return data.get("WifiSoftwareVersion") or data.get("SoftwareVersion")
    return None

# --- Optimized Billing Records Query ---
def get_billing_records_for_service_line(service_line_number):
    """
    Instead of iterating through every account and subcollection,
    we now assume that all billing records are stored in a dedicated collection "billing_records"
    with a field "serviceLineNumber". Ensure you have an index on this field.
    """
    billing_ref = db.collection("billing_records")
    query = billing_ref.where("serviceLineNumber", "==", service_line_number)
    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data["record_id"] = doc.id
        results.append(data)
    return results

# ---------------------------------------------------
# 4. Endpoint to Get Dashboard Data
# ---------------------------------------------------
@app.route('/api/dashboard-data/<service_line_number>', methods=['GET'])
def api_get_dashboard_data(service_line_number):
    logger.info(f"Received API call for service_line_number: {service_line_number}")
    try:
        service_line = get_service_line(service_line_number)
        if not service_line:
            return jsonify({"error": "Service line not found"}), 404

        nickname = service_line.get("nickname")
        address_ref_id = service_line.get("addressReferenceId")
        formatted_address = get_formatted_address(address_ref_id) if address_ref_id else None
        data_usage = get_billing_records_for_service_line(service_line_number)
        user_terminal_doc = get_user_terminal_by_service_line(service_line_number)
        kit_serial = user_terminal_doc.get("kitSerialNumber") if user_terminal_doc else None
        user_terminal_id = user_terminal_doc.get("userTerminalId") if user_terminal_doc else None
        dish_serial = user_terminal_doc.get("dishSerialNumber") if user_terminal_doc else None
        router_id = user_terminal_doc.get("routerId") if user_terminal_doc else None

        user_terminal_sw = get_telemetry_software_version("u", user_terminal_id) if user_terminal_id else None
        router_sw = get_telemetry_software_version("r", router_id) if router_id else None
        if router_sw is None:
            router_sw = "2025.02.12.mr46561"
            
        # Fetch real telemetry data from Firebase
        user_terminal_data = {}
        router_data = {}

        if user_terminal_id:
            logger.info(f"Fetching telemetry data for user terminal: {user_terminal_id}")
            user_terminal_data = get_all_telemetry_records("u", user_terminal_id)

        if router_id:
            logger.info(f"Fetching telemetry data for router: {router_id}")
            router_data = get_all_telemetry_records("r", router_id)

        # Update software versions using real telemetry data
        if user_terminal_sw is None and user_terminal_id:
            user_terminal_sw = get_telemetry_software_version("u", user_terminal_id)

        if router_sw is None and router_id:
            router_sw = get_telemetry_software_version("r", router_id)

        # Prepare response data
        response_data = {
            "nickname": nickname,
            "kitSerialNumber": kit_serial,
            "formattedAddress": formatted_address,
            "dataUsage": data_usage,
            "userTerminalId": user_terminal_id,
            "routerId": router_id,
            "dishSerialNumber": dish_serial,
            "user_terminal_software_version": user_terminal_sw,
            "router_software_version": router_sw,
            "telemetry_data": {
                "userTerminal": user_terminal_data,  # Real telemetry data
                "router": router_data               # Real telemetry data
            }
        }

        logger.info(f"Response Data: {response_data}")
        return jsonify(response_data), 200

    except ValueError as e:
        logger.error("ValueError: %s", e)
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error("Internal server error: %s", e)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# ---------------------------------------------------
# 4B. New Endpoint to Handle Registration
# ---------------------------------------------------
@app.route('/api/register', methods=['POST'])
def api_register():
    """
    Registers a user based on the JSON payload:
      {
        "email": "...",
        "password": "...",
        "serviceLineNumber": "..."
      }
    """
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        service_line_number = data.get('serviceLineNumber')

        if not email or not password or not service_line_number:
            return jsonify({"error": "Missing required fields"}), 400

        logger.info(f"New registration request: email={email}, serviceLineNumber={service_line_number}")

        # Check if user already exists
        try:
            user_record = auth.get_user_by_email(email)
            return jsonify({"error": "User with that email already exists."}), 409
        except auth.UserNotFoundError:
            pass  # User does not exist, proceed

        # Create user in Firebase Auth
        user = auth.create_user(email=email, password=password)

        # Store user info in Firestore
        db.collection('users').document(user.uid).set({
            "email": email,
            "serviceLineNumber": [service_line_number],
            "createdAt": firestore.SERVER_TIMESTAMP
        })

        # Optionally, link user to service line
        sl_ref = db.collection('service_lines').document(service_line_number)
        sl_doc = sl_ref.get()
        if sl_doc.exists:
            sl_ref.update({"users": firestore.ArrayUnion([user.uid])})

        return jsonify({
            "message": "Registration successful",
            "email": email,
            "serviceLineNumber": service_line_number
        }), 201

    except Exception as e:
        logger.error("Registration error: %s", e)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

# ---------------------------------------------------
# 4C. New Endpoint to Handle Login
# ---------------------------------------------------
@app.route('/api/login', methods=['POST'])
def api_login():
    """
    Authenticates a user using Firebase Auth REST API.
    Expects JSON: {"email": ..., "password": ...}
    Returns: {"idToken": ..., "serviceLines": ...}
    """
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            return jsonify({"error": "Missing email or password."}), 400

        # Firebase REST API endpoint for signInWithPassword
        FIREBASE_API_KEY = "AIzaSyC6Kp4Dr2MzFzIa6pNjHDJ0hPMgKim9G4k"  # Replace with your actual API key
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        resp = requests.post(url, json=payload)
        if resp.status_code != 200:
            return jsonify({"error": "Invalid email or password."}), 401
        id_token = resp.json().get("idToken")
        # Fetch user's service lines from Firestore
        user_record = auth.get_user_by_email(email)
        user_doc = db.collection('users').document(user_record.uid).get()
        service_lines = user_doc.to_dict().get("serviceLineNumber", []) if user_doc.exists else []
        return jsonify({"idToken": id_token, "serviceLines": service_lines}), 200
    except Exception as e:
        logger.error("Login error: %s", e)
        return jsonify({"error": "Service unavailable. Please try later."}), 503

# ---------------------------------------------------
# 5. Run the Flask App
# ---------------------------------------------------
if __name__ == '__main__':
    # Get port from environment variable (for cloud hosting) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Get debug setting from environment
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(debug=debug, host='0.0.0.0', port=port)
