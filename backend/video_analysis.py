# backend/focus.py
import cv2
import mediapipe as mp
import numpy as np
from deepface import DeepFace # Make sure DeepFace is imported
import threading
import time
import os

# --- Per-Student State Management ---
student_video_states = {} # Dictionary to hold state for each student: {student_id: state_dict}

# --- MediaPipe Initialization (Global) ---
mp_face_mesh = mp.solutions.face_mesh
try:
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=5,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        refine_landmarks=True # Needed for iris landmarks
    )
    print("MediaPipe FaceMesh initialized successfully.")
except AttributeError:
    print("ERROR: Could not initialize MediaPipe FaceMesh. Is MediaPipe installed correctly?")
    face_mesh = None
except Exception as e:
    print(f"ERROR: Unexpected error initializing FaceMesh: {e}")
    face_mesh = None


# --- Constants ---
AWAY_THRESHOLD_SECONDS = 3.0
WELCOME_BACK_DELAY_SECONDS = 3.0
MY_VERIFICATION_THRESHOLD = 0.50 # Face verification distance threshold
GAZE_AWAY_THRESHOLD_SECONDS = 5.0 # Gaze timer threshold (Increased from 3.0)

# --- Helper Functions (get_head_pose, get_gaze_ratio - REPLACED) ---
# def get_head_pose(face_landmarks, image_shape):
#     """Calculates Yaw and Pitch angles from face landmarks."""
#     h, w = image_shape

#     if face_landmarks is None: return 0, 0 # Added safety check

#     try:
#         # Key landmarks
#         nose_tip = face_landmarks.landmark[1]
#         chin = face_landmarks.landmark[152]
#         left_eye_left_corner = face_landmarks.landmark[33]
#         right_eye_right_corner = face_landmarks.landmark[263]
#         left_mouth_corner = face_landmarks.landmark[61]
#         right_mouth_corner = face_landmarks.landmark[291]

#         # Get 2D image points
#         image_points = np.array([
#             (nose_tip.x * w, nose_tip.y * h),
#             (chin.x * w, chin.y * h),
#             (left_eye_left_corner.x * w, left_eye_left_corner.y * h),
#             (right_eye_right_corner.x * w, right_eye_right_corner.y * h),
#             (left_mouth_corner.x * w, left_mouth_corner.y * h),
#             (right_mouth_corner.x * w, right_mouth_corner.y * h)
#         ], dtype="double")

#         # A generic 3D model of a face
#         model_points = np.array([
#             (0.0, 0.0, 0.0),             # Nose tip
#             (0.0, -330.0, -65.0),        # Chin
#             (-225.0, 170.0, -135.0),     # Left eye left corner
#             (225.0, 170.0, -135.0),      # Right eye right corner
#             (-150.0, -150.0, -125.0),    # Left mouth corner
#             (150.0, -150.0, -125.0)      # Right mouth corner
#         ])
        
#         # Camera internals
#         focal_length = w
#         center = (w / 2, h / 2)
#         camera_matrix = np.array([
#             [focal_length, 0, center[0]],
#             [0, focal_length, center[1]],
#             [0, 0, 1]
#         ], dtype="double")

#         dist_coeffs = np.zeros((4, 1)) # Assuming no lens distortion

#         # SolvePnP
#         (success, rotation_vector, translation_vector) = cv2.solvePnP(
#             model_points, image_points, camera_matrix, dist_coeffs, 
#             flags=cv2.SOLVEPNP_ITERATIVE
#         )
        
#         # Get Euler angles (in degrees)
#         (rotation_matrix, _) = cv2.Rodrigues(rotation_vector)
#         sy = np.sqrt(rotation_matrix[0, 0] * rotation_matrix[0, 0] + rotation_matrix[1, 0] * rotation_matrix[1, 0])
#         singular = sy < 1e-6
        
#         if not singular:
#             x = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
#             y = np.arctan2(-rotation_matrix[2, 0], sy)
#             z = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
#         else:
#             x = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
#             y = np.arctan2(-rotation_matrix[2, 0], sy)
#             z = 0
            
#         # y = Yaw (Left/Right), x = Pitch (Up/Down)
#         yaw = np.degrees(y)
#         pitch = np.degrees(x)
        
#         return yaw, pitch
#     except Exception as e:
#         print(f"Error in solvePnP or landmark access: {e}") # Updated print
#         return 0, 0 # Return neutral angles on error
def get_head_pose(face_landmarks, image_shape):
    """
    Estimates Yaw and Pitch using simple 2D landmark ratios.
    This is MUCH less accurate than solvePnP but far simpler.
    """
    if face_landmarks is None:
        return 0, 0 # Return neutral angles if no face

    try:
        # Key landmarks
        nose_tip = face_landmarks.landmark[1]
        left_eye_inner = face_landmarks.landmark[133]
        right_eye_inner = face_landmarks.landmark[362]
        forehead = face_landmarks.landmark[10]
        chin = face_landmarks.landmark[152]

        # --- YAW (Left/Right) Estimation ---
        # Compare horizontal distance from nose to each inner eye corner
        dist_nose_to_left = abs(nose_tip.x - left_eye_inner.x)
        dist_nose_to_right = abs(nose_tip.x - right_eye_inner.x)
        
        # Create a ratio. (+ 1e-6 to avoid division by zero)
        # If head turns right, dist_nose_to_left grows.
        # If head turns left, dist_nose_to_right grows.
        yaw_ratio = (dist_nose_to_left - dist_nose_to_right) / (dist_nose_to_left + dist_nose_to_right + 1e-6)
        
        # Scale ratio (-1.0 to 1.0) to an approximate degree for your thresholds
        yaw = yaw_ratio * 90 

        # --- PITCH (Up/Down) Estimation ---
        # Compare vertical distance from nose to forehead vs nose to chin
        dist_nose_to_forehead = abs(nose_tip.y - forehead.y)
        dist_nose_to_chin = abs(nose_tip.y - chin.y)

        # Create a ratio.
        # If looking up, nose moves closer to chin (dist_nose_to_chin decreases).
        # If looking down, nose moves closer to forehead (dist_nose_to_forehead decreases).
        pitch_ratio = (dist_nose_to_forehead - dist_nose_to_chin) / (dist_nose_to_forehead + dist_nose_to_chin + 1e-6)
        
        # Scale ratio to an approximate degree.
        # Note: MediaPipe's Y-axis is inverted (0 is top), so a positive ratio means looking down.
        # We multiply by -90 to flip it so "up" is positive and "down" is negative,
        # matching the logic of your PITCH_THRESHOLD_UP/DOWN.
        pitch = pitch_ratio * -90
        
        return yaw, pitch
        
    except Exception as e:
        print(f"Error in simple head pose: {e}")
        return 0, 0 # Return neutral on error

def get_gaze_ratio(face_landmarks, image_shape): # Renamed arg to match usage
    """
    Calculates gaze direction by averaging the iris position of both eyes.
    """
    if face_landmarks is None: return "center" # Added safety check

    try:
        # --- Left Eye Landmarks (Indices 473-477) ---
        # Note: Using 473 as center, but 473-477 are all iris landmarks
        left_eye_center_x = face_landmarks.landmark[473].x 
        left_eye_left_corner_x = face_landmarks.landmark[33].x
        left_eye_right_corner_x = face_landmarks.landmark[133].x
        
        # Ensure correct order for width calculation
        if left_eye_right_corner_x < left_eye_left_corner_x:
            left_eye_left_corner_x, left_eye_right_corner_x = left_eye_right_corner_x, left_eye_left_corner_x

        left_eye_width = left_eye_right_corner_x - left_eye_left_corner_x
        if left_eye_width == 0: 
            left_ratio = 0.5 # Default to center
        else:
            left_iris_pos = left_eye_center_x - left_eye_left_corner_x
            left_ratio = np.clip(left_iris_pos / left_eye_width, 0.0, 1.0) # Added clip

        # --- Right Eye Landmarks (Indices 468-472) ---
        # Note: Using 468 as center, but 468-472 are all iris landmarks
        right_eye_center_x = face_landmarks.landmark[468].x
        right_eye_left_corner_x = face_landmarks.landmark[362].x
        right_eye_right_corner_x = face_landmarks.landmark[263].x

        # Ensure correct order for width calculation
        if right_eye_right_corner_x < right_eye_left_corner_x:
            right_eye_left_corner_x, right_eye_right_corner_x = right_eye_right_corner_x, right_eye_left_corner_x

        right_eye_width = right_eye_right_corner_x - right_eye_left_corner_x
        if right_eye_width == 0:
            right_ratio = 0.5 # Default to center
        else:
            right_iris_pos = right_eye_center_x - right_eye_left_corner_x
            right_ratio = np.clip(right_iris_pos / right_eye_width, 0.0, 1.0) # Added clip

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


# --- Helper Function: Face Verification (Threaded) ---
# Accepts reference_image_path determined by server.py
def verify_identity_threaded(current_image_frame, student_id, reference_image_path):
    """
    Runs DeepFace.verify using the provided reference path. Updates state dict.
    """
    global student_video_states

    print(f"[{student_id}] Verification thread started (Using Ref: {reference_image_path})...")

    result_dict = None
    try:
        if not reference_image_path or not os.path.exists(reference_image_path):
            raise FileNotFoundError(f"Reference image not found at path: {reference_image_path}")

        result = DeepFace.verify(
            img1_path=reference_image_path, # Use the passed path
            img2_path=current_image_frame,  # Pass numpy array directly
            model_name='Facenet',
            detector_backend='mtcnn',       # Recommended detector for Facenet
            enforce_detection=True          # Must find face in img2_path
        )
        result_dict = result
    except FileNotFoundError as fnf_error:
        print(f"[{student_id}] Verification Error: {fnf_error}")
        result_dict = {"verified": False, "distance": 1.0, "threshold": 0.40, "error": str(fnf_error)}
    except ValueError as val_error: # Often means no face found in img2_path
        print(f"[{student_id}] Verification Value Error: {val_error}")
        result_dict = {"verified": False, "distance": 1.0, "threshold": 0.40, "error": "No face detected in snapshot"}
    except Exception as e: # Catch other potential errors (model loading, etc.)
        print(f"[{student_id}] General Verification error: {e}")
        result_dict = {"verified": False, "distance": 1.0, "threshold": 0.40, "error": str(e)}

    # Safely update state only if student still exists
    if student_id in student_video_states:
        student_video_states[student_id]['verification_result_dict'] = result_dict
        student_video_states[student_id]['verification_in_progress'] = False
        print(f"[{student_id}] Verification thread finished.")
    else:
        print(f"[{student_id}] Verification finished, but student state missing (likely disconnected).")


# --- Main Analysis Function ---
# Accepts fallback_reference_path from server.py (used if dynamic isn't set/found)
def analyze_frame(image_bgr, student_id, fallback_reference_path):
    """
    Analyzes frame, manages state (incl verification, gaze timer), triggers verification thread.
    Returns dict: {"status": str, "score_penalty": int, "alert": str}
    """
    global student_video_states

    # --- 1. Get/Initialize State ---
    if student_id not in student_video_states:
        student_video_states[student_id] = {
            "status": "Focused", # Initial status
            "away_start_time": None,
            "welcome_back_start_time": None,
            "verification_in_progress": False,
            "verification_result_dict": None,
            "gaze_start_time": None, # Gaze timer state
            "gaze_alerted": False,   # Gaze timer state
            "referenceImagePath": None # Path to dynamic ref image (set by server)
            # Add 'referenceImageB64' if needed here, but path is used for verification
        }
    state = student_video_states[student_id] # Use reference for easier access

    # --- 2. Basic Image Processing ---
    if face_mesh is None:
        return {"status": "ERROR: MediaPipe Failed", "score_penalty": 100, "alert": "Backend MediaPipe Error"}

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False # Performance hint
    try:
        results = face_mesh.process(image_rgb)
    except Exception as e:
        print(f"ERROR [Analyze]: face_mesh.process failed for {student_id}: {e}")
        return {"status": "ERROR: Face Mesh Failed", "score_penalty": 0, "alert": "Face detection failed"}
    finally:
        image_rgb.flags.writeable = True # Make writeable again
    img_h, img_w, _ = image_bgr.shape

    # --- 3. Check Verification Results FIRST ---
    alert = None; score_penalty = 0; current_status = state["status"] # Store status before checks
    if not state["verification_in_progress"] and state["verification_result_dict"] is not None:
        result_dict = state["verification_result_dict"]
        distance = result_dict.get("distance", 1.0); error_msg = result_dict.get("error")
        if error_msg:
             state["status"] = "Focused"; # Reset status on error
             print(f"[{student_id}] Verification error processed: {error_msg}")
             # Optional: alert = f"Verification Error: {error_msg}" # Might be too noisy
        elif distance > MY_VERIFICATION_THRESHOLD:
             state["status"] = "CRITICAL: IMPERSONATION"; alert = f"CRITICAL: IDENTITY MISMATCH! (Confidence: {distance:.2f})"; score_penalty = 100
        else:
             state["status"] = "Focused"; alert = "Identity Verified" # Temporary message
        state["verification_result_dict"] = None # Consume the result

    # --- 4. State Machine Logic ---
    if results.multi_face_landmarks:
        # --- 4a. Face(s) Present ---
        if state["status"] == "Away":
            state["status"] = "Welcome_Back"; state["welcome_back_start_time"] = time.time()
        elif state["status"] == "Welcome_Back":
            if time.time() - state["welcome_back_start_time"] > WELCOME_BACK_DELAY_SECONDS:
                if not state["verification_in_progress"]:
                    state["status"] = "Verifying..."; state["verification_in_progress"] = True; state["verification_result_dict"] = None
                    # Determine which reference path to use for this verification
                    ref_path_to_use = state.get("referenceImagePath") or fallback_reference_path
                    # Start the verification thread
                    thread = threading.Thread(target=verify_identity_threaded, args=(image_bgr.copy(), student_id, ref_path_to_use), daemon=True)
                    thread.start()
        state["away_start_time"] = None # Reset away timer

        # --- 4b. Proctoring Checks (if not busy/critical) ---
        if state["status"] not in ["Verifying...", "Welcome_Back", "CRITICAL: IMPERSONATION"]:
            num_faces = len(results.multi_face_landmarks)
            if num_faces > 1:
                state["status"] = "CRITICAL: Multiple Faces"; score_penalty = 25; alert = f"{num_faces} faces detected!"
                # Reset gaze timer if multiple faces detected
                state["gaze_start_time"] = None; state["gaze_alerted"] = False
            else: # Single face
                if not alert: state["status"] = "Focused" # Reset only if no other alert/status set yet this frame
                face_landmarks = results.multi_face_landmarks[0]
                yaw, pitch = get_head_pose(face_landmarks, (img_h, img_w))

                # Head Pose Check (takes precedence)
                YAW_THRESHOLD = 45.0  # Increased from 35.0
                PITCH_THRESHOLD_UP = 40.0  # Increased from 30.0
                PITCH_THRESHOLD_DOWN = -30.0 # Increased (made more negative) from -20.0
                head_pose_out_of_bounds = (abs(yaw) > YAW_THRESHOLD or pitch > PITCH_THRESHOLD_UP or pitch < PITCH_THRESHOLD_DOWN)

                if head_pose_out_of_bounds:
                    state["status"] = "Looking Away"; score_penalty = 5; alert = f"Head pose out (Y:{yaw:.1f}, P:{pitch:.1f})"
                    # Reset gaze timer if head is turned away
                    state["gaze_start_time"] = None; state["gaze_alerted"] = False
                # Gaze Check (only if head pose okay AND status allows)
                elif state["status"] == "Focused":
                    gaze_direction = get_gaze_ratio(face_landmarks, (img_h, img_w)) # Pass image_shape
                    if gaze_direction != "center":
                        # Gaze away - Start or check timer
                        if state["gaze_start_time"] is None:
                             state["gaze_start_time"] = time.time(); state["gaze_alerted"] = False
                             print(f"[{student_id}] Gaze moved {gaze_direction} - timer started.")
                        else:
                             elapsed_gaze_time = time.time() - state["gaze_start_time"]
                             if elapsed_gaze_time > GAZE_AWAY_THRESHOLD_SECONDS and not state["gaze_alerted"]:
                                 print(f"[{student_id}] Exceeded {GAZE_AWAY_THRESHOLD_SECONDS}s gaze threshold.")
                                 state["status"] = f"Distracted Gaze ({gaze_direction.capitalize()})"
                                 score_penalty = 2 # Low penalty for timed gaze
                                 alert = f"Gaze {gaze_direction} for > {GAZE_AWAY_THRESHOLD_SECONDS:.0f}s."
                                 state["gaze_alerted"] = True
                    else:
                        # Gaze center - Reset timer
                        if state["gaze_start_time"] is not None: print(f"[{student_id}] Gaze returned center - timer reset.")
                        state["gaze_start_time"] = None; state["gaze_alerted"] = False
    else:
        # --- 4c. No Face Found ---
        if state["status"] not in ["Verifying...", "Welcome_Back"]:
             if state["away_start_time"] is None: state["away_start_time"] = time.time()
             elif time.time() - state["away_start_time"] > AWAY_THRESHOLD_SECONDS:
                 if state["status"] != "Away": state["status"] = "Away"; score_penalty = 15; alert = "No student detected."
             # Reset other states if user goes away
                 if state["status"] == "Welcome_Back": state["welcome_back_start_time"]=None; state["status"]="Away";
                 if state["away_start_time"] is None: state["away_start_time"] = time.time()
                 if state["verification_in_progress"]: state["verification_in_progress"]=False; state["verification_result_dict"]=None; state["status"]="Away"; 
                 if state["away_start_time"] is None: state["away_start_time"] = time.time()
        # Reset gaze timer if no face is found
        state["gaze_start_time"] = None; state["gaze_alerted"] = False

    # --- 5. Final Alert/Status Cleanup ---
    if alert == "Identity Verified" and state["status"] != "Focused": alert = None
    elif alert == "Identity Verified" and state["status"] == "Focused" and current_status == "Focused": alert = None
    final_status = state["status"]

    # --- 6. Return Result ---
    return {"status": final_status, "score_penalty": score_penalty, "alert": alert}

# --- Cleanup Function ---
def remove_student_state(student_id):
    """ Removes state for a disconnected student """
    global student_video_states
    if student_id in student_video_states:
        del student_video_states[student_id]
        print(f"Removed video state for disconnected student {student_id}")