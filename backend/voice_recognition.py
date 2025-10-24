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
from collections import defaultdict
import re

# ---------------- CONFIG ----------------
SAMPLE_RATE = 16000
DURATION = 5  # seconds per chunk
ENERGY_THRESHOLD = 0.015  # RMS energy threshold
ZCR_THRESHOLD = 0.1  # Zero-crossing rate threshold
SPEECH_THRESHOLD = 0.3  # Combined speech detection threshold

# Enhanced keyword categories
SUSPICIOUS_KEYWORDS = {
    "exam_related": ["answer", "question", "test", "exam", "quiz"],
    "seeking_help": ["help", "tell", "say", "what is", "how do"],
    "cheating_tools": ["search", "google", "calculator", "phone", "assistant", "alexa", "siri"],
    "collaboration": ["you", "your", "give me", "send", "share"],
    "academic_terms": ["option", "choice", "select", "calculate", "solve"]
}

# Suspicious patterns (regex)
SUSPICIOUS_PATTERNS = [
    r"what\s+is\s+the\s+answer",
    r"question\s+number\s+\d+",
    r"option\s+[a-d]",
    r"help\s+me\s+with",
    r"tell\s+me\s+the",
    r"search\s+for",
]

SAVE_PATH = os.path.abspath("suspicious_audio")
TEMP_DIR = os.path.abspath("temp")
LOG_FILE = "voice_log.json"
MAX_LOG_ENTRIES = 200
CLEANUP_HOURS = 2

# Conversation tracking
CONVERSATION_WINDOW = 30  # seconds
MIN_CONVERSATION_EXCHANGES = 3

# Global state
start_time = time.time()
last_cleanup_time = None
speech_history = []  # Track recent speech for conversation detection
alert_counts = defaultdict(int)

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
def convert_to_serializable(obj):
    """Convert objects to JSON serializable format"""
    if isinstance(obj, (bool, int, float, str, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.number):
        return obj.item()
    else:
        return str(obj)

def log_event(event_type, text="", filename=None, severity="normal", metadata=None):
    """Thread-safe logging with rotation and severity levels"""
    try:
        # Convert metadata to serializable format
        serializable_metadata = convert_to_serializable(metadata) if metadata else {}
        
        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": event_type,
            "text": text,
            "file": filename,
            "severity": severity,  # normal, warning, critical
            "metadata": serializable_metadata
        }
        
        with log_lock:
            log_buffer.append(entry)
            if len(log_buffer) > MAX_LOG_ENTRIES:
                log_buffer.pop(0)
            try:
                with open(LOG_FILE, "w") as f:
                    json.dump(log_buffer, f, indent=2, default=str)
            except Exception as e:
                print(f"Error writing log file: {e}")
    except Exception as e:
        print(f"Error creating log entry: {e}")

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
    signs[signs == 0] = -1
    zero_crossings = np.sum(np.abs(np.diff(signs))) / 2
    return zero_crossings / len(audio)

def calculate_spectral_centroid(audio, sr=SAMPLE_RATE):
    """Calculate spectral centroid"""
    if audio is None or len(audio) == 0:
        return 0
    
    windowed = audio * np.hamming(len(audio))
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(windowed), 1/sr)
    
    if np.sum(spectrum) == 0:
        return 0
    centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
    return centroid

def has_speech(audio):
    """Advanced VAD using multiple features"""
    if audio is None or len(audio) == 0:
        return False
    
    try:
        energy = calculate_energy(audio)
        zcr = calculate_zcr(audio)
        centroid = calculate_spectral_centroid(audio)
        
        energy_score = 1.0 if energy > ENERGY_THRESHOLD else 0.0
        zcr_score = 1.0 if 0.02 < zcr < 0.3 else 0.0
        centroid_score = 1.0 if 300 < centroid < 4000 else 0.0
        
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

# ---------------- ENHANCED DETECTION ----------------
def analyze_text_suspicion(text):
    """Comprehensive text analysis for suspicious content"""
    suspicion_score = 0
    detected_categories = []
    detected_patterns = []
    reasons = []
    
    text_lower = text.lower()
    
    # 1. Keyword category matching
    for category, keywords in SUSPICIOUS_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in text_lower]
        if matches:
            suspicion_score += len(matches) * 2
            detected_categories.append(category)
            reasons.append(f"{category}: {', '.join(matches)}")
    
    # 2. Pattern matching
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text_lower):
            suspicion_score += 5
            detected_patterns.append(pattern)
            reasons.append(f"Pattern match: {pattern}")
    
    # 3. Question indicators
    question_words = ["what", "how", "why", "when", "where", "which", "who"]
    question_count = sum(1 for qw in question_words if qw in text_lower.split())
    if question_count >= 2:
        suspicion_score += question_count * 2
        reasons.append(f"{question_count} question words")
    
    # 4. Length-based suspicion
    word_count = len(text.split())
    if word_count > 10:
        suspicion_score += (word_count - 10) * 0.5
        reasons.append(f"{word_count} words (lengthy)")
    
    # 5. Imperative statements (commands)
    imperative_verbs = ["tell", "give", "show", "find", "search", "help", "send"]
    imperatives = [verb for verb in imperative_verbs if text_lower.startswith(verb)]
    if imperatives:
        suspicion_score += 3
        reasons.append(f"Imperative: {', '.join(imperatives)}")
    
    return {
        "score": suspicion_score,
        "categories": detected_categories,
        "patterns": detected_patterns,
        "reasons": reasons,
        "is_suspicious": suspicion_score >= 5
    }

def detect_conversation_pattern():
    """Detect if there's an ongoing conversation (multiple exchanges)"""
    global speech_history
    current_time = time.time()
    
    # Clean old entries
    speech_history = [
        entry for entry in speech_history 
        if current_time - entry['time'] < CONVERSATION_WINDOW
    ]
    
    if len(speech_history) >= MIN_CONVERSATION_EXCHANGES:
        return True, len(speech_history)
    return False, len(speech_history)

def estimate_pitch(audio, sr=SAMPLE_RATE):
    """Basic pitch estimation using autocorrelation"""
    try:
        # Autocorrelation method
        correlation = np.correlate(audio, audio, mode='full')
        correlation = correlation[len(correlation)//2:]
        
        # Find peaks
        diff = np.diff(correlation)
        start = np.where(diff > 0)[0]
        if len(start) == 0:
            return 0
        
        peak = np.argmax(correlation[start[0]:]) + start[0]
        return sr / peak if peak > 0 else 0
    except:
        return 0

def analyze_audio_characteristics(audio):
    """Extract audio features that might indicate multiple speakers"""
    try:
        # Calculate pitch
        pitch = estimate_pitch(audio)
        
        # Calculate energy variation (speaking patterns)
        window_size = int(0.5 * SAMPLE_RATE)
        energies = []
        for i in range(0, len(audio) - window_size, window_size // 2):
            window = audio[i:i + window_size]
            energies.append(calculate_energy(window))
        
        energy_std = np.std(energies) if len(energies) > 1 else 0
        
        return {
            "pitch": pitch,
            "energy_variation": energy_std,
            "high_variation": energy_std > 0.02  # Might indicate turn-taking
        }
    except:
        return {"pitch": 0, "energy_variation": 0, "high_variation": False}

# ---------------- CORE FUNCTIONS ----------------
def record_chunk():
    """Record a short chunk of audio"""
    try:
        device = get_input_device()
        
        audio = sd.rec(
            int(DURATION * SAMPLE_RATE), 
            samplerate=SAMPLE_RATE,
            channels=1, 
            dtype='float32', 
            device=device
        )
        sd.wait()
        
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
    print("🎙️  Recorder thread started")
    consecutive_errors = 0
    max_errors = 5
    
    while is_running.is_set():
        try:
            audio_chunk = record_chunk()
            
            if audio_chunk is None:
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    log_event("error", "Too many recording errors, stopping recorder", severity="critical")
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
    
    print("🛑 Recorder thread stopped")

def processor_thread():
    """Processes recorded chunks"""
    print("⚙️  Processor thread started")
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
                continue
            
            # Step 2: Analyze audio characteristics
            audio_features = analyze_audio_characteristics(audio_chunk)
            
            # Step 3: Save temporary file
            temp_file = os.path.join(TEMP_DIR, f"temp_{threading.get_ident()}.wav")
            try:
                sf.write(temp_file, audio_chunk, SAMPLE_RATE)
            except Exception as e:
                log_event("error", f"Failed to write temp file: {e}")
                continue
            
            # Step 4: Speech recognition
            text = transcribe_audio(temp_file)
            
            # Cleanup temp file
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
            
            # Step 5: Process transcription
            current_time = time.time()
            
            if text == "":
                print("👂 Speech detected (unclear)")
                log_event("speech", "unclear speech detected", metadata=audio_features)
            else:
                print(f"💬 Speech: {text}")
                
                # Add to conversation history
                speech_history.append({
                    "time": current_time,
                    "text": text,
                    "audio_features": audio_features
                })
                
                # Analyze suspicion
                analysis = analyze_text_suspicion(text)
                is_conversation, exchange_count = detect_conversation_pattern()
                
                # Determine severity
                severity = "normal"
                if analysis["is_suspicious"]:
                    severity = "warning"
                if is_conversation and analysis["is_suspicious"]:
                    severity = "critical"
                
                # Log with metadata
                metadata = {
                    "suspicion_score": analysis["score"],
                    "categories": analysis["categories"],
                    "audio_features": audio_features,
                    "conversation_detected": is_conversation,
                    "exchange_count": exchange_count
                }
                
                log_event("speech", text, metadata=metadata, severity=severity)
                
                # Step 6: Save suspicious audio
                if analysis["is_suspicious"] or is_conversation:
                    label = "critical_conversation" if severity == "critical" else "suspicious_talk"
                    filepath, filename = save_audio(audio_chunk, label)
                    
                    if filename:
                        reason_text = "; ".join(analysis["reasons"])
                        if is_conversation:
                            reason_text += f"; Conversation ({exchange_count} exchanges)"
                        
                        log_event(
                            "suspicious", 
                            text, 
                            filename,
                            severity=severity,
                            metadata={
                                "analysis": analysis,
                                "conversation": is_conversation,
                                "exchange_count": exchange_count
                            }
                        )
                        
                        alert_counts[severity] += 1
                        print(f"🚨 {severity.upper()}: {filename}")
                        print(f"   Reason: {reason_text}")
                    
        except Exception as e:
            log_event("error", f"Processor thread error: {str(e)}")
            time.sleep(1)
    
    print("🛑 Processor thread stopped")

# ---------------- FLASK ROUTES ----------------
@app.route("/")
def home():
    return jsonify({
        "message": "Voice Proctor API running",
        "status": "active" if is_running.is_set() else "stopped",
        "version": "3.0",
        "features": [
            "advanced_speech_detection",
            "multi_category_keywords",
            "pattern_matching",
            "conversation_detection",
            "severity_levels",
            "audio_analysis"
        ]
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

@app.route("/logs/severity/<severity_level>")
def get_logs_by_severity(severity_level):
    """Get logs by severity level"""
    with log_lock:
        filtered = [log for log in log_buffer if log.get('severity') == severity_level]
        return jsonify({
            "logs": filtered,
            "count": len(filtered),
            "severity": severity_level
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
            "log_entries": len(log_buffer),
            "recent_speech_count": len(speech_history),
            "alert_counts": dict(alert_counts)
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
    elif action == "reset_alerts":
        alert_counts.clear()
        speech_history.clear()
        return jsonify({"status": "alerts reset"})
    return jsonify({"error": "Invalid action. Use: stop, start, cleanup, or reset_alerts"}), 400

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
                    "created": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "critical" if "critical" in f else "suspicious"
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
        
        # Category breakdown
        category_stats = defaultdict(int)
        for log in log_buffer:
            if log['type'] == 'suspicious' and 'metadata' in log:
                categories = log['metadata'].get('analysis', {}).get('categories', [])
                for cat in categories:
                    category_stats[cat] += 1
        
        return jsonify({
            "total_logs": len(log_buffer),
            "speech_detected": speech_count,
            "suspicious_events": suspicious_count,
            "errors": error_count,
            "uptime_hours": round((time.time() - start_time) / 3600, 2),
            "alert_breakdown": dict(alert_counts),
            "category_breakdown": dict(category_stats),
            "current_conversation_exchanges": len(speech_history)
        })

@app.route("/analyze/<log_id>")
def analyze_log(log_id):
    """Get detailed analysis of a specific log entry"""
    try:
        log_id = int(log_id)
        with log_lock:
            if 0 <= log_id < len(log_buffer):
                return jsonify(log_buffer[log_id])
            return jsonify({"error": "Log ID not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid log ID"}), 400

# ---------------- ENTRY POINT ----------------
if __name__ == "__main__":
    print("🚀 Starting Enhanced Voice Proctor System v3.0\n")
    
    # Clean temp directory
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Load existing logs
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                log_buffer = json.load(f)
                print(f"📋 Loaded {len(log_buffer)} existing log entries")
        except:
            print("📋 Starting with fresh logs")
    
    log_event("system", "Enhanced Voice Proctor System starting", severity="normal")

    # Start background threads
    recording_thread = threading.Thread(target=recorder_thread, daemon=True)
    processing_thread = threading.Thread(target=processor_thread, daemon=True)
    
    try:
        recording_thread.start()
        processing_thread.start()
        print("\n✅ System ready - Flask API starting on http://0.0.0.0:5000\n")
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n⚠️  Received shutdown signal")
    except Exception as e:
        print(f"❌ Error starting system: {e}")
        log_event("error", f"System startup failed: {e}", severity="critical")
    finally:
        print("\n🛑 Shutting down Voice Proctor System...")
        is_running.clear()
        time.sleep(2)
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        log_event("system", "Voice Proctor System stopped")
        print("✅ Shutdown complete")