# backend/phone_detection.py
import torch
import cv2
import numpy as np
import time

# --- Per-Student State Management ---
student_phone_states = {} # Dictionary to hold state for each student

# --- YOLOv5 Initialization (Global) ---
try:
    # Load YOLOv5 model (downloads weights on first run)
    yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
    # Set to evaluation mode
    yolo_model.eval()
    print("YOLOv5 model loaded successfully.")
except Exception as e:
    print(f"ERROR: Could not initialize YOLOv5 model: {e}")
    yolo_model = None

# --- Constants ---
# Timer to only trigger a major alert if a phone is visible for > X seconds
PHONE_ALERT_THRESHOLD_SECONDS = 1.0
# Confidence threshold for detection
CONFIDENCE_THRESHOLD = 0.3

# --- Main Analysis Function ---
def analyze_phone_frame(image_bgr, student_id):
    """
    Analyzes a single BGR frame for cell phones, manages state (incl. timers),
    and returns an analysis dictionary.

    Returns dict: {
        "status": str, 
        "score_penalty": int, 
        "alert": str,
        "phone_boxes": list[list[int]]
    }
    """
    global student_phone_states
    global yolo_model

    # --- 1. Get/Initialize State ---
    if student_id not in student_phone_states:
        student_phone_states[student_id] = {
            "phone_detected_start_time": None,
            "phone_alerted": False
        }
    state = student_phone_states[student_id] # Use reference

    # --- 2. Basic Image Processing & Model Check ---
    if yolo_model is None:
        return {
            "status": "ERROR: YOLOv5 Failed", 
            "score_penalty": 100, 
            "alert": "Backend YOLOv5 Error",
            "phone_boxes": []
        }

    # Convert BGR (OpenCV default) to RGB (YOLOv5/PIL default)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    
    # Run inference
    # We run in a 'with' block for efficiency
    with torch.no_grad():
        results = yolo_model(image_rgb, size=640)

    # --- 3. Parse Results ---
    phone_detected_this_frame = False
    phone_boxes = []
    
    # results.xyxy[0] contains [x1, y1, x2, y2, confidence, class_id]
    predictions = results.xyxy[0].cpu().numpy()
    names = results.names # Get class names

    for pred in predictions:
        confidence = pred[4]
        class_id = int(pred[5])
        class_name = names[class_id]

        if class_name == "cell phone" and confidence > CONFIDENCE_THRESHOLD:
            phone_detected_this_frame = True
            # Get box coordinates as integers
            box = list(map(int, pred[:4]))
            phone_boxes.append(box)

    # --- 4. State Machine Logic ---
    alert = None
    score_penalty = 0
    status = "No Phone" # Default status

    if phone_detected_this_frame:
        # A phone is visible in this *current* frame
        if state["phone_detected_start_time"] is None:
            # This is the first frame we've seen it, start the timer
            state["phone_detected_start_time"] = time.time()
            state["phone_alerted"] = False
            status = "Phone Detected (Pending)"
            print(f"[{student_id}] Phone detected - timer started.")
        else:
            # Timer is already running, check if it's past the threshold
            elapsed_time = time.time() - state["phone_detected_start_time"]
            
            if elapsed_time > PHONE_ALERT_THRESHOLD_SECONDS and not state["phone_alerted"]:
                # Timer exceeded, trigger the main alert
                print(f"[{student_id}] Exceeded {PHONE_ALERT_THRESHOLD_SECONDS}s phone threshold.")
                status = "CRITICAL: Phone Detected"
                alert = f"Phone Detected."
                score_penalty = 25 # Assign a penalty
                state["phone_alerted"] = True # Mark as alerted
            elif state["phone_alerted"]:
                # Already alerted, just maintain the critical status
                status = "CRITICAL: Phone Detected"
            else:
                # Timer running but not yet exceeded
                status = "Phone Detected (Pending)"

    else:
        # No phone is visible in this frame
        if state["phone_detected_start_time"] is not None:
            # Phone was visible, but now it's gone. Reset.
            print(f"[{student_id}] Phone no longer detected - resetting timer.")
        
        state["phone_detected_start_time"] = None
        state["phone_alerted"] = False
        status = "No Phone"

    # --- 5. Return Result ---
    # The server (Flask app) will be responsible for using "phone_boxes"
    # to draw on the image before sending it to the frontend.
    return {
        "status": status,
        "score_penalty": score_penalty,
        "alert": alert,
        "phone_boxes": phone_boxes
    }

# --- Cleanup Function ---
def remove_student_phone_state(student_id):
    """ Removes state for a disconnected student """
    global student_phone_states
    if student_id in student_phone_states:
        del student_phone_states[student_id]
        print(f"Removed phone detection state for disconnected student {student_id}")