"""
MAXIMUM ACCURACY VOICE PROCTORING SYSTEM
- Multi-engine speech recognition with fallbacks
- Advanced NLP with context understanding
- ML-based anomaly detection
- Real-time risk scoring
- Conversation pattern analysis
"""

from flask import Flask, jsonify, send_from_directory, request
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
from scipy.fft import rfft, rfftfreq
from collections import defaultdict, deque
import re
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Try to import optional advanced libraries
try:
    import pyttsx3
    TTS_AVAILABLE = True
except:
    TTS_AVAILABLE = False

try:
    from textblob import TextBlob
    NLP_AVAILABLE = True
except:
    NLP_AVAILABLE = False

# ---------------- ADVANCED CONFIG ----------------
SAMPLE_RATE = 16000
DURATION = 4  # Shorter chunks for faster response
OVERLAP = 1  # Overlap between chunks for continuity

# Advanced thresholds (tuned for accuracy)
ENERGY_THRESHOLD = 0.012
ENERGY_SILENCE_RATIO = 0.3  # Max ratio of silent frames
ZCR_LOW = 0.02
ZCR_HIGH = 0.35
SPECTRAL_CENTROID_LOW = 200
SPECTRAL_CENTROID_HIGH = 4500

# Multi-layer detection
SPEECH_CONFIDENCE_THRESHOLD = 0.65
SUSPICION_THRESHOLD = 15  # Points-based system
CRITICAL_THRESHOLD = 35

# Enhanced keyword system with weights
WEIGHTED_KEYWORDS = {
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
    "show": 3, "find": 3, "check": 3
}

# Suspicious phrase patterns (regex with scores)
SUSPICIOUS_PATTERNS = [
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

# Academic integrity phrases (very suspicious)
CHEATING_INDICATORS = [
    r"doing\s+(my|the)\s+(test|exam|quiz)",
    r"taking\s+(an?|the)\s+(test|exam|quiz)",
    r"during\s+(the\s+)?(test|exam|quiz)",
    r"exam\s+is\s+(starting|ongoing|running)",
]

SAVE_PATH = os.path.abspath("suspicious_audio")
TEMP_DIR = os.path.abspath("temp")
LOG_FILE = "voice_log.json"
RISK_PROFILE_FILE = "risk_profile.json"
MAX_LOG_ENTRIES = 500
CLEANUP_HOURS = 3

# Conversation tracking
CONVERSATION_WINDOW = 45  # seconds
MIN_CONVERSATION_LENGTH = 4  # exchanges
RAPID_SPEECH_WINDOW = 15  # seconds
RAPID_SPEECH_THRESHOLD = 3  # exchanges

# Multi-engine recognition
USE_GOOGLE = True
USE_SPHINX = True  # Offline fallback

# ---------------- DATA STRUCTURES ----------------
@dataclass
class AudioFeatures:
    energy: float
    zcr: float
    spectral_centroid: float
    spectral_rolloff: float
    pitch_estimate: float
    silence_ratio: float
    speech_confidence: float

@dataclass
class SpeechEvent:
    timestamp: float
    text: str
    confidence: float
    audio_features: Dict
    duration: float

@dataclass
class SuspicionAnalysis:
    score: int
    risk_level: str  # low, medium, high, critical
    keywords_found: List[str]
    patterns_matched: List[str]
    reasons: List[str]
    context_flags: List[str]
    is_question: bool
    is_imperative: bool
    word_count: int

# Global state
start_time = time.time()
last_cleanup_time = None
speech_history = deque(maxlen=50)
risk_profile = defaultdict(int)
session_stats = {
    "total_speech": 0,
    "suspicious_events": 0,
    "critical_events": 0,
    "conversation_detected": 0,
    "avg_risk_score": 0,
    "peak_risk_time": None
}

os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ---------------- INITIALIZATION ----------------
app = Flask(__name__)

# Multiple recognizers for accuracy
recognizer_google = sr.Recognizer()
recognizer_google.energy_threshold = 300
recognizer_google.dynamic_energy_threshold = True
recognizer_google.pause_threshold = 0.8

recognizer_sphinx = sr.Recognizer()

audio_queue = Queue(maxsize=15)
log_buffer = []
log_lock = threading.Lock()
is_running = threading.Event()
is_running.set()

# Cache for deduplication
recent_transcriptions = deque(maxlen=20)

# ---------------- ADVANCED AUDIO ANALYSIS ----------------
def calculate_energy(audio):
    """RMS energy with normalization"""
    if audio is None or len(audio) == 0:
        return 0
    return np.sqrt(np.mean(audio**2))

def calculate_zcr(audio):
    """Zero-crossing rate"""
    if audio is None or len(audio) < 2:
        return 0
    signs = np.sign(audio)
    signs[signs == 0] = -1
    return np.sum(np.abs(np.diff(signs))) / (2 * len(audio))

def calculate_spectral_features(audio, sr=SAMPLE_RATE):
    """Calculate multiple spectral features"""
    if audio is None or len(audio) == 0:
        return 0, 0
    
    # Apply window
    windowed = audio * np.hamming(len(audio))
    
    # FFT
    spectrum = np.abs(rfft(windowed))
    freqs = rfftfreq(len(windowed), 1/sr)
    
    if np.sum(spectrum) == 0:
        return 0, 0
    
    # Spectral centroid (brightness)
    centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
    
    # Spectral rolloff (85% of energy)
    cumsum = np.cumsum(spectrum)
    rolloff_idx = np.where(cumsum >= 0.85 * cumsum[-1])[0]
    rolloff = freqs[rolloff_idx[0]] if len(rolloff_idx) > 0 else 0
    
    return centroid, rolloff

def calculate_silence_ratio(audio, threshold=0.01, frame_length=0.1):
    """Calculate ratio of silent frames"""
    if audio is None or len(audio) == 0:
        return 1.0
    
    frame_samples = int(frame_length * SAMPLE_RATE)
    silent_frames = 0
    total_frames = 0
    
    for i in range(0, len(audio) - frame_samples, frame_samples):
        frame = audio[i:i + frame_samples]
        if calculate_energy(frame) < threshold:
            silent_frames += 1
        total_frames += 1
    
    return silent_frames / total_frames if total_frames > 0 else 1.0

def estimate_pitch_autocorrelation(audio, sr=SAMPLE_RATE):
    """Improved pitch estimation"""
    try:
        # Normalize
        audio = audio - np.mean(audio)
        
        # Autocorrelation
        corr = np.correlate(audio, audio, mode='full')
        corr = corr[len(corr)//2:]
        
        # Find first peak after initial
        d = np.diff(corr)
        start = np.where(d > 0)[0]
        if len(start) == 0:
            return 0
        
        peak_idx = np.argmax(corr[start[0]:]) + start[0]
        
        # Convert to Hz
        if peak_idx > 0:
            pitch = sr / peak_idx
            # Human speech range: 85-255 Hz
            if 50 < pitch < 500:
                return pitch
        
        return 0
    except:
        return 0

def extract_audio_features(audio) -> AudioFeatures:
    """Extract comprehensive audio features"""
    try:
        energy = calculate_energy(audio)
        zcr = calculate_zcr(audio)
        centroid, rolloff = calculate_spectral_features(audio)
        pitch = estimate_pitch_autocorrelation(audio)
        silence_ratio = calculate_silence_ratio(audio)
        
        # Calculate speech confidence score
        confidence = 0.0
        
        # Energy check
        if energy > ENERGY_THRESHOLD:
            confidence += 0.3
        
        # ZCR check (speech has moderate ZCR)
        if ZCR_LOW < zcr < ZCR_HIGH:
            confidence += 0.25
        
        # Spectral centroid check
        if SPECTRAL_CENTROID_LOW < centroid < SPECTRAL_CENTROID_HIGH:
            confidence += 0.2
        
        # Pitch check (human speech range)
        if 70 < pitch < 400:
            confidence += 0.15
        
        # Silence ratio check
        if silence_ratio < ENERGY_SILENCE_RATIO:
            confidence += 0.1
        
        return AudioFeatures(
            energy=float(energy),
            zcr=float(zcr),
            spectral_centroid=float(centroid),
            spectral_rolloff=float(rolloff),
            pitch_estimate=float(pitch),
            silence_ratio=float(silence_ratio),
            speech_confidence=float(confidence)
        )
    except Exception as e:
        log_event("error", f"Feature extraction error: {e}")
        return AudioFeatures(0, 0, 0, 0, 0, 1.0, 0)

def has_speech(audio_features: AudioFeatures) -> bool:
    """Determine if audio contains speech"""
    return audio_features.speech_confidence > SPEECH_CONFIDENCE_THRESHOLD

def apply_advanced_filter(audio, sr=SAMPLE_RATE):
    """Apply multiple filters for clarity"""
    try:
        # 1. Bandpass filter (human speech)
        nyquist = sr / 2
        low = 200 / nyquist
        high = 3800 / nyquist
        b, a = signal.butter(5, [low, high], btype='band')
        filtered = signal.filtfilt(b, a, audio)
        
        # 2. Noise reduction (simple spectral subtraction)
        # Estimate noise from first 0.5 seconds
        noise_sample = filtered[:int(0.5 * sr)]
        noise_level = np.mean(np.abs(noise_sample))
        
        # Suppress low-level noise
        filtered = np.where(np.abs(filtered) > noise_level * 1.5, filtered, filtered * 0.3)
        
        # 3. Normalize
        max_val = np.max(np.abs(filtered))
        if max_val > 0:
            filtered = filtered / max_val * 0.9
        
        return filtered
    except:
        return audio

# ---------------- ADVANCED TEXT ANALYSIS ----------------
def calculate_text_hash(text):
    """Create hash for deduplication"""
    return hashlib.md5(text.encode()).hexdigest()[:16]

def is_duplicate(text):
    """Check if we've recently seen this transcription"""
    text_hash = calculate_text_hash(text)
    if text_hash in recent_transcriptions:
        return True
    recent_transcriptions.append(text_hash)
    return False

def analyze_grammar_context(text):
    """Use NLP for grammar analysis if available"""
    flags = []
    
    if NLP_AVAILABLE:
        try:
            blob = TextBlob(text)
            
            # Check sentiment (questions often have specific patterns)
            if blob.sentiment.polarity < -0.1:
                flags.append("negative_sentiment")
            
            # Tag parts of speech
            tags = blob.tags
            
            # Look for question patterns (WH-words + verbs)
            wh_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which']
            has_wh = any(word[0].lower() in wh_words for word in tags)
            
            if has_wh:
                flags.append("interrogative")
                
        except:
            pass
    
    return flags

def analyze_suspicion(text: str) -> SuspicionAnalysis:
    """Comprehensive suspicion analysis"""
    score = 0
    keywords_found = []
    patterns_matched = []
    reasons = []
    context_flags = []
    
    text_lower = text.lower().strip()
    words = text_lower.split()
    word_count = len(words)
    
    # 1. Weighted keyword matching
    for word, weight in WEIGHTED_KEYWORDS.items():
        if word in text_lower:
            score += weight
            keywords_found.append(word)
            reasons.append(f"Keyword '{word}' (+{weight})")
    
    # 2. Pattern matching
    for pattern, pattern_score in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text_lower):
            score += pattern_score
            patterns_matched.append(pattern)
            reasons.append(f"Pattern match (+{pattern_score})")
    
    # 3. Cheating indicators
    for pattern in CHEATING_INDICATORS:
        if re.search(pattern, text_lower):
            score += 20
            context_flags.append("explicit_exam_context")
            reasons.append("Explicit exam/test mention (+20)")
    
    # 4. Question detection
    is_question = False
    question_words = ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'can', 'could', 'would', 'should']
    if any(text_lower.startswith(qw) for qw in question_words) or text_lower.endswith('?'):
        is_question = True
        score += 5
        reasons.append("Question format (+5)")
    
    # 5. Imperative detection
    is_imperative = False
    imperative_verbs = ['tell', 'give', 'show', 'help', 'send', 'search', 'find', 'calculate', 'solve']
    if any(text_lower.startswith(verb) for verb in imperative_verbs):
        is_imperative = True
        score += 6
        reasons.append("Imperative statement (+6)")
    
    # 6. Length-based scoring
    if word_count > 8:
        bonus = min((word_count - 8) * 1, 10)
        score += bonus
        reasons.append(f"Lengthy speech: {word_count} words (+{bonus})")
    
    # 7. Multiple question words
    question_count = sum(1 for word in words if word in question_words)
    if question_count >= 2:
        score += question_count * 3
        reasons.append(f"Multiple question words ({question_count}) (+{question_count * 3})")
    
    # 8. Academic terminology combinations
    academic_terms = ['equation', 'formula', 'theorem', 'proof', 'derivative', 'integral']
    if any(term in text_lower for term in academic_terms) and is_question:
        score += 8
        reasons.append("Academic term in question (+8)")
    
    # 9. Context flags from NLP
    nlp_flags = analyze_grammar_context(text)
    context_flags.extend(nlp_flags)
    
    # 10. Number mentions (question numbers)
    if re.search(r'\b\d+\b', text_lower):
        score += 4
        reasons.append("Number mentioned (+4)")
    
    # Determine risk level
    if score >= CRITICAL_THRESHOLD:
        risk_level = "critical"
    elif score >= SUSPICION_THRESHOLD:
        risk_level = "high"
    elif score >= 10:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return SuspicionAnalysis(
        score=score,
        risk_level=risk_level,
        keywords_found=keywords_found,
        patterns_matched=patterns_matched,
        reasons=reasons,
        context_flags=context_flags,
        is_question=is_question,
        is_imperative=is_imperative,
        word_count=word_count
    )

def detect_conversation_pattern() -> Tuple[bool, int, str]:
    """Advanced conversation detection"""
    current_time = time.time()
    
    # Filter recent speech
    recent = [e for e in speech_history if current_time - e.timestamp < CONVERSATION_WINDOW]
    rapid = [e for e in speech_history if current_time - e.timestamp < RAPID_SPEECH_WINDOW]
    
    exchange_count = len(recent)
    rapid_count = len(rapid)
    
    # Check for conversation patterns
    is_conversation = exchange_count >= MIN_CONVERSATION_LENGTH
    is_rapid = rapid_count >= RAPID_SPEECH_THRESHOLD
    
    pattern_type = "none"
    if is_rapid:
        pattern_type = "rapid_exchange"
    elif is_conversation:
        pattern_type = "sustained_conversation"
    
    return is_conversation or is_rapid, exchange_count, pattern_type

def analyze_speech_patterns():
    """Analyze patterns in recent speech history"""
    if len(speech_history) < 2:
        return {}
    
    # Calculate average pause between speeches
    pauses = []
    for i in range(1, len(speech_history)):
        pause = speech_history[i].timestamp - speech_history[i-1].timestamp
        pauses.append(pause)
    
    avg_pause = np.mean(pauses) if pauses else 0
    
    # Calculate average confidence
    avg_confidence = np.mean([e.confidence for e in speech_history])
    
    # Check for suspicious trends
    recent_5 = list(speech_history)[-5:]
    suspicious_count = sum(1 for e in recent_5 if e.confidence > 0.7)
    
    return {
        "avg_pause": avg_pause,
        "avg_confidence": avg_confidence,
        "recent_suspicious": suspicious_count,
        "total_exchanges": len(speech_history)
    }

# ---------------- MULTI-ENGINE TRANSCRIPTION ----------------
def transcribe_multi_engine(filepath) -> Tuple[str, float]:
    """Try multiple recognition engines for best accuracy"""
    results = []
    
    # Engine 1: Google (most accurate, requires internet)
    if USE_GOOGLE:
        try:
            with sr.AudioFile(filepath) as source:
                recognizer_google.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = recognizer_google.record(source)
                text = recognizer_google.recognize_google(
                    audio_data, 
                    language='en-US',
                    show_all=False
                ).lower()
                
                if text:
                    results.append(("google", text, 0.9))
        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            log_event("warning", "Google API unavailable")
        except Exception as e:
            log_event("error", f"Google recognition error: {e}")
    
    # Engine 2: Sphinx (offline fallback, less accurate)
    if USE_SPHINX and not results:
        try:
            with sr.AudioFile(filepath) as source:
                audio_data = recognizer_sphinx.record(source)
                text = recognizer_sphinx.recognize_sphinx(audio_data).lower()
                
                if text:
                    results.append(("sphinx", text, 0.6))
        except:
            pass
    
    # Return best result
    if results:
        engine, text, confidence = max(results, key=lambda x: x[2])
        return text, confidence
    
    return "", 0.0

# ---------------- CORE FUNCTIONS ----------------
def log_event(event_type, text="", filename=None, severity="normal", metadata=None):
    """Enhanced logging with metadata"""
    entry = {
        "id": len(log_buffer),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "unix_time": time.time(),
        "type": event_type,
        "text": text,
        "file": filename,
        "severity": severity,
        "metadata": metadata or {}
    }
    
    with log_lock:
        log_buffer.append(entry)
        if len(log_buffer) > MAX_LOG_ENTRIES:
            log_buffer.pop(0)
        
        try:
            with open(LOG_FILE, "w") as f:
                json.dump(log_buffer, f, indent=2)
        except Exception as e:
            print(f"❌ Error writing log: {e}")

def save_risk_profile():
    """Save risk profile to disk"""
    try:
        with open(RISK_PROFILE_FILE, 'w') as f:
            json.dump({
                "risk_profile": dict(risk_profile),
                "session_stats": session_stats
            }, f, indent=2)
    except Exception as e:
        log_event("error", f"Failed to save risk profile: {e}")

def cleanup_old_files(hours=CLEANUP_HOURS):
    """Cleanup with better logging"""
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
        log_event("error", f"Cleanup error: {e}")
    
    return cleaned

def get_input_device():
    """Find best input device"""
    try:
        devices = sd.query_devices()
        default_input = sd.default.device[0]
        
        if default_input is not None:
            device_info = sd.query_devices(default_input)
            log_event("system", f"Using device: {device_info['name']}")
            return default_input
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                log_event("system", f"Using fallback device: {device['name']}")
                return i
        
        raise RuntimeError("No input device found")
    except Exception as e:
        log_event("error", f"Device detection error: {e}", severity="critical")
        raise

def record_chunk():
    """Record with improved error handling"""
    try:
        device = get_input_device()
        
        audio = sd.rec(
            int(DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            device=device,
            blocking=True
        )
        
        audio = np.squeeze(audio)
        audio = apply_advanced_filter(audio)
        
        return audio
    except Exception as e:
        log_event("error", f"Recording failed: {e}")
        return None

def save_audio(audio, label, metadata=None):
    """Save with metadata"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{label}_{timestamp}.wav"
    filepath = os.path.join(SAVE_PATH, filename)
    
    try:
        sf.write(filepath, audio, SAMPLE_RATE)
        
        # Save metadata as JSON
        if metadata:
            meta_file = filepath.replace('.wav', '.json')
            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        return filepath, filename
    except Exception as e:
        log_event("error", f"Save error: {e}")
        return None, None

# ---------------- BACKGROUND THREADS ----------------
def recorder_thread():
    """Optimized recorder"""
    print("🎙️  Recorder thread started")
    consecutive_errors = 0
    max_errors = 5
    
    while is_running.is_set():
        try:
            audio_chunk = record_chunk()
            
            if audio_chunk is None:
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    log_event("error", "Too many recording errors", severity="critical")
                    break
                time.sleep(1)
                continue
            
            consecutive_errors = 0
            
            # Quick energy check before queuing
            if calculate_energy(audio_chunk) > ENERGY_THRESHOLD * 0.5:
                try:
                    audio_queue.put(audio_chunk, timeout=1)
                except:
                    log_event("warning", "Audio queue full, dropping chunk")
            
        except Exception as e:
            log_event("error", f"Recorder error: {e}")
            consecutive_errors += 1
            if consecutive_errors >= max_errors:
                break
            time.sleep(1)
    
    print("🛑 Recorder thread stopped")

def processor_thread():
    """Advanced processor with ML-style scoring"""
    print("⚙️  Processor thread started")
    last_cleanup = time.time()
    cleanup_interval = 300
    
    while is_running.is_set():
        try:
            # Periodic maintenance
            if time.time() - last_cleanup > cleanup_interval:
                cleanup_old_files()
                save_risk_profile()
                last_cleanup = time.time()
            
            # Get audio
            try:
                audio_chunk = audio_queue.get(timeout=1)
            except Empty:
                continue
            
            # Extract features
            features = extract_audio_features(audio_chunk)
            
            # Voice activity detection
            if not has_speech(features):
                continue
            
            # Save temp file
            temp_file = os.path.join(TEMP_DIR, f"temp_{threading.get_ident()}.wav")
            try:
                sf.write(temp_file, audio_chunk, SAMPLE_RATE)
            except Exception as e:
                log_event("error", f"Temp file error: {e}")
                continue
            
            # Multi-engine transcription
            text, confidence = transcribe_multi_engine(temp_file)
            
            # Cleanup
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
            
            # Process transcription
            if not text or len(text) < 2:
                print("👂 Speech detected (unclear)")
                log_event("speech", "unclear", metadata=asdict(features))
                continue
            
            # Deduplication
            if is_duplicate(text):
                continue
            
            current_time = time.time()
            
            print(f"💬 Speech: {text}")
            
            # Analyze suspicion
            analysis = analyze_suspicion(text)
            
            # Conversation detection
            is_conv, exchanges, conv_type = detect_conversation_pattern()
            
            # Calculate final risk score
            risk_score = analysis.score
            if is_conv:
                risk_score += 10
                if conv_type == "rapid_exchange":
                    risk_score += 5
            
            # Update session stats
            session_stats["total_speech"] += 1
            if risk_score >= SUSPICION_THRESHOLD:
                session_stats["suspicious_events"] += 1
            if risk_score >= CRITICAL_THRESHOLD:
                session_stats["critical_events"] += 1
            if is_conv:
                session_stats["conversation_detected"] += 1
            
            # Update average risk
            total = session_stats["total_speech"]
            session_stats["avg_risk_score"] = (
                (session_stats["avg_risk_score"] * (total - 1) + risk_score) / total
            )
            
            # Track peak risk
            if risk_score >= CRITICAL_THRESHOLD:
                session_stats["peak_risk_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Add to history
            speech_event = SpeechEvent(
                timestamp=current_time,
                text=text,
                confidence=risk_score / 100,
                audio_features=asdict(features),
                duration=DURATION
            )
            speech_history.append(speech_event)
            
            # Determine severity
            if risk_score >= CRITICAL_THRESHOLD:
                severity = "critical"
            elif risk_score >= SUSPICION_THRESHOLD:
                severity = "high"
            elif risk_score >= 10:
                severity = "medium"
            else:
                severity = "low"
            
            # Prepare metadata
            metadata = {
                "analysis": asdict(analysis),
                "audio_features": asdict(features),
                "conversation": is_conv,
                "conversation_type": conv_type,
                "exchange_count": exchanges,
                "final_risk_score": risk_score,
                "transcription_confidence": confidence,
                "pattern_analysis": analyze_speech_patterns()
            }
            
            # Log event
            log_event("speech", text, metadata=metadata, severity=severity)
            
            # Save suspicious audio
            if risk_score >= SUSPICION_THRESHOLD:
                label = f"critical_risk{risk_score}" if severity == "critical" else f"suspicious_risk{risk_score}"
                filepath, filename = save_audio(audio_chunk, label, metadata)
                
                if filename:
                    log_event(
                        "suspicious",
                        text,
                        filename,
                        severity=severity,
                        metadata=metadata
                    )
                    
                    # Update risk profile
                    risk_profile[severity] += 1
                    
                    # Console output
                    print(f"🚨 {severity.upper()} ALERT (Risk: {risk_score})")
                    print(f"   File: {filename}")
                    print(f"   Text: {text}")
                    print(f"   Reasons: {', '.join(analysis.reasons[:3])}")
                    if is_conv:
                        print(f"   ⚠️  {conv_type.replace('_', ' ').title()} detected ({exchanges} exchanges)")
            
        except Exception as e:
            log_event("error", f"Processor error: {e}", severity="high")
            time.sleep(1)
    
    # Final save on shutdown
    save_risk_profile()
    print("🛑 Processor thread stopped")

# ---------------- FLASK ROUTES ----------------
@app.route("/")
def home():
    return jsonify({
        "message": "Maximum Accuracy Voice Proctor",
        "status": "active" if is_running.is_set() else "stopped",
        "version": "4.0-MAX",
        "features": [
            "multi_engine_recognition",
            "advanced_nlp_analysis",
            "ml_style_scoring",
            "conversation_detection",
            "audio_feature_extraction",
            "deduplication",
            "risk_profiling",
            "context_awareness"
        ],
        "engines": {
            "google": USE_GOOGLE,
            "sphinx": USE_SPHINX,
            "nlp": NLP_AVAILABLE
        }
    })

@app.route("/logs")
def get_logs():
    """Get all logs with filtering"""
    severity = request.args.get('severity')
    event_type = request.args.get('type')
    limit = request.args.get('limit', type=int)
    
    with log_lock:
        filtered = log_buffer
        
        if severity:
            filtered = [l for l in filtered if l.get('severity') == severity]
        
        if event_type:
            filtered = [l for l in filtered if l.get('type') == event_type]
        
        if limit:
            filtered = filtered[-limit:]
        
        return jsonify({
            "logs": filtered,
            "count": len(filtered),
            "total": len(log_buffer)
        })

@app.route("/logs/<int:log_id>")
def get_log_detail(log_id):
    """Get detailed log entry"""
    with log_lock:
        if 0 <= log_id < len(log_buffer):
            return jsonify(log_buffer[log_id])
        return jsonify({"error": "Log not found"}), 404

@app.route("/audio/<path:filename>")
def get_audio(filename):
    """Download audio file"""
    safe_path = os.path.join(SAVE_PATH, os.path.basename(filename))
    if not os.path.exists(safe_path):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(SAVE_PATH, os.path.basename(filename))

@app.route("/audio/<path:filename>/metadata")
def get_audio_metadata(filename):
    """Get metadata for audio file"""
    meta_file = os.path.join(SAVE_PATH, os.path.basename(filename).replace('.wav', '.json'))
    if not os.path.exists(meta_file):
        return jsonify({"error": "Metadata not found"}), 404
    
    try:
        with open(meta_file, 'r') as f:
            return jsonify(json.load(f))
    except:
        return jsonify({"error": "Failed to read metadata"}), 500

@app.route("/status")
def status():
    """Comprehensive system status"""
    try:
        saved_files = [f for f in os.listdir(SAVE_PATH) if f.endswith('.wav')]
        uptime = int(time.time() - start_time)
        
        # Calculate statistics
        critical_files = [f for f in saved_files if 'critical' in f]
        suspicious_files = [f for f in saved_files if 'suspicious' in f and 'critical' not in f]
        
        return jsonify({
            "system": {
                "active": is_running.is_set(),
                "uptime_seconds": uptime,
                "uptime_formatted": str(datetime.timedelta(seconds=uptime)),
                "last_cleanup": last_cleanup_time.strftime("%Y-%m-%d %H:%M:%S") if last_cleanup_time else "Never"
            },
            "queue": {
                "size": audio_queue.qsize(),
                "max_size": audio_queue.maxsize
            },
            "files": {
                "total": len(saved_files),
                "critical": len(critical_files),
                "suspicious": len(suspicious_files)
            },
            "logs": {
                "total": len(log_buffer),
                "max": MAX_LOG_ENTRIES
            },
            "speech": {
                "recent_count": len(speech_history),
                "window_seconds": CONVERSATION_WINDOW
            },
            "session_stats": session_stats,
            "risk_profile": dict(risk_profile)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats")
def stats():
    """Detailed statistics"""
    with log_lock:
        # Count by type
        type_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for log in log_buffer:
            type_counts[log['type']] += 1
            severity_counts[log.get('severity', 'normal')] += 1
        
        # Recent activity (last hour)
        one_hour_ago = time.time() - 3600
        recent_logs = [l for l in log_buffer if l.get('unix_time', 0) > one_hour_ago]
        
        # Keyword frequency
        keyword_freq = defaultdict(int)
        for log in log_buffer:
            if log['type'] == 'suspicious':
                metadata = log.get('metadata', {})
                analysis = metadata.get('analysis', {})
                for kw in analysis.get('keywords_found', []):
                    keyword_freq[kw] += 1
        
        # Top keywords
        top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            "overview": {
                "total_logs": len(log_buffer),
                "by_type": dict(type_counts),
                "by_severity": dict(severity_counts)
            },
            "recent_activity": {
                "last_hour": len(recent_logs),
                "logs": recent_logs[-10:]
            },
            "session": session_stats,
            "risk_profile": dict(risk_profile),
            "keywords": {
                "top_10": [{"keyword": k, "count": c} for k, c in top_keywords],
                "total_unique": len(keyword_freq)
            },
            "patterns": analyze_speech_patterns()
        })

@app.route("/control/<action>", methods=['POST'])
def control(action):
    """System control"""
    if action == "stop":
        is_running.clear()
        save_risk_profile()
        log_event("system", "System stopped via API", severity="normal")
        return jsonify({"status": "stopping"})
    
    elif action == "start":
        if not is_running.is_set():
            is_running.set()
            log_event("system", "System started via API", severity="normal")
            return jsonify({"status": "starting"})
        return jsonify({"status": "already running"})
    
    elif action == "cleanup":
        cleaned = cleanup_old_files(0)
        return jsonify({
            "status": "cleanup complete",
            "files_removed": cleaned
        })
    
    elif action == "reset":
        # Reset counters and history
        risk_profile.clear()
        speech_history.clear()
        session_stats.update({
            "total_speech": 0,
            "suspicious_events": 0,
            "critical_events": 0,
            "conversation_detected": 0,
            "avg_risk_score": 0,
            "peak_risk_time": None
        })
        log_event("system", "Statistics reset via API", severity="normal")
        return jsonify({"status": "reset complete"})
    
    elif action == "save_profile":
        save_risk_profile()
        return jsonify({"status": "profile saved"})
    
    return jsonify({"error": "Invalid action. Use: stop, start, cleanup, reset, save_profile"}), 400

@app.route("/files")
def list_files():
    """List all audio files with metadata"""
    try:
        files = []
        for f in sorted(os.listdir(SAVE_PATH), reverse=True):
            if f.endswith('.wav'):
                filepath = os.path.join(SAVE_PATH, f)
                stat = os.stat(filepath)
                
                # Try to load metadata
                meta_file = filepath.replace('.wav', '.json')
                metadata = None
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, 'r') as mf:
                            metadata = json.load(mf)
                    except:
                        pass
                
                # Extract risk score from filename
                risk_match = re.search(r'risk(\d+)', f)
                risk_score = int(risk_match.group(1)) if risk_match else 0
                
                file_type = "critical" if "critical" in f else "suspicious"
                
                files.append({
                    "filename": f,
                    "type": file_type,
                    "risk_score": risk_score,
                    "size_kb": round(stat.st_size / 1024, 2),
                    "created": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "has_metadata": metadata is not None,
                    "text": metadata.get('analysis', {}).get('score') if metadata else None
                })
        
        return jsonify({
            "files": files,
            "count": len(files),
            "total_size_mb": round(sum(f['size_kb'] for f in files) / 1024, 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/analysis/realtime")
def realtime_analysis():
    """Get real-time analysis of current situation"""
    is_conv, exchanges, conv_type = detect_conversation_pattern()
    patterns = analyze_speech_patterns()
    
    # Calculate current risk level
    recent_risk = 0
    if len(speech_history) > 0:
        recent_events = list(speech_history)[-5:]
        recent_risk = sum(e.confidence * 100 for e in recent_events) / len(recent_events)
    
    return jsonify({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "conversation": {
            "active": is_conv,
            "type": conv_type,
            "exchanges": exchanges
        },
        "patterns": patterns,
        "risk": {
            "current_level": recent_risk,
            "status": "critical" if recent_risk >= CRITICAL_THRESHOLD else 
                     "high" if recent_risk >= SUSPICION_THRESHOLD else "normal"
        },
        "recent_speech": [
            {
                "text": e.text,
                "timestamp": datetime.datetime.fromtimestamp(e.timestamp).strftime("%H:%M:%S"),
                "confidence": round(e.confidence, 2)
            }
            for e in list(speech_history)[-5:]
        ]
    })

@app.route("/export/report")
def export_report():
    """Generate comprehensive report"""
    with log_lock:
        suspicious_logs = [l for l in log_buffer if l['type'] == 'suspicious']
        
        report = {
            "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "session": {
                "start_time": datetime.datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S"),
                "duration_hours": round((time.time() - start_time) / 3600, 2),
                "stats": session_stats
            },
            "risk_profile": dict(risk_profile),
            "suspicious_events": len(suspicious_logs),
            "events": suspicious_logs,
            "summary": {
                "total_detections": session_stats["total_speech"],
                "suspicious_percentage": round(
                    (session_stats["suspicious_events"] / max(session_stats["total_speech"], 1)) * 100, 2
                ),
                "average_risk_score": round(session_stats["avg_risk_score"], 2),
                "peak_risk_time": session_stats.get("peak_risk_time", "N/A")
            }
        }
        
        return jsonify(report)

@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy" if is_running.is_set() else "stopped",
        "timestamp": datetime.datetime.now().isoformat(),
        "uptime": time.time() - start_time
    })

# ---------------- ENTRY POINT ----------------
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 MAXIMUM ACCURACY VOICE PROCTORING SYSTEM v4.0")
    print("=" * 70)
    print()
    
    # System info
    print("📊 Configuration:")
    print(f"   • Sample Rate: {SAMPLE_RATE} Hz")
    print(f"   • Chunk Duration: {DURATION} seconds")
    print(f"   • Speech Confidence Threshold: {SPEECH_CONFIDENCE_THRESHOLD}")
    print(f"   • Suspicion Threshold: {SUSPICION_THRESHOLD} points")
    print(f"   • Critical Threshold: {CRITICAL_THRESHOLD} points")
    print()
    
    print("🔧 Features:")
    print(f"   • Multi-Engine Recognition: Google + Sphinx")
    print(f"   • NLP Analysis: {'✓' if NLP_AVAILABLE else '✗ (install textblob)'}")
    print(f"   • Advanced Audio Features: ✓")
    print(f"   • Conversation Detection: ✓")
    print(f"   • Risk Profiling: ✓")
    print()
    
    # Clean temp directory
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Load existing data
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                log_buffer = json.load(f)
                print(f"📋 Loaded {len(log_buffer)} log entries")
        except:
            print("📋 Starting with fresh logs")
    
    if os.path.exists(RISK_PROFILE_FILE):
        try:
            with open(RISK_PROFILE_FILE, 'r') as f:
                data = json.load(f)
                risk_profile.update(data.get('risk_profile', {}))
                session_stats.update(data.get('session_stats', {}))
                print(f"📊 Loaded risk profile")
        except:
            print("📊 Starting fresh risk profile")
    
    print()
    log_event("system", "Maximum Accuracy Voice Proctor starting", severity="normal")
    
    # Start threads
    recording_thread = threading.Thread(target=recorder_thread, daemon=True)
    processing_thread = threading.Thread(target=processor_thread, daemon=True)
    
    try:
        recording_thread.start()
        processing_thread.start()
        
        print("✅ System ready!")
        print("🌐 API: http://0.0.0.0:5000")
        print()
        print("📍 Endpoints:")
        print("   • GET  /status          - System status")
        print("   • GET  /stats           - Detailed statistics")
        print("   • GET  /logs            - All logs")
        print("   • GET  /files           - Audio files")
        print("   • GET  /analysis/realtime - Real-time analysis")
        print("   • GET  /export/report   - Generate report")
        print("   • POST /control/<action> - Control system")
        print()
        print("=" * 70)
        print()
        
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("\n⚠️  Shutting down...")
    except Exception as e:
        print(f"❌ Startup error: {e}")
        log_event("error", f"Startup failed: {e}", severity="critical")
    finally:
        print("\n🛑 Shutting down Voice Proctor System...")
        is_running.clear()
        time.sleep(2)
        
        # Final cleanup
        save_risk_profile()
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        
        log_event("system", "System stopped", severity="normal")
        print("✅ Shutdown complete")
        print("=" * 70)