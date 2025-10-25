// src/pages/StudentExam.jsx
import React, { useRef, useEffect, useState } from 'react';
import io from 'socket.io-client';

// --- Central Backend Server URL ---
const SOCKET_SERVER_URL = 'http://localhost:8000';

// --- Webcam Component (Upgraded for Streaming Video & Audio) ---
const StudentVideoFeed = ({ studentId, socket }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef();
  const videoIntervalRef = useRef();
  const audioRecorderRef = useRef();
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null); // Keep track of the stream

  const styles = { /* ... styles ... */ 
      videoContainer: { width: '100%', borderRadius: '15px', overflow: 'hidden', backgroundColor: '#000', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)', position: 'sticky', top: '20px' },
      video: { width: '100%', height: 'auto', display: 'block' },
  };

  // Helper to take a snapshot (Base64 without prefix)
  const takeSnapshotB64 = () => {
    if (canvasRef.current && videoRef.current && videoRef.current.readyState >= 3) { // Check if video has data
      try {
        const context = canvasRef.current.getContext('2d');
        context.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);
        // Lower quality for faster transmission
        return canvasRef.current.toDataURL('image/jpeg', 0.5).split(',')[1]; 
      } catch (e) {
        console.error("Error taking snapshot:", e);
        return null;
      }
    }
    return null;
  };

  useEffect(() => {
    if (!socket || !studentId) return; // Wait for socket and ID

    canvasRef.current = document.createElement('canvas');

    const startStreaming = async () => {
      try {
        // Get both video and audio
        streamRef.current = await navigator.mediaDevices.getUserMedia({ 
          video: { width: 640, height: 480 }, 
          audio: true 
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = streamRef.current;
        }
        
        const videoTrack = streamRef.current.getVideoTracks()[0];
        const settings = videoTrack.getSettings();
        canvasRef.current.width = settings.width || 640;
        canvasRef.current.height = settings.height || 480;

        // --- 1. Video Frame Streaming ---
        // Send a frame every 2 seconds
        videoIntervalRef.current = setInterval(() => {
          const frameB64 = takeSnapshotB64();
          if (frameB64 && socket.connected) {
            socket.emit('video_frame', { 
              frame: frameB64,
              snapshot: frameB64 // Send snapshot explicitly for backend logic
            });
          }
        }, 2000); // 2 seconds interval

        // --- 2. Audio Chunk Streaming ---
        if (streamRef.current.getAudioTracks().length > 0) {
          audioRecorderRef.current = new MediaRecorder(streamRef.current, { mimeType: 'audio/webm' }); // Use webm or opus if available
          
          audioRecorderRef.current.ondataavailable = (event) => {
            if (event.data.size > 0) {
              audioChunksRef.current.push(event.data);
            }
          };

          // When a 10s chunk is ready, convert to Base64 and send
          audioRecorderRef.current.onstop = () => {
            if (audioChunksRef.current.length === 0) return;

            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = () => {
              const base64Audio = reader.result.split(',')[1];
              const snapshotB64 = takeSnapshotB64(); // Take snapshot when audio is sent

              if (socket.connected) {
                socket.emit('audio_chunk', {
                  audio: base64Audio, // Base64 audio
                  snapshot: snapshotB64 // Base64 snapshot
                });
              }
              audioChunksRef.current = []; // Clear for next chunk
            };
          };
          
          // Continuously record 10-second chunks
          audioRecorderRef.current.start(10000); 
          // Re-start recording when stopped (creates continuous loop)
          audioRecorderRef.current.addEventListener('stop', () => {
              if (audioRecorderRef.current && audioRecorderRef.current.state === 'inactive') {
                   audioRecorderRef.current.start(10000);
              }
          });
        } else {
            console.warn("No audio track available for recording.");
        }

      } catch (err) {
        console.error("Error accessing media devices:", err);
        alert("Could not access camera/microphone. Please check permissions and refresh.");
      }
    };

    startStreaming();

    // Clean up on unmount
    return () => {
      clearInterval(videoIntervalRef.current);
      if (audioRecorderRef.current && audioRecorderRef.current.state !== 'inactive') {
           audioRecorderRef.current.stop();
      }
      // Stop media tracks
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, [socket, studentId]); // Re-run if socket or studentId changes

  return (
    <div style={styles.videoContainer}>
      <video ref={videoRef} autoPlay playsInline muted style={styles.video} />
    </div>
  );
};

// --- Question Component (No changes) ---
const Question = ({ question, index, onAnswer, selectedOption }) => { /* ... JSX ... */ 
    const styles = { questionCard: { backgroundColor: 'white', borderRadius: '15px', padding: '25px', marginBottom: '20px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)' }, questionText: { fontSize: '18px', fontWeight: '600', color: '#333366', marginBottom: '20px' }, option: { display: 'block', padding: '15px', border: '1px solid #eee', borderRadius: '10px', marginBottom: '10px', cursor: 'pointer', transition: 'all 0.2s', backgroundColor: 'transparent' }, selectedOption: { backgroundColor: '#eef2ff', borderColor: '#4a70f0', fontWeight: '600' } };
    return ( <div style={styles.questionCard}> <p style={styles.questionText}>{index + 1}. {question.text}</p> <div> {question.options.map((opt, i) => ( <label key={i} style={{ ...styles.option, ...(selectedOption === i ? styles.selectedOption : {}) }} onClick={() => onAnswer(question.id, i)}> <input type="radio" name={`question-${question.id}`} checked={selectedOption === i} readOnly style={{ marginRight: '10px' }}/> {opt} </label> ))} </div> </div> );
};

// --- Main Student Exam Page ---
export default function StudentExam() {
  const [examQuestions, setExamQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [socket, setSocket] = useState(null); // Socket state
  const studentId = "student@test.com"; // Get from auth

  // --- Connect to Central Server ---
  useEffect(() => {
    const newSocket = io(SOCKET_SERVER_URL);
    setSocket(newSocket); // Store socket in state

    newSocket.emit('studentJoin', { studentId });

    newSocket.on('kick', (data) => {
        alert(`You have been kicked from the exam.\nReason: ${data.reason}`);
        newSocket.disconnect();
        window.location.href = '/student-login';
    });

    // Cleanup on unmount
    return () => newSocket.disconnect();
  }, [studentId]);

  // --- (Load Exam, Answer Logic - No Changes) ---
  useEffect(() => { /* load exam */ const savedExam = localStorage.getItem('hackathonExam'); if (savedExam) setExamQuestions(JSON.parse(savedExam)); }, []);
  const handleAnswerSelect = (questionId, optionIndex) => { /* ... */ setAnswers(prev => ({...prev,[questionId]: optionIndex}));};
  const handleSubmitExam = () => { /* ... */ if (Object.keys(answers).length !== examQuestions.length) { alert('Answer all questions.'); return; } let score = 0; examQuestions.forEach(q => { if (answers[q.id] === q.correct) score++; }); alert(`Submitted! Score: ${score} / ${examQuestions.length}`); };

  const styles = { /* ... styles ... */ 
      appBackground: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      margin: 0,
      padding: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #a8c0ff 0%, #3f63c8 100%)',
      fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      boxSizing: 'border-box',
      overflow: 'hidden', // prevents scrollbars due to minor layout issues
    },
      examContainer: { display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px', maxWidth: '1400px', margin: '0 auto' },
      questionsList: { backgroundColor: 'rgba(255, 255, 255, 0.8)', backdropFilter: 'blur(10px)', borderRadius: '20px', padding: '30px', maxHeight: 'calc(100vh - 80px)', overflowY: 'auto' },
      proctoringColumn: {},
      submitButton: { padding: '15px 30px', fontSize: '16px', fontWeight: '600', borderRadius: '10px', border: 'none', cursor: 'pointer', backgroundColor: '#28a745', color: 'white', width: '100%', marginTop: '20px' },
      errorBox: { backgroundColor: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb', borderRadius: '10px', padding: '15px', marginTop: '20px', fontSize: '14px', fontWeight: '600', textAlign: 'center' }
  };

  if (examQuestions.length === 0) { /* ... waiting message ... */ return ( <div style={{...styles.appBackground, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: '24px'}}> Waiting for exam... </div> ); }

  return (
    <div style={styles.appBackground}>
      <div style={styles.examContainer}>
        <div style={styles.questionsList}>
          <h1 style={{fontSize: '28px', fontWeight: '700', color: '#333366', marginBottom: '30px'}}>Exam in Progress</h1>
          {examQuestions.map((q, index) => ( <Question key={q.id} question={q} index={index} onAnswer={handleAnswerSelect} selectedOption={answers[q.id]} /> ))}
          <button style={styles.submitButton} onClick={handleSubmitExam}>Submit Exam</button>
        </div>
        <div style={styles.proctoringColumn}>
          {/* Pass socket and studentId to the video feed component */}
          {socket && <StudentVideoFeed studentId={studentId} socket={socket} />}
          <div style={{ backgroundColor: 'white', borderRadius: '15px', padding: '20px', marginTop: '20px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)' }}>
            <h3 style={{fontSize: '18px', fontWeight: '600', color: '#333366'}}>Proctoring Active</h3>
            <p style={{fontSize: '14px', color: '#555', marginTop: '10px'}}>
              Your camera and microphone are being monitored.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}