import asyncio
import json
import time
from datetime import datetime
import cv2
from ultralytics import YOLO
import websockets
import random  # Naya module real-time GPS simulation ke liye

# YAHAN SE MODEL BADLO (Pothole ke liye "pothole_model.pt", Traffic Light ke liye "yolov8n.pt")
ACTIVE_MODEL = "pothole_model.pt"  
model = YOLO(ACTIVE_MODEL)

# TERA PHONE CAMERA IP
PHONE_IP_URL = "http://192.0.0.4:8080/video"

# Starting GPS Location (Isko apne hisaab se change kar sakta hai)
CURRENT_LAT = 18.459329
CURRENT_LNG = 73.849233

async def send_detections(websocket):
    global CURRENT_LAT, CURRENT_LNG
    cap = cv2.VideoCapture(PHONE_IP_URL, cv2.CAP_ANY)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("❌ Error: Phone Camera connect nahi ho raha! - detect and send.py:28")
        return

    print(f"🚀 AI ACTIVE! Model: {ACTIVE_MODEL} - detect and send.py:31")
    last_sent_time = 0
    frame_skip_counter = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            continue
        frame_skip_counter += 1
        if frame_skip_counter % 10 != 0:
            continue
        frame = cv2.resize(frame, (640, 480))
        results = model(frame, conf=0.15, imgsz=320, verbose=False)

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                raw_class_name = model.names[class_id].lower()
                confidence = float(box.conf[0]) * 100

                hazard_label = None

                # --- STRICT MODULAR LOGIC ---
                if ACTIVE_MODEL == "pothole_model.pt":
                    # Agar pothole model hai, toh sab kuch Pothole hi hoga
                    hazard_label = "Potholes"
                
                elif ACTIVE_MODEL == "yolov8n.pt":
                    # Agar default model hai, toh sirf traffic light pakdo
                    if "traffic light" in raw_class_name:
                        hazard_label = "Damaged Traffic Signal"

                # Agar kuch match nahi hua toh ignore karo
                if hazard_label is None:
                    continue

                # 3 Second Rate Limiting
                current_time = time.time()
                if current_time - last_sent_time > 0.5:
                    
                    # 📍 GPS SIMULATOR: Har detection par location thodi aage badha do (Moving Vehicle Effect)
                    CURRENT_LAT += random.uniform(0.0010, 0.0030)
                    CURRENT_LNG += random.uniform(0.0010, 0.0030)
                    
                    payload = {
                        "type": "pothole_detection",
                        "hazard_type": hazard_label,
                        "confidence": round(confidence, 1),
                        "location": {
                            "lat": round(CURRENT_LAT, 6),
                            "lng": round(CURRENT_LNG, 6),
                        },
                        "bus_id": "SMART-VAN-01",
                        "timestamp": datetime.now().strftime("%I:%M:%S %p"),
                    }

                    await websocket.send(json.dumps(payload))
                    print(f"🚨 {hazard_label} Detect Hua! New Location: {CURRENT_LAT:.5f}, {CURRENT_LNG:.5f} - detect and send.py:88")
                    last_sent_time = current_time

        cv2.imshow("Smart City Live", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        await asyncio.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()

async def main():
    uri = "ws://localhost:8000/ws/live-stream"
    try:
        async with websockets.connect(uri) as websocket:
            print("🔗 Connected to Command Center Dashboard! - detect and send.py:104")
            await send_detections(websocket)
    except Exception as e:
        print(f"❌ Connection Error: {e}. Pehle 'py main.py' chalao! - detect and send.py:107")

if __name__ == "__main__":
    asyncio.run(main())