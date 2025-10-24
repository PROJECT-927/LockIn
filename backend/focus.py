import cv2
import mediapipe as mp
import numpy as np
import time
from deepface import DeepFace
import threading  

# --- Global state for threading --- ###
verification_in_progress = False
verification_result_dict = None # Will be True, False, or None


# --- Helper Function: Head Pose ---
def get_head_pose(face_landmarks, image_shape):
    """Calculates Yaw and Pitch angles from face landmarks."""
    h, w = image_shape


    # Key landmarks
    nose_tip = face_landmarks.landmark[1]
    chin = face_landmarks.landmark[152]
    left_eye_left_corner = face_landmarks.landmark[33]
    right_eye_right_corner = face_landmarks.landmark[263]
    left_mouth_corner = face_landmarks.landmark[61]
    right_mouth_corner = face_landmarks.landmark[291]

    # Get 2D image points
    image_points = np.array([
        (nose_tip.x * w, nose_tip.y * h),
        (chin.x * w, chin.y * h),
        (left_eye_left_corner.x * w, left_eye_left_corner.y * h),
        (right_eye_right_corner.x * w, right_eye_right_corner.y * h),
        (left_mouth_corner.x * w, left_mouth_corner.y * h),
        (right_mouth_corner.x * w, right_mouth_corner.y * h)
    ], dtype="double")

    # A generic 3D model of a face
    model_points = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left eye left corner
        (225.0, 170.0, -135.0),      # Right eye right corner
        (-150.0, -150.0, -125.0),    # Left mouth corner
        (150.0, -150.0, -125.0)      # Right mouth corner
    ])
   
    # Camera internals
    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype="double")

    dist_coeffs = np.zeros((4, 1)) # Assuming no lens distortion

    # SolvePnP
    try:
        (success, rotation_vector, translation_vector) = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs, 
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        # Get Euler angles (in degrees)
        (rotation_matrix, _) = cv2.Rodrigues(rotation_vector)
        sy = np.sqrt(rotation_matrix[0, 0] * rotation_matrix[0, 0] + rotation_matrix[1, 0] * rotation_matrix[1, 0])
        singular = sy < 1e-6
     
        if not singular:
            x = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            y = np.arctan2(-rotation_matrix[2, 0], sy)
            z = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
        else:
            x = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
            y = np.arctan2(-rotation_matrix[2, 0], sy)
            z = 0
            
        # y = Yaw (Left/Right), x = Pitch (Up/Down)
        yaw = np.degrees(y)
        pitch = np.degrees(x)
      
        return yaw, pitch
    except Exception as e:
        print(f"Error in solvePnP: {e}")
        return 0, 0 # Return neutral angles on error

# --- Helper Function: Gaze Estimation ---
def get_gaze_ratio(face_landmarks, image): # image arg is unused but kept for signature
    """
    Calculates gaze direction by averaging the iris position of both eyes.
    """
    try:
        # --- Left Eye Landmarks (Indices 473-477) ---
        left_eye_center_x = face_landmarks.landmark[473].x
        left_eye_left_corner_x = face_landmarks.landmark[33].x
        left_eye_right_corner_x = face_landmarks.landmark[133].x
        
        left_eye_width = left_eye_right_corner_x - left_eye_left_corner_x
        if left_eye_width == 0: 
            left_ratio = 0.5 # Default to center
        else:
            left_iris_pos = left_eye_center_x - left_eye_left_corner_x
            left_ratio = left_iris_pos / left_eye_width

        # --- Right Eye Landmarks (Indices 468-472) ---
        right_eye_center_x = face_landmarks.landmark[468].x
        right_eye_left_corner_x = face_landmarks.landmark[362].x
        right_eye_right_corner_x = face_landmarks.landmark[263].x

        right_eye_width = right_eye_right_corner_x - right_eye_left_corner_x
        if right_eye_width == 0:
            right_ratio = 0.5 # Default to center
        else:
            right_iris_pos = right_eye_center_x - right_eye_left_corner_x
            right_ratio = right_iris_pos / right_eye_width

        # --- Average Ratio ---
        ratio = (left_ratio + right_ratio) / 2.0

        if ratio < 0.35:
            return "right" # Looking right
        elif ratio > 0.65:
            return "left" # Looking left
        else:
            return "center"
            
    except Exception as e:
        print(f"Error in gaze estimation: {e}")
        return "center" # Default to center on error

# --- Helper Function: Face Verification (Threaded) --- ### --- MODIFIED --- ###

def verify_identity_threaded(current_image_frame):
    """
    Runs DeepFace.verify in a separate thread using the 'Facenet' model.
    Stores the ENTIRE result dictionary in a global variable.
    """
    global verification_in_progress, verification_result_dict
    
    image_copy = current_image_frame.copy() 
  
    try:
        # --- MODEL CHANGED TO FACENET ---
        # 'Facenet' is much better for verification and more forgiving.
        # We also use the 'mtcnn' detector, which is robust.
        result = DeepFace.verify(
            img1_path="reference_image.jpg", 
            img2_path=image_copy,
            model_name='Facenet',       # <--- THIS IS THE KEY CHANGE
            detector_backend='mtcnn',   # <--- This detector works well with Facenet
            enforce_detection=True
        )
        # Store the whole dictionary
        verification_result_dict = result
    except Exception as e:
        print(f"Verification error (or no face found): {e}")
        # On error, create a "fail" dictionary
        # Note: Facenet's default threshold is 0.40
        verification_result_dict = {"verified": False, "distance": 1.0, "threshold": 0.40} 
    
    # Signal that verification is done
    verification_in_progress = False
    print("Verification thread finished.")

# --- Phase 1: Enrollment Function ---
# Make sure 'import time' is at the top of your Python file

def enroll_student(cam):
    """
    Captures and saves a reference image after a 3-second countdown.
    Starts the countdown as soon as a face is detected.
    """
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, 
                                      min_detection_confidence=0.7)

    print("--- Enrollment Phase ---")
    print("Please look at the camera.")
    print("Press 'q' to quit.")

    countdown_started = False
    countdown_start_time = 0

    while True:
        success, image = cam.read()
        if not success:
            print("Failed to get camera feed.")
            return False
        
        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        image.flags.writeable = False
        results = face_mesh.process(image_rgb)
        image.flags.writeable = True
        
        display_image = image.copy()

        if results.multi_face_landmarks:
            # --- Face is detected, start/continue countdown ---
            
            if not countdown_started:
                # Start the timer
                countdown_start_time = time.time()
                countdown_started = True
            
            elapsed_time = time.time() - countdown_start_time
            remaining_time = 3.0 - elapsed_time

            if remaining_time <= 0:
                # --- SUCCESS! ---
                # Countdown finished. Capture the image.
                cv2.putText(display_image, "Perfect! Capturing...", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.imshow("Enrollment", display_image)
                cv2.waitKey(500) # Short pause to show message
                
                # Re-capture a fresh image right before saving
                success, final_image = cam.read()
                if not success: continue
                
                final_image = cv2.flip(final_image, 1)
                cv2.imwrite("reference_image.jpg", final_image)
                print("Enrollment complete! Reference saved.")
                face_mesh.close()
                cv2.destroyWindow("Enrollment")
                return True
            
            else:
                # --- Countdown is active ---
                cv2.putText(display_image, "Face Detected. Hold still...", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(display_image, f"Capturing in {remaining_time:.0f}s", (50, 80), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        else:
            # --- No face detected ---
            # Reset the countdown
            countdown_started = False 
            cv2.putText(display_image, "No face detected. Please position yourself.", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow("Enrollment", display_image)

        if cv2.waitKey(5) & 0xFF == ord('q'):
            break
    
    face_mesh.close()
    cv2.destroyWindow("Enrollment")
    return False
# (Your get_gaze_ratio function)
# (Your verify_identity_threaded function)
# (Your main function)

# (Your imports, global variables, and helper functions go here...)
# ...

# --- Phase 2: Main Application ---

def main():
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=5,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        refine_landmarks=True
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open webcam.")
        return
    
    # --- STEP 1: ENROLLMENT (This runs first and must complete) ---
    if not enroll_student(cap): # Using the "countdown" enroll_student
        print("Enrollment Failed or Canceled. Exiting.")
        cap.release()
        return
    
    print("--- Starting Monitoring ---")

    # --- State Variables ---
    # --- STEP 2: SET STATUS (Initial_Check is removed) ---
    user_status = "Focused" # <-- CHANGED: Start monitoring immediately
    away_start_time = None
    AWAY_THRESHOLD = 5.0
    
    welcome_back_start_time = None
    WELCOME_BACK_DELAY = 4.0

    global verification_in_progress, verification_result_dict 

    # --- NEW: Temporary Alert Variables ---
    alert_message = ""
    alert_message_time = 0
    ALERT_DURATION = 5.0 # Show alerts for 5 seconds

    MY_VERIFICATION_THRESHOLD = 0.50 

    # --- STEP 3: MAIN LOOP BEGINS ---
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        image = cv2.flip(image, 1)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        image.flags.writeable = False
        results = face_mesh.process(image_rgb)
        image.flags.writeable = True
        
        image_bgr = image
        img_h, img_w, _ = image_bgr.shape

        
        # --- Check for verification results ---
        if not verification_in_progress and verification_result_dict is not None:
            
            distance = verification_result_dict.get("distance", 1.0)
            default_threshold = verification_result_dict.get("threshold", 0.40)
            
            print(f"Verification complete. Distance: {distance:.2f} (Default: {default_threshold})")

            if distance > MY_VERIFICATION_THRESHOLD:
                # --- REQUEST 2: SWAP DETECTED ---
                print(f"!!! HIGH ALERT: IDENTITY MISMATCH !!! (Distance {distance:.2f} > {MY_VERIFICATION_THRESHOLD})")
                cv2.imwrite(f"alert_swap_{int(time.time())}.jpg", image_bgr)
                
                # Set temporary alert and continue monitoring
                alert_message = "ALERT: IDENTITY MISMATCH!"
                alert_message_time = time.time()
                user_status = "Focused" # <-- CHANGED: Go back to monitoring
            
            else:
                # --- Verification Succeeded ---
                print(f"Identity verified. Welcome back. (Distance {distance:.2f} <= {MY_VERIFICATION_THRESHOLD})")
                
                # Set temporary success message
                alert_message = "Identity Verified"
                alert_message_time = time.time()
                user_status = "Focused" # Proceed to monitoring
            
            verification_result_dict = None


        # --- Main Logic ---
        if results.multi_face_landmarks:
            # === 1. FACE IS PRESENT ===
            
            # --- REQUEST 1: "Initial_Check" block is removed ---
            
            if user_status == "Away":
                print("Face re-detected. Starting welcome back timer...")
                user_status = "Welcome_Back"
                welcome_back_start_time = time.time()
            
            elif user_status == "Welcome_Back":
                if time.time() - welcome_back_start_time > WELCOME_BACK_DELAY:
                    if not verification_in_progress:
                        print(f"Delay of {WELCOME_BACK_DELAY}s over. Starting verification thread...")
                        user_status = "Verifying..."
                        verification_in_progress = True
                        verification_result_dict = None
                        
                        thread = threading.Thread(
                            target=verify_identity_threaded, 
                            args=(image_bgr,),
                            daemon=True
                        )
                        thread.start()
            
            away_start_time = None
            
            # --- Run proctoring checks *only if* not busy verifying ---
            if user_status not in ["Verifying...", "Welcome_Back"]:
                
                if len(results.multi_face_landmarks) > 1:
                    user_status = "Distracted"
                    # Set temporary alert
                    alert_message = "ALERT: MULTIPLE FACES!"
                    alert_message_time = time.time()

                elif user_status == "Focused" or user_status == "Distracted":
                    user_status = "Focused" # Assume focused
                    face_landmarks = results.multi_face_landmarks[0]
                    
                    # Check Head Pose
                    yaw, pitch = get_head_pose(face_landmarks, (img_h, img_w))
                    if yaw > 30 or yaw < -30 or pitch > 25:
                        user_status = "Distracted"
                        cv2.putText(image_bgr, "Distracted: Head Pose", (10, 90), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
                    
                    # Check Gaze (only if head is straight)
                    if user_status == "Focused":
                        gaze_direction = get_gaze_ratio(face_landmarks, image_bgr) # Make sure this function name is right!
                        if gaze_direction != "center":
                            user_status = "Distracted"
                            cv2.putText(image_bgr, f"Distracted: Gaze {gaze_direction}", (10, 120), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
                
        else:
            # === 2. NO FACE FOUND ===
            if user_status not in ["Verifying...", "Welcome_Back"]: 
                if away_start_time is None:
                    away_start_time = time.time()
                
                elif time.time() - away_start_time > AWAY_THRESHOLD:
                    if user_status != "Away":
                        print("User is Away")
                        user_status = "Away"
                
                if user_status == "Welcome_Back":
                    print("User left during welcome back delay. Resetting.")
                    user_status = "Away"
                    welcome_back_start_time = None

                if verification_in_progress:
                    print("User left during verification. Resetting.")
                    verification_in_progress = False
                    verification_result_dict = None

       
        # --- Draw Temporary Alert Message ---
        if alert_message and (time.time() - alert_message_time < ALERT_DURATION):
            alert_color = (0, 0, 255) if "ALERT" in alert_message else (0, 255, 0)
            cv2.putText(image_bgr, alert_message, (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, alert_color, 2)
        else:
            alert_message = "" # Clear message after duration
           
        # --- Draw Main Status Text ---
        color = (0, 255, 0) # Green
        if "Distracted" in user_status:
            color = (0, 165, 255) # Orange
        elif "Away" in user_status:
            color = (0, 0, 255) # Red
        elif "Verifying" in user_status or "Welcome_Back" in user_status:
            color = (0, 255, 255) # Yellow
        # "ALERT_SWAP" status is no longer used, so it's removed from here

        cv2.putText(image_bgr, f"STATUS: {user_status}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        cv2.imshow('Proctoring System', image_bgr)

        if cv2.waitKey(5) & 0xFF == ord('q'):
            print("Exiting...")
            break

    # --- Cleanup ---
    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()

if __name__ == "__main__":
    main()

