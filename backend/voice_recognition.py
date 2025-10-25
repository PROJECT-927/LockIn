import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
import datetime
import os
import speech_recognition as sr
import time
import json
from queue import Queue, Empty
from collections import defaultdict, deque
import re
import hashlib

# ---------------- SPEED-OPTIMIZED CONFIG ----------------
SAMPLE_RATE = 16000
DURATION = 5 # seconds per chunk
ENERGY_THRESHOLD = 0.008
SPEECH_CONFIDENCE_THRESHOLD = 0.5

# Simplified scoring
SUSPICION_THRESHOLD = 12
CRITICAL_THRESHOLD = 25

# Speed-optimized keywords
KEYWORDS = {
   # High risk (weight: 10)
    "answer": 10, "answers": 10, "solution": 10, "solutions": 10,
    
    # Medium-high risk (weight: 7)
    "question": 7, "help": 7, "tell": 7, "google": 7, "search": 7,
    "phone": 7, "calculator": 7, "chatgpt": 7, "gpt": 7,
    
    # Medium risk (weight: 5)
    "test": 5, "exam": 5, "quiz": 5, "option": 5, "choice": 5,
    "select": 5, "calculate": 5, "solve": 5,
    
    # Lower risk but contextual (weight: 3)
    "what": 3, "how": 3, "why": 3, "send": 3, "give": 3,
    "show": 3, "find": 3, "check": 3, "define": 3,
    "explain": 3,
    "list": 3,
    "name": 3,
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
start_time = time.time()
audio_queue = Queue(maxsize=10)
log_buffer = []
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
    
    log_buffer.append(entry)
    if len(log_buffer) > 300:
        log_buffer.pop(0)
    
    # Auto-save logs
    try:
        with open(LOG_FILE, 'w') as f:
            json.dump(log_buffer, f, indent=2)
    except:
        pass

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
            time.sleep(0.5)
    
    print("Recorder stopped")

# ---------------- PROCESSOR ----------------
def processor_thread():
    """Speed-optimized processor"""
    
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
                print(f"Risk: {score} - Suspicious recorded")
        else:
            log_event("speech", text, metadata=analysis)
        
        # Add to history
        speech_history.append({
            "timestamp": time.time(),
            "text": text,
            "score": score
        })
    
    print("Processor stopped")

# ---------------- STATS DISPLAY ----------------
def display_stats():
    """Display periodic statistics"""
    while is_running.is_set():
        time.sleep(30)  # Every 30 seconds

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("Voice Proctor System")
    print(f"Audio: {SAVE_PATH}")
    print(f"Logs: {LOG_FILE}")
    print()
    
    # Load existing logs
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                log_buffer = json.load(f)
        except:
            pass
    
    log_event("system", "System starting")
    
    print("Starting...")
    print()
    
    # Start threads
    recording_thread = threading.Thread(target=recorder_thread, daemon=True)
    processing_thread = threading.Thread(target=processor_thread, daemon=True)
    stats_thread = threading.Thread(target=display_stats, daemon=True)
    
    try:
        recording_thread.start()
        processing_thread.start()
        stats_thread.start()
        
        print("Listening...")
        print()
        
        # Keep main thread alive
        while is_running.is_set():
            time.sleep(1)
        
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        is_running.clear()
        time.sleep(2)
        
        # Save final logs
        try:
            with open(LOG_FILE, 'w') as f:
                json.dump(log_buffer, f, indent=2)
        except:
            pass
        
        log_event("system", "System stopped")
        print("Stopped")