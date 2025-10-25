#
from flask import Flask, jsonify, send_from_directory, request
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
import datetime
import os
import speech_recognition as sr
import time
import json
import glob
from queue import Queue, Empty
from collections import defaultdict, deque
import re
import hashlib

# Optional imports
try:
    from textblob import TextBlob
    NLP_AVAILABLE = True
except:
    NLP_AVAILABLE = False

# ---------------- SPEED-OPTIMIZED CONFIG ----------------
SAMPLE_RATE = 16000
DURATION = 5  # Shorter for speed
OVERLAP = 0  # No overlap for speed

# Relaxed thresholds for speed
ENERGY_THRESHOLD = 0.008
SPEECH_CONFIDENCE_THRESHOLD = 0.5

# Simplified scoring
SUSPICION_THRESHOLD = 12
CRITICAL_THRESHOLD = 25

# Speed-optimized keywords (only high-risk)
KEYWORDS = {
     "answer": 10, "answers": 10, "solution": 10, "solutions": 10,
    
    # Medium-high risk (weight: 7)
    "question": 7, "help": 7, "tell": 7, "google": 7, "search": 7,
    "phone": 7, "calculator": 7, "chatgpt": 7, "gpt": 7,
    
    # Medium risk (weight: 5)
    "test": 5, "exam": 5, "quiz": 5, "option": 5, "choice": 5,
    "select": 5, "calculate": 5, "solve": 5,
    
    # Lower risk but contextual (weight: 3)
    "what": 3, "how": 3, "why": 3, "send": 3, "give": 3,
    "show": 3, "find": 3, "check": 3
}

# Fast pattern matching
PATTERNS = [
    (r"what\s+is\s+the\s+(answer|solution)", 15),
    (r"question\s+(number\s+)?\d+", 12),
    (r"option\s+[a-d]", 10),
    (r"help\s+me\s+(with|solve|answer)", 12),
    (r"tell\s+me\s+(the|how)", 10),
    (r"(search|google)\s+(for|this)", 12),
    (r"can\s+you\s+(help|tell|give)", 10),
    (r"i\s+don'?t\s+know\s+(the\s+)?(answer|solution)", 8),
    (r"(send|share|give)\s+me", 10),
    (r"what\s+does\s+.{5,30}\s+mean", 7),
    (r"how\s+do\s+(i|you)\s+(calculate|solve|find)", 12),
    (r"(alexa|siri|hey\s+google)", 15),
]

SAVE_PATH = os.path.abspath("suspicious_audio")
TEMP_DIR = os.path.abspath("temp")
LOG_FILE = "voice_log.json"

os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ---------------- GLOBALS ----------------
app = Flask(__name__)
start_time = time.time()
audio_queue = Queue(maxsize=10)
log_buffer = []
log_lock = threading.Lock()
is_running = threading.Event()
is_running.set()

speech_history = deque(maxlen=30)
recent_hashes = deque(maxlen=15)
session_stats = {
    "total_speech": 0,
    "suspicious_events": 0,
    "critical_events": 0
}

# Fast recognizer setup
recognizer = sr.Recognizer()
recognizer.energy_threshold = 250
recognizer.dynamic_energy_threshold = False
recognizer.pause_threshold = 0.6

# ---------------- FAST AUDIO PROCESSING ----------------
def fast_energy(audio):
    """Ultra-fast energy calculation"""
    return np.sqrt(np.mean(audio**2))

def has_speech_fast(audio):
    """Quick speech detection"""
    return fast_energy(audio) > ENERGY_THRESHOLD

def fast_hash(text):
    """Quick deduplication hash"""
    return hashlib.md5(text.encode()).hexdigest()[:12]

def is_duplicate_fast(text):
    """Fast duplicate check"""
    h = fast_hash(text)
    if h in recent_hashes:
        return True
    recent_hashes.append(h)
    return False

# ---------------- FAST ANALYSIS ----------------
def analyze_fast(text):
    """Speed-optimized suspicion analysis"""
    score = 0
    keywords_found = []
    text_lower = text.lower()
    
    # Quick keyword scan
    for word, weight in KEYWORDS.items():
        if word in text_lower:
            score += weight
            keywords_found.append(word)
    
    # Fast pattern matching
    for pattern, pts in PATTERNS:
        if re.search(pattern, text_lower):
            score += pts
    
    # Quick question detection
    if text_lower.startswith(('what', 'how', 'why', 'can', 'could')) or '?' in text:
        score += 5
    
    # Risk level
    if score >= CRITICAL_THRESHOLD:
        risk = "critical"
    elif score >= SUSPICION_THRESHOLD:
        risk = "high"
    else:
        risk = "low"
    
    return {
        "score": score,
        "risk": risk,
        "keywords": keywords_found
    }

# ---------------- FAST TRANSCRIPTION ----------------
def transcribe_fast(filepath):
    """Speed-optimized transcription"""
    try:
        with sr.AudioFile(filepath) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language='en-US').lower()
            return text
    except:
        return ""

# ---------------- LOGGING ----------------
def log_event(event_type, text="", filename=None, metadata=None):
    """Fast logging"""
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": event_type,
        "text": text,
        "file": filename,
        "metadata": metadata or {}
    }
    
    with log_lock:
        log_buffer.append(entry)
        if len(log_buffer) > 300:
            log_buffer.pop(0)

def save_audio_fast(audio, label):
    """Fast audio saving"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{label}_{timestamp}.wav"
    filepath = os.path.join(SAVE_PATH, filename)
    
    try:
        sf.write(filepath, audio, SAMPLE_RATE)
        return filename
    except:
        return None

# ---------------- RECORDER ----------------
def recorder_thread():
    """Speed-optimized recorder"""
    print("🎙️  Recorder started")
    device = sd.default.device[0]
    
    while is_running.is_set():
        try:
            audio = sd.rec(
                int(DURATION * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='float32',
                device=device,
                blocking=True
            )
            
            audio = np.squeeze(audio)
            
            # Quick energy check
            if fast_energy(audio) > ENERGY_THRESHOLD * 0.5:
                try:
                    audio_queue.put(audio, block=False)
                except:
                    pass  # Skip if queue full
                    
        except Exception as e:
            print(f"Record error: {e}")
            time.sleep(0.5)
    
    print("🛑 Recorder stopped")

# ---------------- PROCESSOR ----------------
def processor_thread():
    """Speed-optimized processor"""
    print("⚙️  Processor started")
    
    while is_running.is_set():
        try:
            audio_chunk = audio_queue.get(timeout=1)
        except Empty:
            continue
        
        # Quick speech check
        if not has_speech_fast(audio_chunk):
            continue
        
        # Save temp
        temp_file = os.path.join(TEMP_DIR, f"temp_{threading.get_ident()}.wav")
        try:
            sf.write(temp_file, audio_chunk, SAMPLE_RATE)
        except:
            continue
        
        # Transcribe
        text = transcribe_fast(temp_file)
        
        # Cleanup temp
        try:
            os.remove(temp_file)
        except:
            pass
        
        if not text or len(text) < 2:
            continue
        
        # Dedup
        if is_duplicate_fast(text):
            continue
        
        print(f"💬 {text}")
        
        # Analyze
        analysis = analyze_fast(text)
        score = analysis["score"]
        
        # Update stats
        session_stats["total_speech"] += 1
        
        if score >= SUSPICION_THRESHOLD:
            session_stats["suspicious_events"] += 1
            
            if score >= CRITICAL_THRESHOLD:
                session_stats["critical_events"] += 1
            
            # Save suspicious audio
            label = f"risk{score}"
            filename = save_audio_fast(audio_chunk, label)
            
            if filename:
                log_event("suspicious", text, filename, analysis)
                print(f"🚨 ALERT (Risk: {score}) - {filename}")
                print(f"   Keywords: {', '.join(analysis['keywords'])}")
        else:
            log_event("speech", text, metadata=analysis)
        
        # Add to history
        speech_history.append({
            "timestamp": time.time(),
            "text": text,
            "score": score
        })
    
    print("🛑 Processor stopped")

# ---------------- API ROUTES ----------------
@app.route("/")
def home():
    return jsonify({
        "message": "High-Speed Voice Proctor",
        "status": "active" if is_running.is_set() else "stopped",
        "version": "SPEED-1.0"
    })

@app.route("/status")
def status():
    files = [f for f in os.listdir(SAVE_PATH) if f.endswith('.wav')]
    uptime = int(time.time() - start_time)
    
    return jsonify({
        "active": is_running.is_set(),
        "uptime_seconds": uptime,
        "queue_size": audio_queue.qsize(),
        "total_files": len(files),
        "stats": session_stats
    })

@app.route("/logs")
def get_logs():
    limit = request.args.get('limit', type=int)
    
    with log_lock:
        logs = log_buffer if not limit else log_buffer[-limit:]
        return jsonify({
            "logs": logs,
            "count": len(logs)
        })

@app.route("/files")
def list_files():
    files = []
    for f in sorted(os.listdir(SAVE_PATH), reverse=True):
        if f.endswith('.wav'):
            filepath = os.path.join(SAVE_PATH, f)
            stat = os.stat(filepath)
            
            risk_match = re.search(r'risk(\d+)', f)
            risk_score = int(risk_match.group(1)) if risk_match else 0
            
            files.append({
                "filename": f,
                "risk_score": risk_score,
                "size_kb": round(stat.st_size / 1024, 2),
                "created": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
    
    return jsonify({
        "files": files,
        "count": len(files)
    })

@app.route("/audio/<path:filename>")
def get_audio(filename):
    return send_from_directory(SAVE_PATH, os.path.basename(filename))

@app.route("/stats")
def stats():
    with log_lock:
        suspicious = [l for l in log_buffer if l['type'] == 'suspicious']
        
        keyword_counts = defaultdict(int)
        for log in suspicious:
            for kw in log.get('metadata', {}).get('keywords', []):
                keyword_counts[kw] += 1
        
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            "total_logs": len(log_buffer),
            "suspicious_count": len(suspicious),
            "session": session_stats,
            "top_keywords": [{"word": k, "count": c} for k, c in top_keywords],
            "recent_speech": list(speech_history)[-10:]
        })

@app.route("/recent")
def recent():
    """Get recent detections"""
    recent = list(speech_history)[-10:]
    return jsonify({
        "recent": recent,
        "count": len(recent)
    })

@app.route("/control/<action>", methods=['POST'])
def control(action):
    if action == "stop":
        is_running.clear()
        return jsonify({"status": "stopping"})
    
    elif action == "start":
        if not is_running.is_set():
            is_running.set()
            return jsonify({"status": "starting"})
        return jsonify({"status": "already running"})
    
    elif action == "cleanup":
        count = 0
        for f in glob.glob(os.path.join(SAVE_PATH, "*.wav")):
            try:
                os.remove(f)
                count += 1
            except:
                pass
        return jsonify({"status": "cleanup complete", "removed": count})
    
    elif action == "reset":
        speech_history.clear()
        session_stats.update({
            "total_speech": 0,
            "suspicious_events": 0,
            "critical_events": 0
        })
        return jsonify({"status": "reset complete"})
    
    return jsonify({"error": "Invalid action"}), 400

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy" if is_running.is_set() else "stopped",
        "timestamp": datetime.datetime.now().isoformat()
    })

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 HIGH-SPEED VOICE PROCTORING SYSTEM")
    print("=" * 60)
    print()
    print("⚡ Speed Optimizations:")
    print("   • 2-second chunks (fast response)")
    print("   • Minimal processing overhead")
    print("   • Streamlined detection")
    print("   • Optimized thresholds")
    print()
    
    # Load existing logs
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                log_buffer = json.load(f)
        except:
            pass
    
    log_event("system", "High-Speed Voice Proctor starting")
    
    # Start threads
    recording_thread = threading.Thread(target=recorder_thread, daemon=True)
    processing_thread = threading.Thread(target=processor_thread, daemon=True)
    
    try:
        recording_thread.start()
        processing_thread.start()
        
        print("✅ System ready!")
        print("🌐 API: http://0.0.0.0:5000")
        print()
        print("📍 Quick Endpoints:")
        print("   • GET  /status   - System status")
        print("   • GET  /stats    - Statistics")
        print("   • GET  /recent   - Recent detections")
        print("   • GET  /logs     - All logs")
        print("   • GET  /files    - Audio files")
        print("   • POST /control/<action> - Control")
        print()
        print("=" * 60)
        print()
        
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n⚠️  Shutting down...")
    finally:
        print("\n🛑 Stopping...")
        is_running.clear()
        time.sleep(1)
        
        # Save logs
        try:
            with open(LOG_FILE, 'w') as f:
                json.dump(log_buffer, f)
        except:
            pass
        
        log_event("system", "System stopped")
        print("✅ Shutdown complete")
        print("=" * 60)