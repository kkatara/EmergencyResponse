
# main.py
# ResQ Emergency Alert System - Flask Backend with SQLite
# SAME LOGIC + DATABASE STORAGE

import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
import uuid
from math import radians, cos, sin, asin, sqrt

load_dotenv()

# ============================================
# CONFIGURATION
# ============================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'resq-secret-key-change-in-production'

# CORS setup
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Socket.IO setup
socketio = SocketIO(app, cors_allowed_origins="*")

# Database file
DB_FILE = 'alerts.db'

# ============================================
# DATABASE SETUP
# ============================================
def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Create alerts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            type TEXT,
            situation TEXT,
            location_lat REAL,
            location_lng REAL,
            contact_name TEXT,
            contact_phone TEXT,
            status TEXT,
            dispatched_units TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# Initialize database on startup
init_db()

# ============================================
# IN-MEMORY DATABASE (Same as before)
# ============================================
class Database:
    def __init__(self):
        self.alerts = {}
        self.units = [
            {"id": "unit-1", "type": "ambulance", "status": "available", "location": {"lat": -1.2521, "lng": 36.7784}},
            {"id": "unit-2", "type": "firefighter", "status": "available", "location": {"lat": -1.2621, "lng": 36.7684}},
            {"id": "unit-3", "type": "police", "status": "available", "location": {"lat": -1.2421, "lng": 36.7884}},
        ]

db = Database()

# ============================================
# HELPER FUNCTIONS (Same as before)
# ============================================
def generate_id():
    """Generate unique alert ID"""
    return str(uuid.uuid4())[:8]

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between coordinates"""
    lon1, lat1, lon2, lat2 = map(radians, [lng1, lat1, lng2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r

def find_nearest_units(lat, lng, count=2):
    """Find nearest available units"""
    available_units = [u for u in db.units if u["status"] == "available"]
    
    nearest = sorted(
        available_units,
        key=lambda u: calculate_distance(
            lat, lng,
            u["location"]["lat"], u["location"]["lng"]
        )
    )[:count]
    
    return nearest

def save_alert_to_db(alert_id, emergency_type, situation, location, status, dispatched_units, created_at):
    """Save alert to SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO alerts 
        (id, type, situation, location_lat, location_lng, status, dispatched_units, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        alert_id,
        emergency_type,
        situation,
        location.get('lat'),
        location.get('lng'),
        status,
        json.dumps(dispatched_units),
        created_at
    ))
    
    conn.commit()
    conn.close()

def get_all_alerts_from_db():
    """Get all alerts from database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('SELECT * FROM alerts ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    alerts = []
    for row in rows:
        alerts.append({
            'id': row[0],
            'type': row[1],
            'situation': row[2],
            'location': {'lat': row[3], 'lng': row[4]},
            'status': row[7],
            'dispatchedUnits': json.loads(row[8]),
            'createdAt': row[9]
        })
    
    return alerts

# ============================================
# WEBSOCKET EVENTS (Same as before)
# ============================================
active_subscriptions = {}

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"📱 Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"📴 Client disconnected: {request.sid}")
    for alert_id in list(active_subscriptions.keys()):
        active_subscriptions[alert_id].discard(request.sid)

@socketio.on('subscribe-alert')
def handle_subscribe(data):
    """Subscribe to alert updates"""
    alert_id = data.get('alertId')
    if alert_id:
        if alert_id not in active_subscriptions:
            active_subscriptions[alert_id] = set()
        active_subscriptions[alert_id].add(request.sid)
        join_room(alert_id)
        print(f"✅ Subscribed to alert: {alert_id}")

@socketio.on('unsubscribe-alert')
def handle_unsubscribe(data):
    """Unsubscribe from alert"""
    alert_id = data.get('alertId')
    if alert_id and alert_id in active_subscriptions:
        active_subscriptions[alert_id].discard(request.sid)
        leave_room(alert_id)
        print(f"❌ Unsubscribed from alert: {alert_id}")

# ============================================
# API ENDPOINTS (Same as before + Database)
# ============================================

@app.route('/', methods=['GET'])
def root():
    """API info"""
    return jsonify({
        "name": "ResQ Emergency Alert API",
        "version": "1.0.0",
        "framework": "Flask",
        "description": "No authentication required!",
        "alerts_created": len(get_all_alerts_from_db()),
        "active_units": sum(1 for u in db.units if u["status"] == "available")
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "alerts_count": len(get_all_alerts_from_db()),
        "units_count": len(db.units)
    })

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """
    Create a new emergency alert
    NO AUTHENTICATION REQUIRED!
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'emergencyType' not in data:
            return jsonify({"error": "Missing emergencyType"}), 400
        
        if 'location' not in data:
            return jsonify({"error": "Missing location"}), 400
        
        alert_id = generate_id()
        now = datetime.utcnow()
        
        # Extract data
        emergency_type = data.get('emergencyType')
        location = data.get('location')
        contact_info = data.get('contactInfo', {"phone": "+1234567890", "name": "User"})
        description = data.get('description', '')
        
        # Find nearest responders
        nearest_units = find_nearest_units(
            location.get('lat'),
            location.get('lng'),
            count=2
        )
        
        dispatch_unit_ids = [u["id"] for u in nearest_units]
        
        # Create alert
        alert = {
            "id": alert_id,
            "type": emergency_type,
            "location": {
                "lat": location.get('lat'),
                "lng": location.get('lng')
            },
            "contactInfo": contact_info,
            "description": description,
            "status": "confirmed",
            "createdAt": now.isoformat(),
            "dispatchedUnits": dispatch_unit_ids
        }
        
        # Save to in-memory (for real-time tracking)
        db.alerts[alert_id] = alert
        
        # Save to database (for persistence)
        save_alert_to_db(alert_id, emergency_type, description, location, "confirmed", dispatch_unit_ids, now.isoformat())
        
        # Broadcast to all connected clients
        socketio.emit('new-alert', {
            "id": alert_id,
            "type": emergency_type,
            "location": location,
            "dispatchedUnits": dispatch_unit_ids
        })
        
        # Print detailed alert info
        print("\n" + "="*70)
        print("🚨 NEW ALERT CREATED")
        print("="*70)
        print(f"Alert ID: {alert_id}")
        print(f"Emergency Type: {emergency_type}")
        print(f"Situation: {description}")
        print(f"Location: Lat {location.get('lat')}, Lng {location.get('lng')}")
        print(f"Dispatched Units: {dispatch_unit_ids}")
        print(f"Status: confirmed")
        print(f"Created At: {now.isoformat()}")
        print("="*70 + "\n")
        
        return jsonify({
            "alertId": alert_id,
            "status": "confirmed",
            "dispatchedUnits": dispatch_unit_ids,
            "confirmationTime": now.isoformat()
        }), 201
        
    except Exception as e:
        print(f"❌ Error creating alert: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts/<alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Get alert details - NO AUTHENTICATION"""
    if alert_id not in db.alerts:
        return jsonify({"error": "Alert not found"}), 404
    
    return jsonify(db.alerts[alert_id])

@app.route('/api/alerts/<alert_id>/cancel', methods=['PATCH'])
def cancel_alert(alert_id):
    """Cancel an alert - NO AUTHENTICATION"""
    if alert_id not in db.alerts:
        return jsonify({"error": "Alert not found"}), 404
    
    db.alerts[alert_id]["status"] = "cancelled"
    db.alerts[alert_id]["cancelledAt"] = datetime.utcnow().isoformat()
    
    # Notify clients
    socketio.emit('alert-cancelled', {"alertId": alert_id})
    
    print(f"❌ Alert cancelled: {alert_id}")
    
    return jsonify({
        "status": "cancelled",
        "cancelledAt": db.alerts[alert_id]["cancelledAt"]
    })

@app.route('/api/alerts/active', methods=['GET'])
def get_active_alerts():
    """Get all active alerts - NO AUTHENTICATION"""
    active = [
        alert for alert in db.alerts.values() 
        if alert["status"] in ["sent", "confirmed"]
    ]
    return jsonify(active)

@app.route('/api/alerts/all', methods=['GET'])
def get_all_alerts():
    """Get all alerts from database"""
    return jsonify(get_all_alerts_from_db())

@app.route('/api/status/system', methods=['GET'])
def get_system_status():
    """Get system status"""
    all_alerts = get_all_alerts_from_db()
    active_alerts = sum(1 for a in all_alerts if a["status"] == "confirmed")
    available_units = sum(1 for u in db.units if u["status"] == "available")
    
    return jsonify({
        "systemStatus": "operational",
        "activeUnitsCount": available_units,
        "activeAlertsCount": active_alerts,
        "averageResponseTime": "3.2 mins",
        "coverage": "24/7",
        "totalAlerts": len(all_alerts)
    })

@app.route('/api/location/verify', methods=['POST'])
def verify_location():
    """Verify user location - NO AUTHENTICATION"""
    try:
        data = request.get_json()
        location = data.get('location', {})
        
        lat = location.get('lat')
        lng = location.get('lng')
        
        if lat < -90 or lat > 90 or lng < -180 or lng > 180:
            return jsonify({"error": "Invalid coordinates"}), 400
        
        return jsonify({
            "verified": True,
            "location": location,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# RUN SERVER
# ============================================
if __name__ == '__main__':
    port = int(os.getenv("PORT", 3000))
    
    print(f"""
╔═══════════════════════════════════════╗
║  🚨 ResQ BACKEND SERVER (FLASK)      ║
╠═══════════════════════════════════════╣
║  URL: http://127.0.0.1:{port}             ║
║  WebSocket: ws://127.0.0.1:{port}         ║
║  Health: http://127.0.0.1:{port}/health   ║
║  Database: alerts.db                  ║
╠═══════════════════════════════════════╣
║  NO AUTHENTICATION REQUIRED           ║
║  Ready to receive alerts!             ║
╚═══════════════════════════════════════╝
    """)
    
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=True
    )
