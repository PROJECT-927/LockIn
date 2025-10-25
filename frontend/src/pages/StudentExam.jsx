// src/pages/StudentExam.jsx
import React, { useRef, useEffect, useState } from 'react';
import io from 'socket.io-client';

// --- Central Backend Server URL ---
const SOCKET_SERVER_URL = 'http://localhost:8000';

// --- Webcam Component ---
const StudentVideoFeed = ({ studentId, socket }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null); // Changed: Initialize directly
  const videoIntervalRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);

  const styles = {
    videoContainer: { width: '100%', borderRadius: '15px', overflow: 'hidden', backgroundColor: '#000', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)', position: 'sticky', top: '20px' },
    video: { width: '100%', height: 'auto', display: 'block' },
  };

  // Helper to take a snapshot (Base64 without prefix)
  const takeSnapshotB64 = () => {
    if (canvasRef.current && videoRef.current && videoRef.current.readyState >= 3 && !videoRef.current.paused) {
      try {
        const context = canvasRef.current.getContext('2d');
        // Ensure canvas size matches video intrinsic size *after* metadata loaded
        if (videoRef.current.videoWidth > 0 && videoRef.current.videoHeight > 0) {
            canvasRef.current.width = videoRef.current.videoWidth;
            canvasRef.current.height = videoRef.current.videoHeight;
        } else {
            // Fallback size if dimensions aren't ready (less ideal)
             canvasRef.current.width = 640;
             canvasRef.current.height = 480;
        }

        context.drawImage(videoRef.current, 0, 0, canvasRef.current.width, canvasRef.current.height);
        // Use JPEG with quality adjustment for snapshots
        return canvasRef.current.toDataURL('image/jpeg', 0.6).split(',')[1]; // Quality 0.6
      } catch (e) {
        console.error("Error taking snapshot:", e);
        return null;
      }
    }
    // console.warn("Snapshot skipped: Video not ready or canvas missing."); // DEBUG - Can be noisy
    return null;
  };

  useEffect(() => {
    if (!socket || !studentId) {
        console.log("DEBUG [Student]: Socket or studentId missing, delaying stream start.");
        return; // Wait for socket and ID
    }

    // Initialize canvas here
    canvasRef.current = document.createElement('canvas');
    console.log("DEBUG [Student]: Canvas created.");

    let localStream = null; // Variable to hold the stream for cleanup

    const startStreaming = async () => {
      console.log("DEBUG [Student]: Attempting to get user media (video & audio)...");
      try {
        localStream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 },
          audio: true // Request audio
        });
        streamRef.current = localStream; // Store stream in ref
        console.log("DEBUG [Student]: Got user media stream.");

        if (videoRef.current) {
          videoRef.current.srcObject = localStream;
          videoRef.current.onloadedmetadata = () => { // Wait for metadata
             console.log("DEBUG [Student]: Video metadata loaded.");
             // Set initial canvas size based on video dimensions
             if (videoRef.current && canvasRef.current) {
                canvasRef.current.width = videoRef.current.videoWidth || 640;
                canvasRef.current.height = videoRef.current.videoHeight || 480;
                console.log(`DEBUG [Student]: Initial canvas size set to ${canvasRef.current.width}x${canvasRef.current.height}`);
             }
          };
        } else {
             console.warn("DEBUG [Student]: videoRef.current is null when setting srcObject.");
        }

        // --- Video Frame Streaming ---
        console.log("DEBUG [Student]: Setting up video frame interval (2 seconds)...");
        // Clear any previous interval first
        if(videoIntervalRef.current) clearInterval(videoIntervalRef.current);
        videoIntervalRef.current = setInterval(() => {
          if (!socket || !socket.connected) {
             console.warn("DEBUG [Student]: Video frame skipped, socket not connected.");
             return;
          }
          const frameB64 = takeSnapshotB64();
          if (frameB64) {
            // console.log("DEBUG [Student]: Emitting video_frame..."); // Noisy
            socket.emit('video_frame', {
              frame: frameB64,
              snapshot: frameB64 // Explicitly send snapshot
            });
          }
        }, 2000); // Send frame every 2 seconds

        // --- Audio Chunk Streaming ---
        if (localStream.getAudioTracks().length > 0) {
          console.log("DEBUG [Student]: Audio track found. Setting up MediaRecorder...");
          try {
            // Stop existing recorder if any
            if (audioRecorderRef.current && audioRecorderRef.current.state !== 'inactive') {
                audioRecorderRef.current.stop();
            }

            // Create new recorder - explicitly use WAV
            const options = { mimeType: 'audio/webm' };
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                console.warn(`WARN [Student]: ${options.mimeType} not supported. Trying default.`);
                delete options.mimeType; // Fallback to browser default (might be webm/opus)
            }
            audioRecorderRef.current = new MediaRecorder(localStream, options);
            audioChunksRef.current = []; // Reset chunks

            audioRecorderRef.current.ondataavailable = (event) => {
            //   console.log("DEBUG [Student]: Audio data available, size:", event.data.size); // Noisy
              if (event.data.size > 0) {
                audioChunksRef.current.push(event.data);
              }
            };

            audioRecorderRef.current.onstop = () => {
              console.log("DEBUG [Student]: MediaRecorder stopped. Processing chunks:", audioChunksRef.current.length);
              if (audioChunksRef.current.length === 0 || !socket || !socket.connected) {
                  console.warn("DEBUG [Student]: Audio chunk processing skipped (no chunks or socket disconnected).");
                  // Don't restart if socket is gone
                  if (audioRecorderRef.current && socket && socket.connected) {
                     // If stopped unexpectedly, try restarting after a short delay
                     // setTimeout(() => {
                     //     if (audioRecorderRef.current && audioRecorderRef.current.state === 'inactive') {
                     //         try { audioRecorderRef.current.start(10000); } catch(e){ console.error("Error restarting recorder:", e); }
                     //     }
                     // }, 500);
                  }
                  audioChunksRef.current = []; // Clear anyway
                  return;
              }

              // Use correct mimeType based on what was chosen
              const blobMimeType = audioRecorderRef.current.mimeType || 'audio/webm';
              const audioBlob = new Blob(audioChunksRef.current, { type: blobMimeType });
              audioChunksRef.current = []; // Clear chunks immediately

              const reader = new FileReader();
              reader.readAsDataURL(audioBlob);
              reader.onloadend = () => {
                const base64Audio = reader.result.split(',')[1];
                const snapshotB64 = takeSnapshotB64(); // Take snapshot when audio chunk is ready

                // *** ADD LOGGING HERE ***
                console.log(`DEBUG [Student]: Emitting audio_chunk... (Audio length: ${base64Audio?.length || 0}, Snapshot length: ${snapshotB64?.length || 0})`);
                socket.emit('audio_chunk', {
                  audio: base64Audio,
                  snapshot: snapshotB64
                });

                // Restart recording ONLY if it was stopped normally (not by cleanup)
                if (audioRecorderRef.current && audioRecorderRef.current.state === 'inactive') {
                    try {
                         console.log("DEBUG [Student]: Restarting MediaRecorder...");
                         audioRecorderRef.current.start(10000); // Restart for the next chunk
                    } catch (e) {
                        console.error("ERROR [Student]: Failed to restart MediaRecorder:", e)
                    }
                }
              };
               reader.onerror = (err) => {
                    console.error("ERROR [Student]: FileReader failed:", err);
                     // Still try to restart recording
                    if (audioRecorderRef.current && audioRecorderRef.current.state === 'inactive') {
                         try { audioRecorderRef.current.start(10000); } catch(e){ console.error("Error restarting recorder:", e); }
                    }
               }
            };

            // Start recording chunks (e.g., 10 seconds)
            console.log("DEBUG [Student]: Starting MediaRecorder (10 second chunks)...");
            audioRecorderRef.current.start(10000);

          } catch (recorderError) {
              console.error("ERROR [Student]: Failed to create or start MediaRecorder:", recorderError);
              // Handle specific errors like NotSupportedError if mimeType is bad
              alert("Could not start audio recording. Please ensure your browser supports WAV recording or try a different browser.");
          }

        } else {
          console.warn("WARN [Student]: No audio track available in the stream.");
          alert("Audio track not found. Microphone might not be working or permitted.");
        }

      } catch (err) {
        console.error("ERROR [Student]: Error accessing media devices:", err.name, err.message);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
             alert("Camera/Microphone access was denied. Please allow access in browser settings and refresh.");
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError'){
             alert("No camera/microphone found. Please ensure they are connected and enabled.");
        } else {
             alert(`Could not access camera/microphone: ${err.message}. Please check permissions and refresh.`);
        }
      }
    };

    startStreaming();

    // Clean up function
    return () => {
      console.log("DEBUG [Student]: Cleaning up StudentVideoFeed component...");
      clearInterval(videoIntervalRef.current);
      videoIntervalRef.current = null;

      if (audioRecorderRef.current && audioRecorderRef.current.state !== 'inactive') {
        console.log("DEBUG [Student]: Stopping MediaRecorder...");
        // Remove listeners before stopping to prevent restart logic during cleanup
        audioRecorderRef.current.onstop = null;
        audioRecorderRef.current.ondataavailable = null;
        try {
            audioRecorderRef.current.stop();
        } catch (e) {
            console.warn("WARN [Student]: Error stopping MediaRecorder (might already be stopped):", e);
        }

      }
       audioRecorderRef.current = null;
       audioChunksRef.current = []; // Clear any remaining chunks


      // Stop media tracks
      if (streamRef.current) { // Use the stored stream ref
        console.log("DEBUG [Student]: Stopping media stream tracks...");
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null; // Clear the ref
      } else {
        console.log("DEBUG [Student]: No active media stream found to stop.");
      }

       // Clear video src
       if (videoRef.current) {
           videoRef.current.srcObject = null;
       }
        console.log("DEBUG [Student]: Cleanup complete.");
    };
  }, [socket, studentId]); // Re-run effect if socket or studentId changes

  return (
    <div style={styles.videoContainer}>
      <video ref={videoRef} autoPlay playsInline muted style={styles.video} />
      {/* Canvas is now created in useEffect, not rendered */}
    </div>
  );
};

// --- Question Component (No changes) ---
const Question = ({ question, index, onAnswer, selectedOption }) => {
    const styles = { questionCard: { backgroundColor: 'white', borderRadius: '15px', padding: '25px', marginBottom: '20px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)' }, questionText: { fontSize: '18px', fontWeight: '600', color: '#333366', marginBottom: '20px' }, option: { display: 'block', padding: '15px', border: '1px solid #eee', borderRadius: '10px', marginBottom: '10px', cursor: 'pointer', transition: 'all 0.2s', backgroundColor: 'transparent' }, selectedOption: { backgroundColor: '#eef2ff', borderColor: '#4a70f0', fontWeight: '600' } };
    return ( <div style={styles.questionCard}> <p style={styles.questionText}>{index + 1}. {question.text}</p> <div> {question.options.map((opt, i) => ( <label key={i} style={{ ...styles.option, ...(selectedOption === i ? styles.selectedOption : {}) }} onClick={() => onAnswer(question.id, i)}> <input type="radio" name={`question-${question.id}`} checked={selectedOption === i} onChange={() => {}} /* Add onChange handler */ style={{ marginRight: '10px' }}/> {opt} </label> ))} </div> </div> );
};


// --- Main Student Exam Page ---
export default function StudentExam() {
  const [examQuestions, setExamQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false); // Track connection status
  const [errorState, setErrorState] = useState(null); // Track critical errors
  const studentId = "student@test.com"; // Get from auth context in real app

  // --- Connect to Central Server ---
  useEffect(() => {
    console.log("DEBUG [Student]: StudentExam component mounting. Setting up socket...");
    const newSocket = io(SOCKET_SERVER_URL, {
        reconnectionAttempts: 3,
        timeout: 5000,
    });
    setSocket(newSocket); // Store socket instance

    newSocket.on('connect', () => {
      console.log("DEBUG [Student]: Socket connected. Emitting studentJoin...");
      setIsConnected(true);
      setErrorState(null); // Clear previous errors on connect
      newSocket.emit('studentJoin', { studentId });
    });

    newSocket.on('disconnect', (reason) => {
      console.warn("DEBUG [Student]: Socket disconnected:", reason);
      setIsConnected(false);
      // Optional: Show a message indicating disconnection
      setErrorState(`Disconnected from server: ${reason}. Attempting to reconnect...`);
      // No need to manually reconnect, io client handles it based on options
    });

     newSocket.on('connect_error', (err) => {
        console.error("DEBUG [Student]: Connection Error:", err.message);
        setIsConnected(false);
        setErrorState(`Connection failed: ${err.message}. Please check server and refresh.`);
     });

    newSocket.on('kick', (data) => {
      console.warn("DEBUG [Student]: Received kick event:", data);
      alert(`You have been kicked from the exam.\nReason: ${data.reason || 'No reason specified.'}`);
      setErrorState(`Kicked from exam: ${data.reason || 'No reason specified.'}`); // Show error state
      newSocket.disconnect(); // Explicitly disconnect
      // Redirect after a short delay to allow alert to be seen
      // setTimeout(() => { window.location.href = '/student-login'; }, 3000);
    });

    // --- Load Exam Questions ---
    try {
        const savedExam = localStorage.getItem('hackathonExam');
        if (savedExam) {
            const parsedExam = JSON.parse(savedExam);
            setExamQuestions(parsedExam);
            console.log("DEBUG [Student]: Loaded exam questions from localStorage:", parsedExam.length);
        } else {
             console.warn("DEBUG [Student]: No exam found in localStorage.");
             setErrorState("No exam questions found. Please ask the admin to publish an exam.");
        }
    } catch(e) {
         console.error("ERROR [Student]: Failed to load/parse exam from localStorage:", e);
         setErrorState("Error loading exam questions.");
    }


    // Cleanup on unmount
    return () => {
      console.log("DEBUG [Student]: StudentExam component unmounting. Disconnecting socket...");
      if (newSocket) {
          newSocket.disconnect();
      }
      setSocket(null); // Clear socket state
      setIsConnected(false);
    };
  }, [studentId]); // Rerun if studentId changes (e.g., on login)


  // --- Answer Handling ---
  const handleAnswerSelect = (questionId, optionIndex) => {
    setAnswers(prev => ({ ...prev, [questionId]: optionIndex }));
  };

  const handleSubmitExam = () => {
    if (Object.keys(answers).length !== examQuestions.length) {
      alert('Please answer all questions before submitting.');
      return;
    }
    let score = 0;
    examQuestions.forEach(q => {
      // Ensure correct comparison (e.g., index vs index)
      if (answers[q.id] === q.correct) {
        score++;
      }
    });
    const percentage = ((score / examQuestions.length) * 100).toFixed(1);
    alert(`Exam Submitted!\nYour Score: ${score} / ${examQuestions.length} (${percentage}%)`);
    // Optionally: Send results to backend, disconnect socket, redirect
    if(socket) socket.disconnect();
    // window.location.href = '/student-login'; // Example redirect
  };

  // --- Styles ---
  const styles = {
    appBackground: {
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, margin: 0, padding: '40px',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center', // Align top
        background: 'linear-gradient(135deg, #a8c0ff 0%, #3f63c8 100%)',
        fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif", boxSizing: 'border-box', overflowY: 'auto' // Allow vertical scroll for exam content
    },
    examContainer: { display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px', maxWidth: '1400px', width: '100%', margin: '0 auto' },
    questionsList: { backgroundColor: 'rgba(255, 255, 255, 0.9)', backdropFilter: 'blur(5px)', borderRadius: '20px', padding: '30px', maxHeight: 'calc(100vh - 120px)' /* Adjust based on padding */, overflowY: 'auto' },
    proctoringColumn: {},
    submitButton: { padding: '15px 30px', fontSize: '16px', fontWeight: '600', borderRadius: '10px', border: 'none', cursor: 'pointer', backgroundColor: '#28a745', color: 'white', width: '100%', marginTop: '20px', transition: 'background-color 0.2s' },
    submitButtonHover: { backgroundColor: '#218838' },
    statusBox: { backgroundColor: 'rgba(255, 255, 255, 0.9)', borderRadius: '15px', padding: '20px', marginTop: '20px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)', textAlign: 'center' },
    statusText: { fontSize: '14px', color: '#555', marginTop: '10px' },
    statusTitle: { fontSize: '18px', fontWeight: '600', color: '#333366', marginBottom: '10px' },
    errorBox: { backgroundColor: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb', borderRadius: '10px', padding: '15px', marginTop: '20px', fontSize: '14px', fontWeight: '600', textAlign: 'center' },
    loadingBox: { padding: '50px', textAlign: 'center', color: 'white', fontSize: '24px', fontWeight: '600'}
  };


  // --- Render Logic ---
  if (errorState) {
       return (
           <div style={{...styles.appBackground, alignItems: 'center'}}>
               <div style={styles.errorBox}>{errorState}</div>
           </div>
       );
   }

  if (examQuestions.length === 0) {
    return (
        <div style={{...styles.appBackground, alignItems: 'center'}}>
            <div style={styles.loadingBox}>Waiting for exam questions...</div>
        </div>
    );
   }


  return (
    <div style={styles.appBackground}>
      <div style={styles.examContainer}>
        {/* Questions Column */}
        <div style={styles.questionsList}>
          <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#333366', marginBottom: '30px' }}>Exam in Progress</h1>
          {examQuestions.map((q, index) => (
            <Question key={q.id} question={q} index={index} onAnswer={handleAnswerSelect} selectedOption={answers[q.id]} />
          ))}
          <button
             style={styles.submitButton}
             onClick={handleSubmitExam}
             onMouseEnter={(e) => e.currentTarget.style.backgroundColor = styles.submitButtonHover.backgroundColor}
             onMouseLeave={(e) => e.currentTarget.style.backgroundColor = styles.submitButton.backgroundColor}
          >
              Submit Exam
          </button>
        </div>

        {/* Proctoring Column */}
        <div style={styles.proctoringColumn}>
          {/* Only render video feed if socket is connected */}
          {socket && isConnected ? (
              <StudentVideoFeed studentId={studentId} socket={socket} />
          ) : (
              <div style={styles.statusBox}> {/* Placeholder/Status box */}
                  <h3 style={styles.statusTitle}>Connecting...</h3>
                  <p style={styles.statusText}>Attempting to connect to the proctoring server.</p>
              </div>
          )}

          <div style={styles.statusBox}>
            <h3 style={styles.statusTitle}>Proctoring Status</h3>
            <p style={styles.statusText}>
              {isConnected ? "Monitoring active. Your camera and microphone are being monitored." : "Not connected to proctoring server."}
            </p>
             {/* Add more status info here if needed */}
          </div>
        </div>
      </div>
    </div>
  );
}