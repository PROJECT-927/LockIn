from flask import Flask, jsonify, send_from_directory
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
import datetime
import os
import speech_recognition as sr
import time
import shutil
import json
import glob
from queue import Queue, Empty
from scipy import signal

# ---------------- CONFIG ----------------
SAMPLE_RATE = 16000
DURATION = 5  # seconds per chunk
ENERGY_THRESHOLD = 0.015  # RMS energy threshold
ZCR_THRESHOLD = 0.1  # Zero-crossing rate threshold
SPEECH_THRESHOLD = 0.3  # Combined speech detection threshold
SUSPICIOUS_KEYWORDS = {
    "answer", "question", "say", "tell", "option", "help", 
    "search", "google", "calculate", "cheating", "exam"
}

SAVE_PATH = os.path.abspath("suspicious_audio")
TEMP_DIR = os.path.abspath("temp")
LOG_FILE = "voice_log.json"
MAX_LOG_ENTRIES = 100
CLEANUP_HOURS = 2

# Global state
start_time = time.time()
last_cleanup_time = None

os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ---------------- INITIALIZATION ----------------
app = Flask(__name__)
recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

audio_queue = Queue(maxsize=10)
log_buffer = []
log_lock = threading.Lock()
is_running = threading.Event()
is_running.set()

# ---------------- UTILITIES ----------------
def log_event(event_type, text="", filename=None):
    """Thread-safe logging with rotation"""
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "text": text,
        "file": filename,
    }
    with log_lock:
        log_buffer.append(entry)
        if len(log_buffer) > MAX_LOG_ENTRIES:
            log_buffer.pop(0)
        try:
            with open(LOG_FILE, "w") as f:
                json.dump(log_buffer, f, indent=2)
        except Exception as e:
            print(f"Error writing log file: {e}")

def cleanup_old_files(hours=CLEANUP_HOURS):
    """Remove old audio files"""
    global last_cleanup_time
    now = time.time()
    cleaned = 0
    try:
        for f in glob.glob(os.path.join(SAVE_PATH, "*.wav")):
            if os.stat(f).st_mtime < now - hours * 3600:
                os.remove(f)
                cleaned += 1
        last_cleanup_time = datetime.datetime.now()
        if cleaned > 0:
            log_event("cleanup", f"Removed {cleaned} old files")
    except Exception as e:
        log_event("error", f"Cleanup error: {str(e)}")
    return cleaned

def get_input_device():
    """Find a suitable input device"""
    try:
        devices = sd.query_devices()
        default_input = sd.default.device[0]
        if default_input is not None:
            return default_input
        
        # Fallback: find any input device
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                return i
        raise RuntimeError("No input device found")
    except Exception as e:
        log_event("error", f"Device detection error: {e}")
        raise

# ---------------- VOICE ACTIVITY DETECTION ----------------
def calculate_energy(audio):
    """Calculate RMS energy of audio"""
    if audio is None or len(audio) == 0:
        return 0
    return np.sqrt(np.mean(audio**2))

def calculate_zcr(audio):
    """Calculate zero-crossing rate"""
    if audio is None or len(audio) < 2:
        return 0
    signs = np.sign(audio)
    signs[signs == 0] = -1  # Treat zeros as negative
    zero_crossings = np.sum(np.abs(np.diff(signs))) / 2
    return zero_crossings / len(audio)

def calculate_spectral_centroid(audio, sr=SAMPLE_RATE):
    """Calculate spectral centroid (measure of brightness)"""
    if audio is None or len(audio) == 0:
        return 0
    
    # Apply window function
    windowed = audio * np.hamming(len(audio))
    
    # Compute FFT
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(windowed), 1/sr)
    
    # Calculate centroid
    if np.sum(spectrum) == 0:
        return 0
    centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
    return centroid

def has_speech(audio):
    """
    Advanced VAD using multiple features:
    - Energy (RMS)
    - Zero-crossing rate
    - Spectral centroid
    """
    if audio is None or len(audio) == 0:
        return False
    
    try:
        # Calculate features
        energy = calculate_energy(audio)
        zcr = calculate_zcr(audio)
        centroid = calculate_spectral_centroid(audio)
        
        # Speech typically has:
        # - Higher energy than silence
        # - Moderate ZCR (not too high like noise, not too low like silence)
        # - Spectral centroid in speech range (roughly 500-3000 Hz)
        
        energy_score = 1.0 if energy > ENERGY_THRESHOLD else 0.0
        zcr_score = 1.0 if 0.02 < zcr < 0.3 else 0.0
        centroid_score = 1.0 if 300 < centroid < 4000 else 0.0
        
        # Weighted combination
        speech_score = (energy_score * 0.5 + zcr_score * 0.3 + centroid_score * 0.2)
        
        return speech_score > SPEECH_THRESHOLD
        
    except Exception as e:
        log_event("error", f"VAD error: {e}")
        return False

def apply_bandpass_filter(audio, lowcut=300, highcut=3400, sr=SAMPLE_RATE, order=5):
    """Apply bandpass filter to focus on speech frequencies"""
    nyquist = sr / 2
    low = lowcut / nyquist
    high = highcut / nyquist
    
    try:
        b, a = signal.butter(order, [low, high], btype='band')
        filtered = signal.filtfilt(b, a, audio)
        return filtered
    except:
        return audio

# ---------------- CORE FUNCTIONS ----------------
def record_chunk():
    """Record a short chunk of audio"""
    try:
        device = get_input_device()
        device_info = sd.query_devices(device)
        
        audio = sd.rec(
            int(DURATION * SAMPLE_RATE), 
            samplerate=SAMPLE_RATE,
            channels=1, 
            dtype='float32', 
            device=device
        )
        sd.wait()
        
        # Apply bandpass filter to improve speech detection
        audio = np.squeeze(audio)
        audio = apply_bandpass_filter(audio)
        
        return audio
    except Exception as e:
        log_event("error", f"Recording failed: {e}")
        return None

def save_audio(audio, label):
    """Save audio to file with timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{label}_{timestamp}.wav"
    filepath = os.path.join(SAVE_PATH, filename)
    try:
        sf.write(filepath, audio, SAMPLE_RATE)
        return filepath, filename
    except Exception as e:
        log_event("error", f"Save error: {e}")
        return None, None

def transcribe_audio(filepath):
    """Use Google Speech Recognition"""
    try:
        with sr.AudioFile(filepath) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='en-US').lower()
            return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        log_event("warning", f"Google API error: {e}")
        return ""
    except Exception as e:
        log_event("error", f"Transcription error: {e}")
        return ""

# ---------------- BACKGROUND THREADS ----------------
def recorder_thread():
    """Continuously records audio chunks"""
    print(" Recorder thread started")
    consecutive_errors = 0
    max_errors = 5
    
    while is_running.is_set():
        try:
            audio_chunk = record_chunk()
            
            if audio_chunk is None:
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    log_event("error", "Too many recording errors, stopping recorder")
                    break
                time.sleep(1)
                continue
            
            consecutive_errors = 0
            
            energy = calculate_energy(audio_chunk)
            if energy > ENERGY_THRESHOLD:
                try:
                    audio_queue.put(audio_chunk, timeout=1)
                except:
                    log_event("warning", "Audio queue full, dropping chunk")
                    
        except Exception as e:
            log_event("error", f"Recorder thread error: {str(e)}")
            consecutive_errors += 1
            if consecutive_errors >= max_errors:
                break
            time.sleep(1)
    
    print(" Recorder thread stopped")

def processor_thread():
    """Processes recorded chunks"""
    print(" Processor thread started")
    last_cleanup = time.time()
    cleanup_interval = 300  # 5 minutes
    
    while is_running.is_set():
        try:
            # Periodic cleanup
            if time.time() - last_cleanup > cleanup_interval:
                cleanup_old_files()
                last_cleanup = time.time()
            
            # Get audio from queue
            try:
                audio_chunk = audio_queue.get(timeout=1)
            except Empty:
                continue
            
            # Step 1: Voice Activity Detection
            if not has_speech(audio_chunk):
                print(" Silence or background noise")
                continue
            
            # Step 2: Save temporary file
            temp_file = os.path.join(TEMP_DIR, f"temp_{threading.get_ident()}.wav")
            try:
                sf.write(temp_file, audio_chunk, SAMPLE_RATE)
            except Exception as e:
                log_event("error", f"Failed to write temp file: {e}")
                continue
            
            # Step 3: Speech recognition
            text = transcribe_audio(temp_file)
            
            # Cleanup temp file
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
            
            # Step 4: Log results
            if text == "":
                print(" Speech detected (unclear)")
                log_event("speech", "unclear speech detected")
            else:
                print(f" Speech: {text}")
                log_event("speech", text)
                
                # Step 5: Suspicious detection
                word_count = len(text.split())
                has_keywords = any(keyword in text for keyword in SUSPICIOUS_KEYWORDS)
                
                is_suspicious = word_count > 5 or has_keywords
                
                if is_suspicious:
                    filepath, filename = save_audio(audio_chunk, "suspicious_talk")
                    if filename:
                        reason = []
                        if word_count > 5:
                            reason.append(f"{word_count} words")
                        if has_keywords:
                            found = [k for k in SUSPICIOUS_KEYWORDS if k in text]
                            reason.append(f"keywords: {', '.join(found)}")
                        
                        log_event("suspicious", text, filename)
                        print(f" Suspicious talk: {filename} ({'; '.join(reason)})")
                    
        except Exception as e:
            log_event("error", f"Processor thread error: {str(e)}")
            time.sleep(1)
    
    print(" Processor thread stopped")

# ---------------- FLASK ROUTES ----------------
@app.route("/")
def home():
    return jsonify({
        "message": "Voice Proctor API running",
        "status": "active" if is_running.is_set() else "stopped",
        "version": "2.2",
        "features": ["speech_detection", "keyword_monitoring", "auto_cleanup"]
    })

@app.route("/logs")
def get_logs():
    """Get all logs"""
    with log_lock:
        return jsonify({
            "logs": log_buffer,
            "count": len(log_buffer)
        })

@app.route("/logs/<log_type>")
def get_logs_by_type(log_type):
    """Get filtered logs by type"""
    with log_lock:
        filtered = [log for log in log_buffer if log['type'] == log_type]
        return jsonify({
            "logs": filtered,
            "count": len(filtered),
            "type": log_type
        })

@app.route("/audio/<path:filename>")
def get_audio(filename):
    """Download audio file"""
    safe_path = os.path.join(SAVE_PATH, os.path.basename(filename))
    if not os.path.exists(safe_path):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(SAVE_PATH, os.path.basename(filename))

@app.route("/status")
def status():
    """Get system status"""
    try:
        saved_files = [f for f in os.listdir(SAVE_PATH) if f.endswith('.wav')]
        uptime = int(time.time() - start_time)
        
        return jsonify({
            "active": is_running.is_set(),
            "queue_size": audio_queue.qsize(),
            "saved_files": len(saved_files),
            "uptime_seconds": uptime,
            "uptime_formatted": str(datetime.timedelta(seconds=uptime)),
            "last_cleanup": last_cleanup_time.strftime("%Y-%m-%d %H:%M:%S") if last_cleanup_time else "Never",
            "log_entries": len(log_buffer)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/control/<action>", methods=['POST'])
def control(action):
    """Control system (start/stop/cleanup)"""
    if action == "stop":
        is_running.clear()
        log_event("system", "System stopped via API")
        return jsonify({"status": "stopping"})
    elif action == "start":
        if not is_running.is_set():
            is_running.set()
            log_event("system", "System started via API")
            return jsonify({"status": "starting"})
        return jsonify({"status": "already running"})
    elif action == "cleanup":
        cleaned = cleanup_old_files(0)
        return jsonify({"status": "cleanup complete", "files_removed": cleaned})
    return jsonify({"error": "Invalid action. Use: stop, start, or cleanup"}), 400

@app.route("/files")
def list_files():
    """List all saved audio files"""
    try:
        files = []
        for f in sorted(os.listdir(SAVE_PATH), reverse=True):
            if f.endswith('.wav'):
                filepath = os.path.join(SAVE_PATH, f)
                stat = os.stat(filepath)
                files.append({
                    "filename": f,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        return jsonify({"files": files, "count": len(files)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats")
def stats():
    """Get statistics"""
    with log_lock:
        speech_count = len([l for l in log_buffer if l['type'] == 'speech'])
        suspicious_count = len([l for l in log_buffer if l['type'] == 'suspicious'])
        error_count = len([l for l in log_buffer if l['type'] == 'error'])
        
        return jsonify({
            "total_logs": len(log_buffer),
            "speech_detected": speech_count,
            "suspicious_events": suspicious_count,
            "errors": error_count,
            "uptime_hours": round((time.time() - start_time) / 3600, 2)
        })

# ---------------- ENTRY POINT ----------------
if __name__ == "__main__":
    print(" Starting Voice Proctor System.\n")
    
    # Clean temp directory
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Load existing logs
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                log_buffer = json.load(f)
                print(f" Loaded {len(log_buffer)} existing log entries")
        except:
            print(" Starting with fresh logs")
    
    log_event("system", "Voice Proctor System starting")

    # Start background threads
    recording_thread = threading.Thread(target=recorder_thread, daemon=True)
    processing_thread = threading.Thread(target=processor_thread, daemon=True)
    
    try:
        recording_thread.start()
        processing_thread.start()
        # Start Flask API
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n Received shutdown signal")
    except Exception as e:
        print(f" Error starting system: {e}")
        log_event("error", f"System startup failed: {e}")
    finally:
        print("\n Shutting down Voice Proctor System...")
        is_running.clear()
        time.sleep(2)
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        log_event("system", "Voice Proctor System stopped")
        print(" Shutdown complete")