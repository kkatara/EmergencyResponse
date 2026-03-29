# EmergencyResponse

## 📌 Project Overview
This project is a simple emergency alert system that includes:

- A **frontend** (HTML/CSS) for creating and viewing emergency alerts.
- A **backend** (Flask + Socket.IO + SQLite) that receives alerts, stores them, and broadcasts updates to connected clients.

The goal is to support a fast, real-time alert workflow with minimal setup.

---

## 🧠 How It Works (Step-by-step)

### 1) Frontend sends an alert
1. A user fills out an alert form in the UI (e.g., `index.html`).
2. The frontend javascript sends a **POST** request to `POST /api/alerts` with the alert data (type, location, description, contact info).

### 2) Backend receives the alert
1. **`Backend/main.py`** receives the request and parses JSON.
2. It validates required fields (`emergencyType`, `location`).
3. It generates a unique alert ID (`generate_id()`).
4. It finds the nearest response units (`find_nearest_units()`).
5. It creates an alert object and:
   - saves it in memory (`db.alerts`)
   - saves it to SQLite (`save_alert_to_db()`)
6. It broadcasts the new alert to any connected clients via Socket.IO (`socketio.emit('new-alert', ...)`).

### 3) Clients receive live updates
- Any client subscribed to a specific alert via WebSocket receives live updates:
  - `new-alert` when an alert is created
  - `alert-cancelled` when an alert is canceled

---

## 🗂️ File/Folder Breakdown

### Frontend (HTML + CSS)
- `index.html` – Main landing page for creating alerts.
- `active-alert.html` – Displays details of a specific active alert.
- `admin.html` – Admin console for viewing status and alerts.
- `emergency-type.html` – A helper page for selecting emergency types.

CSS files (styling each UI page):
- `styles.css`
- `admin.css`
- `active-alert.css`
- `emergency-type.css`

### Backend (Python)
- `Backend/main.py` – The full backend server:
  - Loads environment variables via `python-dotenv`.
  - Uses Flask to expose REST endpoints.
  - Uses Flask-SocketIO to send real-time broadcasts.
  - Uses SQLite (`alerts.db`) for persistent storage.

---

## 🔧 Running the Project Locally

1. Install Python dependencies:
```bash
pip install flask flask-cors flask-socketio python-dotenv
```

2. Run the server:
```bash
python Backend/main.py
```

3. Open `index.html` in a browser (or run a simple local server) and use the UI to create alerts.

> ⚠️ The backend listens on port `3000` by default (configurable via `PORT` environment variable).

---

## 🧩 Key Backend Behaviors (Code Walkthrough)

### 1) Configuration & Setup
- `app = Flask(__name__)` creates the Flask app.
- `CORS(app, resources={r"/api/*": {"origins": "*"}})` enables cross-origin requests for the API.
- `socketio = SocketIO(app, cors_allowed_origins="*")` sets up WebSocket support.

### 2) Database Setup (`init_db()`)
- Creates the `alerts` table if it doesn’t exist.
- Columns include: `id`, `type`, `situation`, `location_lat`, `location_lng`, `status`, `dispatched_units`, `created_at`.

### 3) Alert Lifecycle
- Creating an alert (`/api/alerts`): persists it and emits `new-alert`.
- Fetching an alert (`/api/alerts/<alert_id>`): returns stored details from memory.
- Canceling an alert (`/api/alerts/<alert_id>/cancel`): updates in-memory status and emits `alert-cancelled`.

---

## ✅ Notes & Tips
- **No authentication is implemented**, so this is meant for demo / prototype use.
- Alerts are persisted to `alerts.db` but are also stored in memory for real-time updates.
- If you want to reset the system, delete `alerts.db` and restart the backend.
