# gps_simulator.py
import time
import random
import requests
from datetime import datetime

# College coordinates (Sree Buddha College of Engineering)
BASE_LAT = 10.3048341
BASE_LON = 76.2994753
DEVICE_ID = "FACULTY_01"
SERVER_URL = "http://localhost:5000/api/update"  # Change to your server URL

def generate_gps_data():
    """Generate realistic GPS coordinates with small variations"""
    # Add random noise (simulate GPS drift)
    lat = BASE_LAT + random.uniform(-0.0002, 0.0002)  # ~20m radius
    lon = BASE_LON + random.uniform(-0.0002, 0.0002)
    
    # Simulate different campus locations
    locations = {
        "main_gate": (10.3048341, 76.2994753),
        "cafeteria": (10.304912, 76.299601),
        "library": (10.304701, 76.299312),
        "cs_block": (10.304945, 76.299188),
        "parking_lot": (10.304567, 76.299744)
    }
    
    # Randomly select a campus location
    selected = random.choice(list(locations.values()))
    lat = selected[0] + random.uniform(-0.00005, 0.00005)
    lon = selected[1] + random.uniform(-0.00005, 0.00005)
    
    return lat, lon

def send_gps_data():
    while True:
        try:
            lat, lon = generate_gps_data()
            
            payload = {
                "device_id": DEVICE_ID,
                "source": "gps",
                "lat": lat,
                "lng": lon
            }
            
            response = requests.post(SERVER_URL, json=payload)
            print(f"[{datetime.now().time()}] Sent: {lat:.6f}, {lon:.6f} | Status: {response.status_code}")
            
            time.sleep(10)  # Send update every 10 seconds
            
        except Exception as e:
            print(f"Error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    print("Starting GPS Simulator for Sree Buddha College...")
    print(f"Base Coordinates: {BASE_LAT:.6f}, {BASE_LON:.6f}")
    send_gps_data()
