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
AWAY_THRESHOLD_SECONDS = 5.0
WELCOME_BACK_DELAY_SECONDS = 4.0
MY_VERIFICATION_THRESHOLD = 0.50 # Face verification distance threshold
GAZE_AWAY_THRESHOLD_SECONDS = 3.0 # Gaze timer threshold

# --- Helper Functions (get_head_pose, get_gaze_ratio - unchanged) ---
def get_head_pose(face_landmarks, image_shape):
    """Calculates Yaw and Pitch angles (degrees) from face landmarks."""
    h, w = image_shape
    if face_landmarks is None: return 0, 0
    try:
        # Key landmarks indices
        nose_tip_idx, chin_idx = 1, 152
        left_eye_left_corner_idx, right_eye_right_corner_idx = 33, 263
        left_mouth_corner_idx, right_mouth_corner_idx = 61, 291
        lm = face_landmarks.landmark
        required_indices = [nose_tip_idx, chin_idx, left_eye_left_corner_idx, right_eye_right_corner_idx, left_mouth_corner_idx, right_mouth_corner_idx]
        if any(idx >= len(lm) for idx in required_indices): print("ERROR [Pose]: Landmark index out of bounds."); return 0, 0
        # 2D points
        image_points = np.array([(lm[i].x * w, lm[i].y * h) for i in required_indices], dtype="double")
        # 3D model points
        model_points = np.array([(0.0, 0.0, 0.0), (0.0, -330.0, -65.0), (-225.0, 170.0, -135.0), (225.0, 170.0, -135.0), (-150.0, -150.0, -125.0), (150.0, -150.0, -125.0)])
        # Camera matrix
        focal_length = w; center = (w / 2, h / 2)
        camera_matrix = np.array([[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype="double")
        dist_coeffs = np.zeros((4, 1))
        # SolvePnP
        (success, rotation_vector, _) = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
        if not success: print("WARN [Pose]: solvePnP failed."); return 0, 0
        # Euler angles
        (rotation_matrix, _) = cv2.Rodrigues(rotation_vector)
        sy = np.sqrt(rotation_matrix[0, 0]**2 + rotation_matrix[1, 0]**2); singular = sy < 1e-6
        if not singular: x = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2]); y = np.arctan2(-rotation_matrix[2, 0], sy)
        else: x = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1]); y = np.arctan2(-rotation_matrix[2, 0], sy)
        yaw = np.degrees(y); pitch = np.degrees(x)
        return yaw, pitch
    except Exception as e: print(f"ERROR [Pose]: {e}"); return 0, 0

def get_gaze_ratio(face_landmarks, image_shape):
    """ Estimates horizontal gaze direction. Returns "left", "right", or "center". """
    h, w = image_shape
    if face_landmarks is None: return "center"
    try:
        lm = face_landmarks.landmark
        # Iris and eye corner indices
        l_iris, l_inner, l_outer = 473, 133, 33
        r_iris, r_inner, r_outer = 468, 362, 263
        required_indices = [l_iris, l_inner, l_outer, r_iris, r_inner, r_outer]
        if any(idx >= len(lm) for idx in required_indices): print("ERROR [Gaze]: Iris index OOB."); return "center"
        # Left Eye
        l_iris_x, l_inner_x, l_outer_x = lm[l_iris].x, lm[l_inner].x, lm[l_outer].x
        if l_outer_x > l_inner_x: l_outer_x, l_inner_x = l_inner_x, l_outer_x # Ensure outer < inner
        l_width = l_inner_x - l_outer_x; left_ratio = np.clip((l_iris_x - l_outer_x) / l_width, 0.0, 1.0) if l_width > 1e-6 else 0.5
        # Right Eye
        r_iris_x, r_inner_x, r_outer_x = lm[r_iris].x, lm[r_inner].x, lm[r_outer].x
        if r_outer_x > r_inner_x: r_outer_x, r_inner_x = r_inner_x, r_outer_x # Ensure outer < inner
        r_width = r_inner_x - r_outer_x; right_ratio = np.clip((r_iris_x - r_outer_x) / r_width, 0.0, 1.0) if r_width > 1e-6 else 0.5
        # Average
        avg_ratio = (left_ratio + right_ratio) / 2.0
        # Thresholds (relative to eye width, 0=Outer, 1=Inner)
        GAZE_THRESH_RIGHT, GAZE_THRESH_LEFT = 0.40, 0.60
        if avg_ratio < GAZE_THRESH_RIGHT: return "right"
        elif avg_ratio > GAZE_THRESH_LEFT: return "left"
        else: return "center"
    except Exception as e: print(f"ERROR [Gaze]: {e}"); return "center"


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
                YAW_THRESHOLD = 35.0; PITCH_THRESHOLD_UP = 30.0; PITCH_THRESHOLD_DOWN = -20.0
                head_pose_out_of_bounds = (abs(yaw) > YAW_THRESHOLD or pitch > PITCH_THRESHOLD_UP or pitch < PITCH_THRESHOLD_DOWN)

                if head_pose_out_of_bounds:
                    state["status"] = "Looking Away"; score_penalty = 5; alert = f"Head pose out (Y:{yaw:.1f}, P:{pitch:.1f})"
                    # Reset gaze timer if head is turned away
                    state["gaze_start_time"] = None; state["gaze_alerted"] = False
                # Gaze Check (only if head pose okay AND status allows)
                elif state["status"] == "Focused":
                    gaze_direction = get_gaze_ratio(face_landmarks, (img_h, img_w))
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