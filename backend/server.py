# backend/server.py
import eventlet
eventlet.monkey_patch() 
from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import datetime
import base64
import numpy as np
import cv2
import os
import tempfile
import subprocess
import threading
import shutil
import io
import soundfile as sf

# --- Import logic ---
import  video_analysis # Expects analyze_frame, remove_student_state
# from voice_analysis import transcribe_fast, analyze_fast
import phone_detection # Import phone detection

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=False, engineio_logger=False)

# --- Directories ---
BASE_DIR = os.path.dirname(__file__)
SUSPICIOUS_AUDIO_DIR = os.path.join(BASE_DIR, "suspicious_audio")
# --- Use reference_images dir for dynamically saved wallpapers ---
REFERENCE_IMAGES_DIR = os.path.join(BASE_DIR, "reference_images")
os.makedirs(SUSPICIOUS_AUDIO_DIR, exist_ok=True)
os.makedirs(REFERENCE_IMAGES_DIR, exist_ok=True)

# --- Load STATIC Reference Image (as fallback ONLY) ---
STATIC_REFERENCE_IMAGE_FILENAME = "reference_image.jpg" # Fallback filename
STATIC_REFERENCE_IMAGE_PATH = os.path.join(BASE_DIR, STATIC_REFERENCE_IMAGE_FILENAME)
STATIC_REFERENCE_IMAGE_B64 = None
try:
    # Load fallback ONLY if it exists, don't warn loudly if missing now
    if os.path.exists(STATIC_REFERENCE_IMAGE_PATH):
        with open(STATIC_REFERENCE_IMAGE_PATH, "rb") as image_file:
            STATIC_REFERENCE_IMAGE_B64 = base64.b64encode(image_file.read()).decode('utf-8')
        print(f"Loaded static fallback reference image ('{STATIC_REFERENCE_IMAGE_FILENAME}').")
    else:
        print(f"INFO: Static fallback reference image ('{STATIC_REFERENCE_IMAGE_FILENAME}') not found. Dynamic capture is required.")
except Exception as e:
     print(f"WARNING: Error loading static fallback reference image: {e}")

# --- Server State ---
connected_students = {}  # {id, sid, score, status, snapshot, wallpaperB64, wallpaperPath, warnings}
admin_sids = set()       # Use set for efficiency
exam_questions = []
sid_to_student = {}

# --- Helper Functions ---
def b64_to_cv2_image(b64_string):
    """ Converts a Base64 string to an OpenCV image (BGR). """
    try:
        img_bytes = base64.b64decode(b64_string)
        img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        if img is None: print("ERROR [Image Decode]: cv2.imdecode returned None."); return None
        return img
    except Exception as e: print(f"ERROR [Image Decode]: {e}"); return None

def emit_alert_to_admin(student_id, message, color="#ffc107", snapshot=None, audio_filename=None):
    """ Sends a standardized alert message to all connected admins. """
    if not admin_sids: print(f"ALERT (No Admins): {student_id}: {message}"); return
    print(f"ALERT: {student_id}: {message}")
    alert = { "id": f"{student_id}_{int(time.time()*1000)}", "text": f"{student_id}: {message}", "time": time.strftime("%H:%M:%S"), "color": color, "snapshot": snapshot, "audio_filename": audio_filename }
    socketio.emit("new_alert", alert, room="admin_room") # Emit to admin room

def emit_student_update(student_id):
    """ Sends the complete, current state of a student to all admins. """
    if student_id in connected_students and admin_sids:
        state_to_send = connected_students[student_id].copy()
        print(f"DEBUG [Update]: Emitting update for {student_id} | Score: {state_to_send.get('score','N/A')} | Status: '{state_to_send.get('status','N/A')}' | Wallpaper Set: {'Yes' if state_to_send.get('wallpaperPath') else 'No'}")
        socketio.emit("student_update", state_to_send, room="admin_room")


# --- SocketIO Event Handlers ---

@socketio.on('connect')
def on_connect():
    sid = request.sid; print(f"Client connected: {sid}")

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid; print(f"Client disconnected: {sid}")
    if sid in sid_to_student:
        student_id = sid_to_student.pop(sid)
        print(f"Student left: {student_id}")
        if student_id in connected_students: del connected_students[student_id]
        try:
            video_analysis.remove_student_state(student_id) # Cleanup focus state
            phone_detection.remove_student_phone_state(student_id) # Cleanup phone state
            print(f"DEBUG [Disconnect]: Cleaned up analysis states for {student_id}")
        except Exception as e: print(f"ERROR [Disconnect Cleanup]: {e}")
        if admin_sids: print(f"DEBUG [Disconnect]: Emitting student_left for {student_id}"); socketio.emit("student_left", {"student_id": student_id}, room="admin_room")
    elif sid in admin_sids: print(f"Admin left: {sid}"); admin_sids.discard(sid)
    print(f"Current State: {len(connected_students)} students, {len(admin_sids)} admins.")


@socketio.on('adminJoin')
def on_admin_join():
    sid = request.sid; admin_sids.add(sid); join_room("admin_room") # Use admin_room
    print(f"Admin joined room 'admin_room': {sid}. Total admins: {len(admin_sids)}")
    current_student_list = list(connected_students.values())
    print(f"DEBUG [Admin Join]: Sending student_list ({len(current_student_list)} students) to {sid}")
    emit("student_list", current_student_list, to=sid)


@socketio.on('adminKickStudent')
def on_admin_kick(data):
    student_id = data.get("student_id"); print(f"INFO [Kick]: Admin requested kick for {student_id}")
    student_data = connected_students.get(student_id)
    if student_data and student_data.get("sid"):
        student_sid = student_data["sid"]; print(f"INFO [Kick]: Sending 'kick' to {student_id} (SID: {student_sid})")
        emit("kick", {"reason": "Kicked by administrator."}, to=student_sid)
        emit_alert_to_admin(student_id, "Manually kicked by admin.", color="#6c757d")
    else: print(f"WARN [Kick]: Cannot kick {student_id}, not found or no SID.")


@socketio.on('adminFalseAlarm')
def on_admin_false_alarm(data):
    student_id = data.get("student_id"); print(f"DEBUG [False Alarm]: Received for {student_id}")
    student_data = connected_students.get(student_id)
    if student_data and "Multiple Faces" in student_data.get("status", ""):
        print(f"DEBUG [False Alarm]: Resetting status for {student_id}."); student_data["status"] = "Focused"
        emit_student_update(student_id); emit_alert_to_admin(student_id, "Admin marked 'Multiple Face' as false alarm.", color="#17a2b8")
    else: print(f"DEBUG [False Alarm]: Ignoring for {student_id}, status not 'Multiple Faces'.")


@socketio.on('studentJoin')
def on_student_join(data):
    sid = request.sid; student_id = data.get("studentId")
    if not student_id: print(f"WARN [Student Join]: Failed - no studentId. SID: {sid}"); return
    if student_id in connected_students: print(f"WARN [Student Join]: {student_id} already joined?"); return

    print(f"Student joined: {student_id} (SID: {sid})")
    connected_students[student_id] = {
        "id": student_id, "sid": sid, "score": 100, "status": "Connected", "snapshot": None,
        "wallpaperB64": None, # Will be set by the first video frame
        "wallpaperPath": None, # Will be set when wallpaper is saved
        "warnings": 0, "looking_away_start_time": None, "looking_away_alerted": False
    }
    sid_to_student[sid] = student_id
    if admin_sids: print(f"DEBUG [Student Join]: Emitting new_student for {student_id}"); socketio.emit("new_student", connected_students[student_id], room="admin_room")
    if exam_questions: emit('receiveExam', {"questions": exam_questions}, room=sid)

# --- 'setReferenceImage' handler REMOVED ---

@socketio.on('video_frame')
def on_video_frame(data):
    sid = request.sid
    student_id = sid_to_student.get(sid)
    if not student_id or student_id not in connected_students: return

    frame_b64 = data.get("frame")
    snapshot_b64 = data.get("snapshot") or frame_b64

    if not frame_b64: return

    student_data = connected_students[student_id]
    student_data["snapshot"] = snapshot_b64
    wallpaper_path = student_data.get("wallpaperPath")
    wallpaper_just_set = False

    # --- Save Wallpaper Image (if not already done) ---
    if not wallpaper_path and frame_b64:
        try:
            img_cv2 = b64_to_cv2_image(frame_b64)
            if img_cv2 is not None:
                safe_student_id = "".join(c for c in student_id if c.isalnum() or c in ('-', '_', '.')).rstrip()
                filename = f"wallpaper_{safe_student_id}.jpg"
                save_path = os.path.join(REFERENCE_IMAGES_DIR, filename)

                cv2.imwrite(save_path, img_cv2)
                print(f"INFO [{student_id}]: Saved wallpaper image to: {save_path}")

                student_data['wallpaperPath'] = save_path
                student_data['wallpaperB64'] = frame_b64
                wallpaper_path = save_path
                wallpaper_just_set = True
            else:
                print(f"WARN [{student_id}]: Failed to decode frame for wallpaper saving.")
        except Exception as e:
            print(f"ERROR [{student_id}]: Failed to save wallpaper image: {e}")

    # --- Image Analysis ---
    frame_cv2_analysis = b64_to_cv2_image(frame_b64)
    if frame_cv2_analysis is None: print(f"ERROR [Video]: Failed decode for analysis {student_id}."); return

    reference_path_for_analysis = wallpaper_path or STATIC_REFERENCE_IMAGE_PATH

    focus_analysis = None; phone_analysis = None; analysis_error = False
    try: focus_analysis = video_analysis.analyze_frame(frame_cv2_analysis, student_id, reference_path_for_analysis)
    except Exception as e: print(f"ERROR [Focus Analysis]: {e}"); focus_analysis = {"status": "ERROR: Focus Failed", "alert": f"Focus error: {e}", "score_penalty": 10}; analysis_error = True
    try: phone_analysis = phone_detection.analyze_phone_frame(frame_cv2_analysis, student_id)
    except Exception as e: print(f"ERROR [Phone Analysis]: {e}"); phone_analysis = {"status": "ERROR: Phone Failed", "alert": f"Phone error: {e}", "score_penalty": 10}; analysis_error = True

    # Combine results
    analysis = focus_analysis if focus_analysis else {}
    if phone_analysis and phone_analysis.get("status") == "CRITICAL: Phone Detected": analysis = phone_analysis
    elif focus_analysis and "CRITICAL" in focus_analysis.get("status", ""): analysis = focus_analysis
    elif analysis_error and not analysis.get("status"):
        if phone_analysis: analysis = phone_analysis
        else: analysis = {"status": "Backend Error", "alert": (focus_analysis.get("alert") or "") + (phone_analysis.get("alert") or ""), "score_penalty": (focus_analysis.get("score_penalty",0))+(phone_analysis.get("score_penalty",0))}
    elif focus_analysis and focus_analysis.get("status") == "Away": analysis = focus_analysis
    elif focus_analysis and focus_analysis.get("status") == "Looking Away": analysis = focus_analysis
    elif phone_analysis and phone_analysis.get("status") == "Phone Detected (Pending)": analysis = phone_analysis

    # --- Score, Status, Alert, Timer Logic ---
    previous_status = student_data["status"]
    student_data["status"] = analysis.get("status", previous_status)
    score_updated = False
    status_changed = (previous_status != student_data["status"])
    alert_triggered_this_frame = False

    # Looking Away Timer
    is_looking_away = (analysis.get("status") == "Looking Away")
    looking_away_start_time = student_data.get("looking_away_start_time")
    if is_looking_away:
        if looking_away_start_time is None: student_data["looking_away_start_time"] = time.time(); student_data["looking_away_alerted"] = False; print(f"DEBUG [Video]: {student_id} timer started (Looking Away).")
        else:
             elapsed = time.time() - looking_away_start_time
             if elapsed > 2.0 and not student_data.get("looking_away_alerted"):
                  print(f"DEBUG [Video]: {student_id} exceeded 2.0s threshold.")
                  current_score = student_data["score"]; penalty = analysis.get("score_penalty", 0)
                  new_score = max(0, current_score - penalty)
                  if new_score != current_score: student_data["score"] = new_score; score_updated = True
                  student_data["warnings"] += 1; student_data["looking_away_alerted"] = True; alert_triggered_this_frame = True
                  emit_alert_to_admin(student_id, analysis.get("alert", "Looking away threshold exceeded"), color="#ffc107", snapshot=snapshot_b64)
    else: # Not "Looking Away"
        if looking_away_start_time is not None: print(f"DEBUG [Video]: {student_id} timer reset.")
        student_data["looking_away_start_time"] = None; student_data["looking_away_alerted"] = False

    # Handle OTHER alerts
    alert_message = analysis.get("alert")
    if alert_message and  not alert_triggered_this_frame:
        current_score = student_data["score"]; penalty = analysis.get("score_penalty", 0)
        new_score = max(0, current_score - penalty)
        if new_score != current_score: student_data["score"] = new_score; score_updated = True
        if "Identity Verified" not in alert_message: student_data["warnings"] += 1
        alert_color = "#dc3545" if "CRITICAL" in analysis.get("status", "") else "#ffc107"
        if "Identity Verified" in alert_message: alert_color = "#28a745"
        alert_triggered_this_frame = True
        emit_alert_to_admin(student_id, alert_message, color=alert_color, snapshot=snapshot_b64)

    # --- Emit Update ---
    if wallpaper_just_set or score_updated or status_changed:
        emit_student_update(student_id)


@socketio.on('audio_chunk')
def on_audio_chunk(data):
    sid = request.sid; student_id = sid_to_student.get(sid);
    if not student_id: return
    audio_b64 = data.get("audio"); snapshot_b64 = data.get("snapshot")
    if not audio_b64: return
    thread = threading.Thread(target=handle_audio_analysis, args=(student_id, audio_b64, snapshot_b64), daemon=True)
    thread.start()

def process_audio_chunk_wrapper(student_id, base64_audio):
    # This function now correctly handles ffmpeg and calls voice_recognition helpers
    print(f"[{student_id}] Processing audio chunk...")
    temp_wav_path = None; analysis = {"score": 0, "risk": "low", "text": "", "keywords": []}
    webm_path = None # Define outside try
    try:
        audio_data = base64.b64decode(base64_audio)
        # Save temp webm
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False, prefix=f"{student_id}_aud_") as webm_file:
            webm_path = webm_file.name
            webm_file.write(audio_data)

        # Convert to wav
        temp_wav_path = webm_path.replace(".webm", ".wav")
        command = ['ffmpeg', '-i', webm_path, '-ac', '1', '-ar', '16000', temp_wav_path, '-y'] # Force mono, 16kHz
        print(f"[{student_id}] Running ffmpeg: {' '.join(command)}")
        result = subprocess.run(command, timeout=10, check=True, capture_output=True, text=True)
        print(f"[{student_id}] ffmpeg successful.")

        # Transcribe wav
        text = transcribe_fast(temp_wav_path) # From voice_recognition.py
        if text:
            print(f"[{student_id}] Transcription: '{text}'")
            analysis = analyze_fast(text) # From voice_recognition.py
            analysis['text'] = text
            if analysis.get('risk') in ['high', 'critical']:
                return analysis, temp_wav_path # Keep wav path if risky
        else:
             print(f"[{student_id}] Transcription resulted in empty text.")
        # If not risky or no text, return None for path (will be deleted)
        return analysis, None
    except subprocess.TimeoutExpired:
        print(f"[{student_id}] ERROR: ffmpeg command timed out.")
        analysis['text'] = "Audio processing timeout"; analysis['risk'] = 'error'
        return analysis, None
    except FileNotFoundError:
        print(f"[{student_id}] CRITICAL ERROR: 'ffmpeg' command not found. Install ffmpeg and add to PATH.")
        analysis['text'] = "Backend Error: ffmpeg not found"; analysis['risk'] = 'error'
        return analysis, None
    except subprocess.CalledProcessError as e:
        print(f"[{student_id}] ERROR: ffmpeg failed: {e.stderr}")
        analysis['text'] = f"Audio conversion error: {e.stderr[:100]}..."; analysis['risk'] = 'error'
        return analysis, None
    except Exception as e:
        print(f"[{student_id}] ERROR processing audio chunk: {e}")
        analysis['text'] = f"Audio Error: {e}"; analysis['risk'] = 'error'
        return analysis, None
    finally:
        # Clean up temp webm file
        if webm_path and os.path.exists(webm_path):
            try: os.remove(webm_path)
            except Exception as e: print(f"WARN: Failed to delete temp webm {webm_path}: {e}")
        # Temp wav deletion is handled based on return value in handle_audio_analysis


def handle_audio_analysis(student_id, base64_audio, snapshot_b64):
    analysis, wav_file_path_to_save = process_audio_chunk_wrapper(student_id, base64_audio)
    saved_audio_filename = None
    if wav_file_path_to_save:
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S"); safe_id = "".join(c for c in student_id if c.isalnum() or c in ('-', '_')).rstrip(); score = analysis.get('score', 0)
            new_filename = f"{safe_id}_{timestamp}_risk{score}.wav"; destination_path = os.path.join(SUSPICIOUS_AUDIO_DIR, new_filename)
            shutil.move(wav_file_path_to_save, destination_path); saved_audio_filename = new_filename
            print(f"[{student_id}] Saved suspicious audio: {saved_audio_filename}")
        except Exception as e: print(f"[{student_id}] Error saving audio {wav_file_path_to_save}: {e}");
        if os.path.exists(wav_file_path_to_save): os.remove(wav_file_path_to_save); wav_file_path_to_save = None

    risk_level = analysis.get('risk', 'low'); text = analysis.get('text', '')
    if risk_level in ["high", "critical", "error"]:
        print(f"[{student_id}] !!! AUDIO ALERT !!! (Risk: {risk_level})")
        alert_color = '#dc3545' if risk_level == 'critical' or risk_level == 'error' else '#ffc107'
        emit_alert_to_admin(student_id, f"(Audio) \"{text}\"", color=alert_color, snapshot=snapshot_b64, audio_filename=saved_audio_filename)
        if student_id in connected_students:
             current_score = connected_students[student_id]['score']; penalty = analysis.get('score', 10 if risk_level=='error' else 0)
             new_score = max(0, current_score - penalty)
             if new_score != current_score: connected_students[student_id]['score'] = new_score; connected_students[student_id]['warnings'] += 1; emit_student_update(student_id)
    else: print(f"[{student_id}] Audio analysis complete (Low risk).")
    # Clean up temp wav if it wasn't saved
    if wav_file_path_to_save and os.path.exists(wav_file_path_to_save):
         try: os.remove(wav_file_path_to_save)
         except Exception as e: print(f"WARN: Failed to delete temp wav {wav_file_path_to_save}: {e}")


# --- Flask Route to Serve Audio Files ---
@app.route('/audio/<path:filename>')
def serve_audio(filename):
    print(f"Serving audio file: {filename}"); 
    try:
        if '..' in filename or filename.startswith('/'): return "Invalid filename", 400
        response = send_from_directory(SUSPICIOUS_AUDIO_DIR, filename, as_attachment=False)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"; response.headers["Pragma"] = "no-cache"; response.headers["Expires"] = "0"; return response
    except FileNotFoundError: return "File not found", 404
    except Exception as e: print(f"Error serving {filename}: {e}"); return "Server error", 500

# --- Main Execution ---
if __name__ == '__main__':
    print(f"Flask-SocketIO server starting on http://localhost:8000")
    print(f"Static reference image path (fallback): {STATIC_REFERENCE_IMAGE_PATH}")
    print(f"Dynamic reference images will be saved to: {REFERENCE_IMAGES_DIR}")
    print(f"Suspicious audio directory: {SUSPICIOUS_AUDIO_DIR}")
    try: socketio.run(app, host='0.0.0.0', port=8000, debug=False, use_reloader=False)
    except KeyboardInterrupt: print("Server shutting down.")
    except Exception as e: print(f"Failed to start server: {e}")