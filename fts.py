from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import threading
import logging
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('FTS')

# Rate limiting setup
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(app=app, key_func=get_remote_address)

class FacultyData:
    def __init__(self):
        self.locations = {}
        self.rfid_readers = {
            "reader_1": [9.21082, 76.63905, "Block A"],
            "reader_2": [9.21065, 76.63860, "Block B"],
            "reader_3": [9.21045, 76.63820, "Block C"],
            "reader_4": [9.21030, 76.63785, "Block D"]
        }
        # Store plain-text passwords (for internal use only)
        self.users = {
            "admin": "admin123",
            "faculty": "faculty123"
        }
        self.faculty_db = {
            "PP": {
                "name": "Pavitha PP",
                "dept": "Computer Science & AIML",
                "contact": "+91 98765 43210",
                "email": "pavitha@sbce.edu.in",
                "block": "C Block",
                "rfid_tag": "PP123456"
            },
            "SS": {
                "name": "Sabi S",
                "dept": "Electrical & Electronics",
                "contact": "+91 87654 32109",
                "email": "sabi@sbce.edu.in",
                "block": "B Block",
                "rfid_tag": "SS654321"
            },
            "SN": {
                "name": "Saritha NR",
                "dept": "Mechanical Engineering",
                "contact": "+91 76543 21098",
                "email": "saritha@sbce.edu.in",
                "block": "D Block",
                "rfid_tag": "SN789012"
            }
        }
        self.lock = threading.Lock()

    def authenticate(self, username, password):
        return self.users.get(username) == password

    def update_location(self, device_id, lat, lng, source):
        with self.lock:
            self.locations[device_id] = {
                "lat": lat,
                "lng": lng,
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "status": "active",
                "name": self.faculty_db.get(device_id, {}).get("name", "Unknown")
            }

    def get_locations(self):
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=5)
            for device_id, loc in self.locations.items():
                if datetime.fromisoformat(loc["timestamp"]) < cutoff:
                    loc["status"] = "inactive"
            return self.locations

    def get_rfid_locations(self):
        return {k: v[:2] for k, v in self.rfid_readers.items()}

    def get_faculty_by_rfid(self, rfid_tag):
        for faculty_id, data in self.faculty_db.items():
            if data.get("rfid_tag") == rfid_tag:
                return faculty_id
        return None

data_store = FacultyData()

def cleanup_task():
    while True:
        try:
            cutoff = datetime.now() - timedelta(hours=24)
            with data_store.lock:
                to_delete = [k for k, v in data_store.locations.items() 
                            if datetime.fromisoformat(v["timestamp"]) < cutoff]
                for k in to_delete:
                    del data_store.locations[k]
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
        threading.Event().wait(3600)

threading.Thread(target=cleanup_task, daemon=True).start()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if data_store.authenticate(username, password):
            session['username'] = username
            session.permanent = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/update', methods=['POST'])
@limiter.limit("10 per minute")
def update_location():
    try:
        data = request.get_json()
        if not data or 'device_id' not in data or 'source' not in data:
            return jsonify({"error": "Invalid data"}), 400

        device_id = data['device_id']
        source = data['source']
        
        if source == 'gps':
            lat = data.get('lat')
            lng = data.get('lng')
            if None in (lat, lng):
                return jsonify({"error": "Missing coordinates"}), 400
            data_store.update_location(device_id, lat, lng, 'gps')
        
        elif source == 'rfid':
            reader_id = data.get('reader_id')
            rfid_tag = data.get('rfid_tag')
            if not rfid_tag:
                return jsonify({"error": "Missing RFID tag"}), 400
                
            faculty_id = data_store.get_faculty_by_rfid(rfid_tag)
            if not faculty_id:
                return jsonify({"error": "Unknown RFID tag"}), 404
                
            if reader_id not in data_store.rfid_readers:
                return jsonify({"error": "Invalid RFID reader"}), 400
                
            lat, lng, _ = data_store.rfid_readers[reader_id]
            data_store.update_location(faculty_id, lat, lng, f'rfid@{reader_id}')
        
        return jsonify({"status": "success"})
    
    except Exception as e:
        logger.error(f"Update error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/locations')
@login_required
def get_locations():
    try:
        return jsonify(data_store.get_locations())
    except Exception as e:
        logger.error(f"Location error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rfid_locations')
@login_required
def get_rfid_locations():
    return jsonify(data_store.get_rfid_locations())

@app.route('/api/faculty')
@login_required
def get_faculty():
    return jsonify(data_store.faculty_db)


@app.route('/api/add_faculty', methods=['POST'])
@login_required
def add_faculty():
    data = request.get_json()
    faculty_id = data.get('id')
    if not faculty_id:
        return jsonify({"error": "Missing ID"}), 400
    if faculty_id in data_store.faculty_db:
        return jsonify({"error": "Faculty ID already exists"}), 409

    data_store.faculty_db[faculty_id] = {
        "name": data.get("name"),
        "dept": data.get("dept"),
        "contact": data.get("contact"),
        "email": data.get("email"),
        "block": data.get("block"),
        "rfid_tag": None  # Can be added later
    }
    return jsonify({"status": "success"}), 200


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, )
