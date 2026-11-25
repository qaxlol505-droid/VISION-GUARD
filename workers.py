import os
import time
import threading
import cv2
import numpy as np
import face_recognition
from ultralytics import YOLO

import state
from config import DEVICE, CONF_PISTOL, CONF_KNIFE, CONF_GENERAL, TARGET_CLASSES, FACE_TOLERANCE
from utils import send_alert_to_server, log_person_access, draw_ui_box

# ==========================================
# 1. CAMERA THREAD
# ==========================================
def camera_worker():
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if ret:
            with state.frame_lock:
                state.shared_frame = frame
        else:
            time.sleep(0.01)

# ==========================================
# 2. YOLO WORKER
# ==========================================
def yolo_worker():
    print("⏳ Loading YOLO Models...")
    gun_model = YOLO('pistol.pt').to(DEVICE)
    obj_model = YOLO('yolov8s.pt').to(DEVICE)
    print("✅ YOLO Models Loaded Successfully!")

    last_logged = {} 
    
    while True:
        try:
            start_time = time.time()
            
            with state.frame_lock:
                if state.shared_frame is None:
                    time.sleep(0.01)
                    continue
                frame_ai = state.shared_frame.copy()
                
            temp_boxes = []
            detected_labels = set()

            pistol_results = gun_model(frame_ai, stream=True, verbose=False, device=DEVICE, conf=CONF_PISTOL, iou=0.45, agnostic_nms=True)
            for r in pistol_results:
                for box in r.boxes:
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    temp_boxes.append((x1, y1, x2, y2, (0, 0, 255), f"PISTOL {conf:.2f}"))
                    detected_labels.add("PISTOL")

            object_results = obj_model(frame_ai, stream=True, verbose=False, device=DEVICE, classes=TARGET_CLASSES, conf=CONF_GENERAL, iou=0.45, agnostic_nms=True)
            for r in object_results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    label = obj_model.names[cls_id].upper()
                    if label == "CELL PHONE": label = "CELL_PHONE" 
                    
                    color = (0, 0, 255) if label == "KNIFE" else (255, 0, 0)
                    temp_boxes.append((x1, y1, x2, y2, color, f"{label} {conf:.2f}"))
                    detected_labels.add(label)

            with state.box_lock:
                state.yolo_boxes = temp_boxes

            state.threat_active = any(label in ["PISTOL", "KNIFE"] for label in detected_labels)

            current_time = time.time()
            for label in detected_labels:
                if current_time - last_logged.get(label, 0) > 15:
                    last_logged[label] = current_time
                    
                    alert_frame = frame_ai.copy()
                    with state.box_lock:
                        current_boxes = state.yolo_boxes + state.face_boxes
                    for (x1, y1, x2, y2, c, t) in current_boxes:
                        draw_ui_box(alert_frame, x1, y1, x2, y2, c, t)
                        
                    threading.Thread(target=send_alert_to_server, args=(label, alert_frame), daemon=True).start()

            elapsed = time.time() - start_time
            time.sleep(max(0, 0.033 - elapsed))
            
        except Exception as e:
            print(f"🔥 YOLO THREAD CRASHED: {e}")
            time.sleep(1)

# ==========================================
# 3. FACE RECOGNITION (HOG)
# ==========================================
def face_worker():
    known_encodings, known_names = [], []
    if os.path.exists('faces'):
        for person_name in os.listdir('faces'):
            person_folder = os.path.join('faces', person_name)
            if os.path.isdir(person_folder):
                for img_name in os.listdir(person_folder):
                    try:
                        img_path = os.path.join(person_folder, img_name)
                        img = cv2.imread(img_path)
                        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        encodings = face_recognition.face_encodings(rgb_img)
                        if encodings:
                            known_encodings.append(encodings[0])
                            known_names.append(person_name)
                    except: continue

    last_seen = {}
    
    while True:
        try:
            start_time = time.time()
            
            with state.frame_lock:
                if state.shared_frame is None:
                    time.sleep(0.01)
                    continue
                frame_ai = state.shared_frame.copy()

            small_frame = cv2.resize(frame_ai, (0, 0), fx=0.50, fy=0.50)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            face_locations = face_recognition.face_locations(rgb_small, number_of_times_to_upsample=2, model="hog")
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
            
            temp_boxes = []
            unauthorized_detected = False 
            
            for i, face_encoding in enumerate(face_encodings):
                real_name = "UNKNOWN"
                display_text = "UNAUTHORIZED"
                color = (0, 255, 255) 
                
                if known_encodings:
                    matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_TOLERANCE)
                    distances = face_recognition.face_distance(known_encodings, face_encoding)
                    
                    if len(distances) > 0:
                        best_match_index = np.argmin(distances)
                        if matches[best_match_index]:
                            real_name = known_names[best_match_index].upper()
                            display_text = "AUTHORIZED"
                            color = (0, 255, 0) 
                            
                            if start_time - last_seen.get(real_name, 0) > 300:
                                threading.Thread(target=log_person_access, args=(real_name,), daemon=True).start()
                                last_seen[real_name] = start_time
                
                if display_text == "UNAUTHORIZED":
                    unauthorized_detected = True
                    
                top, right, bottom, left = face_locations[i]
                temp_boxes.append((left*2, top*2, right*2, bottom*2, color, display_text))
                
            with state.box_lock:
                state.face_boxes = temp_boxes
                
            if unauthorized_detected and (start_time - last_seen.get("UNAUTH_ALERT", 0) > 15):
                last_seen["UNAUTH_ALERT"] = start_time
                
                alert_frame = frame_ai.copy()
                with state.box_lock:
                    current_boxes = state.yolo_boxes + state.face_boxes
                for (x1, y1, x2, y2, c, t) in current_boxes:
                    draw_ui_box(alert_frame, x1, y1, x2, y2, c, t)
                    
                threading.Thread(target=send_alert_to_server, args=("UNAUTHORIZED", alert_frame), daemon=True).start()
                
            elapsed = time.time() - start_time
            time.sleep(max(0, 0.05 - elapsed)) 
        except Exception as e:
            print(f"🔥 FACE THREAD CRASHED: {e}")
            time.sleep(1)