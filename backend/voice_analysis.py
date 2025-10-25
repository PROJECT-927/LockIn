import speech_recognition as sr
import re
import os
import soundfile as sf
import io
import numpy as np

# --- Configuration ---
# Energy threshold to consider audio as potentially containing speech
# Adjust this based on microphone sensitivity and background noise.
# Higher value = less sensitive (ignores quieter sounds).
AUDIO_ENERGY_THRESHOLD = 0.008 # Example value, might need tuning

# Scoring thresholds
SUSPICION_THRESHOLD = 12
CRITICAL_THRESHOLD = 25

# Keywords and Patterns (keep these as they were)
KEYWORDS = {
    "answer": 10, "answers": 10, "solution": 10, "solutions": 10,
    "question": 7, "help": 7, "tell": 7, "google": 7, "search": 7,
    "phone": 7, "calculator": 7, "chatgpt": 7, "gpt": 7,
    "test": 5, "exam": 5, "quiz": 5, "option": 5, "choice": 5,
    "select": 5, "calculate": 5, "solve": 5,
    "what": 3, "how": 3, "why": 3, "send": 3, "give": 3,
    "show": 3, "find": 3, "check": 3, "define": 3,
    "explain": 3, "list": 3, "name": 3,
}
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

# --- Recognizer Setup ---
recognizer = sr.Recognizer()
# Keep energy_threshold relatively low here, as we do a pre-check
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = False
recognizer.pause_threshold = 0.8

# --- Helper Function: Fast Energy Check ---
def calculate_rms_energy(audio_data):
    """Calculates Root Mean Square energy of the audio chunk."""
    if audio_data is None or len(audio_data) == 0:
        return 0.0
    # Ensure data is float for calculation
    audio_float = audio_data.astype(np.float32)
    rms = np.sqrt(np.mean(audio_float**2))
    return rms

# --- Main Analysis Function ---
def analyze_audio_chunk(audio_data, samplerate):
    """
    Analyzes a single audio chunk (numpy array) and returns a status dict.
    Includes energy pre-check and detailed logging.
    """
    if audio_data is None or len(audio_data) == 0:
        print("DEBUG [Audio]: Received empty or None audio data.")
        return None

    # 1. Pre-check: Calculate energy
    energy = calculate_rms_energy(audio_data)
    print(f"DEBUG [Audio]: Analyzing chunk. Rate: {samplerate}, Samples: {len(audio_data)}, Energy: {energy:.6f}")

    # If energy is below threshold, assume silence and skip transcription
    if energy < AUDIO_ENERGY_THRESHOLD:
        print(f"DEBUG [Audio]: Chunk energy ({energy:.6f}) below threshold ({AUDIO_ENERGY_THRESHOLD}). Skipping transcription.")
        return None # Return None, indicating no suspicious speech detected

    # 2. Prepare audio data for SpeechRecognition
    virtual_file = io.BytesIO()
    try:
        # Write WAV data using the correct sample rate
        sf.write(virtual_file, audio_data, samplerate, format='WAV', subtype='PCM_16')
        virtual_file.seek(0)
        print("DEBUG [Audio]: Successfully wrote audio to virtual WAV file.")
    except Exception as e:
        print(f"ERROR [Audio]: Failed to write audio to virtual file: {e}")
        return None

    text = ""
    # 3. Transcribe using SpeechRecognition
    try:
        with sr.AudioFile(virtual_file) as source:
            print("DEBUG [Audio]: sr.AudioFile opened successfully.")
            # Optional: adjust_for_ambient_noise (can be slow, might not be needed with pre-check)
            # recognizer.adjust_for_ambient_noise(source, duration=0.5)

            try:
                print("DEBUG [Audio]: Attempting recognizer.record(source)...")
                audio_data_sr = recognizer.record(source) # Load audio file data
                print(f"DEBUG [Audio]: recognizer.record completed. Duration: {audio_data_sr.duration:.2f}s")

                print("DEBUG [Audio]: Attempting recognizer.recognize_google...")
                # Perform recognition
                text = recognizer.recognize_google(audio_data_sr, language='en-US').lower()
                print(f"DEBUG [Audio]: recognize_google successful. Text: '{text}'")

            except sr.WaitTimeoutError:
                print("DEBUG [Audio]: No speech detected within timeout by recognizer.record.")
                return None
            except sr.UnknownValueError:
                print("DEBUG [Audio]: Google Speech Recognition could not understand audio.")
                return None
            except sr.RequestError as e:
                print(f"ERROR [Audio]: Google Speech Recognition request failed; {e}")
                return None
            except Exception as e_rec:
                print(f"ERROR [Audio]: Unexpected error during speech recognition: {e_rec}")
                return None
    except Exception as e_file:
        print(f"ERROR [Audio]: Failed to process virtual audio file with sr.AudioFile: {e_file}")
        return None

    # Filter out very short/empty results
    if not text or len(text) < 3:
        print(f"DEBUG [Audio]: Transcription '{text}' too short/empty, ignoring.")
        return None

    # --- 4. Analysis Logic (Score calculation) ---
    score = 0
    keywords_found = []
    text_lower = text # Already lowercased

    # Keyword Scan (using word boundaries)
    for word, weight in KEYWORDS.items():
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            score += weight
            keywords_found.append(word)

    # Pattern Matching
    for pattern, pts in PATTERNS:
        if re.search(pattern, text_lower):
            score += pts
            if "pattern_match" not in keywords_found: keywords_found.append("pattern_match") # Generic marker

    # Simple Question Detection
    if text_lower.startswith(('what', 'how', 'why', 'can', 'could', 'is', 'are', 'do', 'does', 'tell me', 'explain', 'define')) or '?' in text:
        score += 5
        if "question_detected" not in keywords_found: keywords_found.append("question_detected")

    # Determine Risk Level
    if score >= CRITICAL_THRESHOLD:
        risk = "critical"
    elif score >= SUSPICION_THRESHOLD:
        risk = "high"
    else:
        # Even if score is low, we detected speech, so risk is 'low' not None
        risk = "low"

    analysis = {
        "score": score,
        "risk": risk,
        "keywords": keywords_found,
        "text": text
    }

    # Log analysis result only if speech was transcribed
    print(f"DEBUG [Audio]: Analysis Result -> Score={score}, Risk={risk}, Keywords={keywords_found}")
    return analysis