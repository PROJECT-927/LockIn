// src/pages/AdminDashboard.jsx
import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import {
  FiHome, FiClipboard, FiUsers, FiBarChart2, FiSettings,
  FiBell, FiUser, FiSearch, FiAlertTriangle, FiAlertCircle, FiX,
  FiCheckCircle, FiUserX, FiPlus, FiInfo, FiVolume2 // Added FiVolume2 for audio alerts
} from 'react-icons/fi';

// --- Central Backend Server URL ---
const SOCKET_SERVER_URL = 'http://localhost:8000'; // Make sure this matches your server

// --- Modal Component (Updated for Impersonation Alert) ---
const StudentDetailModal = ({ student, onClose, onKickStudent, styles, latestAlert }) => {
    // student = { id, score, status, snapshot, sid, wallpaperB64 } // Updated expected props
    // latestAlert = the alert object { ..., snapshot, audioFilename }
    const isImpersonation = student.status && student.status.includes('IMPERSONATION');
    // Consider other potential critical states if needed
    const isOtherCritical = !isImpersonation && student.status && (student.status.includes('CRITICAL') || student.status.includes('Multiple Faces') || student.status === 'Away'); // Include Away?
    const isCritical = isImpersonation || isOtherCritical; // General critical flag

    const audioFilename = latestAlert?.audioFilename;
    const alertSnapshot = latestAlert?.snapshot; // Snapshot associated with the alert trigger

    const handleConfirmKick = () => { onKickStudent(student.id); };

    // Fallback image source or placeholder component
    const ImageWithErrorFallback = ({ src, alt, style, fallbackText }) => {
        const [imgSrc, setImgSrc] = useState(src);
        const handleError = () => {
            setImgSrc(null); // Set to null or a placeholder image URL
        };
        if (!imgSrc) {
            return <div style={{...style, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888', backgroundColor: '#eee'}}>{fallbackText || "Image unavailable"}</div>;
        }
        return <img src={imgSrc} alt={alt} style={style} onError={handleError} />;
    };


    return (
        <div style={styles.modalBackdrop} onClick={onClose}>
            {/* Adjust width based on content */}
            <div style={{...styles.modalContent, maxWidth: (isImpersonation || audioFilename) ? '850px' : '700px'}} onClick={(e) => e.stopPropagation()}>
                <div style={styles.modalHeader}>
                    <h2 style={styles.modalTitle}>Student Details: {student.id}</h2>
                    <button style={styles.modalCloseButton} onClick={onClose}><FiX /></button>
                </div>

                {/* --- IMPERSONATION ALERT SECTION --- */}
                {isImpersonation ? (
                    <div style={{...styles.modalBody, gridTemplateColumns: '1fr 1fr'}}> {/* Ensure 2 columns */}
                        {/* Impersonation Banner */}
                        <div style={{ ...styles.modalSection, gridColumn: '1 / -1', ...styles.criticalAlertBox, marginBottom: '15px' }}>
                            <FiAlertTriangle style={{ fontSize: '24px', marginRight: '10px' }} />
                            <h3 style={styles.modalSectionTitle}>IMPERSONATION ALERT</h3>
                        </div>
                        <p style={{ ...styles.modalStat, gridColumn: '1 / -1', marginTop: '-10px', marginBottom: '20px' }}>
                            System detected a potential face swap. Please review the images below and confirm.
                        </p>

                        {/* Baseline Photo */}
                        <div style={styles.modalSection}>
                            <h4 style={styles.modalPhotoLabel}>Baseline Photo (Start of Exam)</h4>
                            <ImageWithErrorFallback
                                // Use wallpaperB64 for the baseline photo
                                src={student.wallpaperB64 ? `data:image/jpeg;base64,${student.wallpaperB64}` : null}
                                alt="Reference Snapshot"
                                style={styles.modalPhoto}
                                fallbackText="Reference image unavailable"
                             />
                        </div>

                        {/* New Snapshot */}
                        <div style={styles.modalSection}>
                            <h4 style={styles.modalPhotoLabel}>New Snapshot (From Alert)</h4>
                             <ImageWithErrorFallback
                                src={alertSnapshot ? `data:image/jpeg;base64,${alertSnapshot}` : null}
                                alt="Alert Snapshot"
                                style={styles.modalPhoto}
                                fallbackText="Alert snapshot unavailable"
                             />
                        </div>

                        {/* Action Buttons */}
                        <div style={styles.modalActionButtons}>
                            <button style={{ ...styles.modalButton, ...styles.modalButtonConfirm }} onClick={handleConfirmKick}>
                                <FiUserX style={{ marginRight: '5px' }} /> Confirm & Kick Student
                            </button>
                            <button style={{ ...styles.modalButton, ...styles.modalButtonIgnore }} onClick={onClose}>
                                <FiCheckCircle style={{ marginRight: '5px' }} /> False Alarm (Ignore)
                            </button>
                        </div>
                    </div>
                ) :
                /* --- OTHER CRITICAL ALERT (e.g., Audio, Multiple Faces) --- */
                isOtherCritical ? (
                    <div style={styles.modalBody}>
                       <div style={{ ...styles.modalSection, ...styles.criticalAlertBox }}>
                         <FiAlertTriangle style={{ fontSize: '24px', marginRight: '10px' }} />
                         <h3 style={styles.modalSectionTitle}>ALERT DETECTED</h3>
                       </div>
                       <p style={{ ...styles.modalStat, gridColumn: '1 / -1', fontWeight: 'bold' }}>{student.status}. Review details.</p>

                       {/* AUDIO PLAYER (If alert has audio) */}
                       {audioFilename && (
                          <div style={{...styles.modalSection, gridColumn: '1 / -1', marginTop: '-15px'}}>
                              <h4 style={styles.modalPhotoLabel}>Suspicious Audio Clip:</h4>
                              <audio controls controlsList="nodownload nofullscreen noremoteplayback" style={{ width: '100%' }}>
                                  {/* Add timestamp to src to force reload if filename is the same */}
                                  <source src={`${SOCKET_SERVER_URL}/audio/${audioFilename}?t=${Date.now()}`} type="audio/wav" />
                                  Your browser does not support the audio element. File: {audioFilename}
                              </audio>
                          </div>
                       )}

                       {/* Snapshot from Alert */}
                       <div style={styles.modalSection}>
                         <h4 style={styles.modalPhotoLabel}>Snapshot (From Alert Time)</h4>
                          <ImageWithErrorFallback
                             src={(alertSnapshot || student.snapshot) ? `data:image/jpeg;base64,${alertSnapshot || student.snapshot}` : null}
                             alt="Alert Snapshot"
                             style={styles.modalPhoto}
                             fallbackText="Snapshot unavailable"
                          />
                       </div>
                       {/* Current Status */}
                       <div style={styles.modalSection}>
                         <h4 style={styles.modalPhotoLabel}>Current Status</h4>
                          <p style={styles.modalStat}><strong>Status:</strong> {student.status}</p>
                          <p style={styles.modalStat}><strong>Score:</strong> {student.score}%</p>
                          {latestAlert?.text && <p style={styles.modalStat}><strong>Alert Detail:</strong> {latestAlert.text.replace(student.id + ": ", "")}</p>}
                       </div>
                       {/* Action Buttons */}
                       <div style={styles.modalActionButtons}>
                         <button style={{ ...styles.modalButton, ...styles.modalButtonConfirm }} onClick={handleConfirmKick}>
                           <FiUserX style={{ marginRight: '5px' }} /> Confirm & Kick
                         </button>
                         <button style={{ ...styles.modalButton, ...styles.modalButtonIgnore }} onClick={onClose}>
                           <FiCheckCircle style={{ marginRight: '5px' }} /> False Alarm / Ignore
                         </button>
                       </div>
                    </div>
                ) : (
                    // --- NORMAL (Non-Critical) MODAL ---
                    <div style={styles.modalBody}>
                       {/* Snapshot Section */}
                       <div style={styles.modalSection}>
                         <h3 style={styles.modalSectionTitle}>Latest Snapshot</h3>
                         {/* Show latest snapshot available (could be from alert or general state) */}
                          <ImageWithErrorFallback
                             src={(alertSnapshot || student.snapshot) ? `data:image/jpeg;base64,${alertSnapshot || student.snapshot}` : null}
                             alt={student.id}
                             style={{...styles.feedItem, height: 'auto', width: '100%'}}
                             fallbackText="Waiting for snapshot..."
                          />
                       </div>
                       {/* Stats Section */}
                       <div style={styles.modalSection}>
                         <h3 style={styles.modalSectionTitle}>Focus Statistics</h3>
                         <p style={styles.modalStat}><strong>Current Score:</strong> {student.score}%</p>
                         <p style={styles.modalStat}><strong>Status:</strong> {student.status}</p>
                         {latestAlert?.text && <p style={styles.modalStat}><strong>Last Alert:</strong> {latestAlert.text.replace(student.id + ": ", "")}</p>}

                         {/* Audio Player (if last alert had audio) */}
                         {audioFilename && (
                           <div style={{marginTop: '15px'}}>
                               <h4 style={styles.modalPhotoLabel}>Last Suspicious Audio:</h4>
                               <audio controls controlsList="nodownload nofullscreen noremoteplayback" style={{ width: '100%' }}>
                                   {/* Add timestamp to src to force reload */}
                                   <source src={`${SOCKET_SERVER_URL}/audio/${audioFilename}?t=${Date.now()}`} type="audio/wav" />
                                   Your browser does not support the audio element.
                               </audio>
                           </div>
                         )}
                       </div>
                       {/* Manual kick button */}
                       <div style={{...styles.modalActionButtons, gridColumn: '1 / -1'}}>
                           <button style={{ ...styles.modalButton, ...styles.modalButtonConfirm, flex: '0 1 auto', padding: '10px 20px' }} onClick={handleConfirmKick}>
                               <FiUserX style={{ marginRight: '5px' }} /> Manually Kick Student
                           </button>
                       </div>
                    </div>
                )}
            </div>
        </div>
    );
};


// --- Create Exam Form (NO CHANGES) ---
const CreateExamForm = ({ styles, socket }) => {
  const [questions, setQuestions] = useState([]); const [currentQ, setCurrentQ] = useState(''); const [options, setOptions] = useState(['', '', '', '']); const [correctAnswer, setCorrectAnswer] = useState(0);
  const handleOptionChange = (index, value) => { const newOptions = [...options]; newOptions[index] = value; setOptions(newOptions); };
  const handleAddQuestion = () => { if (!currentQ || options.some(opt => !opt.trim())) { alert("Please fill in the question and all options."); return; } const newQuestion = { id: Date.now(), text: currentQ, options: options, correct: correctAnswer }; setQuestions([...questions, newQuestion]); setCurrentQ(''); setOptions(['', '', '', '']); setCorrectAnswer(0); };
  const handleSaveExam = () => { if (!socket) { alert("Not connected to server."); return; } socket.emit('adminPublishExam', { questions: questions }); alert(`Exam Published! ${questions.length} questions sent to students.`); setQuestions([]); };
  return ( <div style={styles.examFormContainer}> <div style={styles.panel}> <h3 style={styles.panelTitle}>Create New Exam</h3> <div style={styles.formGroup}> <label style={styles.formLabel}>Question Text</label> <input type="text" style={styles.formInput} value={currentQ} onChange={(e) => setCurrentQ(e.target.value)} placeholder="e.g., What is 2 + 2?" /> </div> {options.map((opt, index) => ( <div style={styles.formGroup} key={index}> <label style={styles.formLabel}>Option {index + 1} (Mark correct)</label> <div style={{ display: 'flex', alignItems: 'center' }}> <input type="radio" name="correctAnswer" checked={correctAnswer === index} onChange={() => setCorrectAnswer(index)} style={{ marginRight: '10px', height: '18px', width: '18px' }} /> <input type="text" style={styles.formInput} value={opt} onChange={(e) => handleOptionChange(index, e.target.value)} placeholder={`Option ${index + 1}`} /> </div> </div> ))} <button style={{ ...styles.modalButton, ...styles.modalButtonIgnore, width: 'auto', marginTop: '10px', backgroundColor: '#007bff', '&:hover': { backgroundColor: '#0056b3'} }} onClick={handleAddQuestion}> <FiPlus style={{ marginRight: '5px' }} /> Add Question </button> </div> <div style={styles.panel}> <h3 style={styles.panelTitle}>Current Exam Questions ({questions.length})</h3> <div style={{ maxHeight: 'calc(100vh - 450px)', overflowY: 'auto', border: '1px solid #eee', padding: '10px', borderRadius: '8px' }}> {questions.map((q, index) => ( <div key={q.id} style={styles.questionPreview}><strong>{index + 1}. {q.text}</strong><small> (Correct: Option {q.correct + 1})</small></div> ))} {questions.length === 0 && <p style={styles.modalStat}>No questions added yet.</p>} </div> <button style={{ ...styles.modalButton, ...styles.modalButtonConfirm, marginTop: '20px', backgroundColor: '#28a745', '&:hover': { backgroundColor: '#1e7e34'} }} onClick={handleSaveExam} disabled={questions.length === 0}> Publish Exam to Students </button> </div> </div> );
};

// --- Main Dashboard Component ---
const AdminDashboard = () => {
  const [activeNav, setActiveNav] = useState('Home');
  const [selectedStudent, setSelectedStudent] = useState(null); // Student ID for modal
  const [alerts, setAlerts] = useState([]);
  const [students, setStudents] = useState({});
  const [styles, setStyles] = useState(createStyles());
  const socketRef = useRef(null);

  // --- Connect to Backend and Listen ---
  useEffect(() => {
    if (socketRef.current) return;
    socketRef.current = io(SOCKET_SERVER_URL);
    socketRef.current.on('connect', () => { console.log("Connected."); socketRef.current.emit('adminJoin'); });
    socketRef.current.on('disconnect', () => console.log("Disconnected."));

    socketRef.current.on('student_list', (studentList) => {
      console.log("Received initial student list:", studentList);
      setStudents(prev => {
        const newStudents = {};
        studentList.forEach(student => { if (student && student.id) newStudents[student.id] = student; });
        return newStudents;
      });
    });
    socketRef.current.on('new_student', (student) => {
       console.log("New student:", student);
       if (student && student.id) setStudents(prev => ({ ...prev, [student.id]: student }));
    });
    socketRef.current.on('student_left', (data) => {
      console.log("Student left:", data);
      if (data && data.student_id) {
          setStudents(prev => { const ns = { ...prev }; delete ns[data.student_id]; return ns; });
          setSelectedStudent(prevId => (prevId === data.student_id ? null : prevId));
      }
    });

    socketRef.current.on('student_update', (data) => {
       // 'data' IS the student object, e.g., { id: 'student1', score: 95, ... }
       
       // 1. Check if the data payload has an 'id' field
       if (!data || !data.id) return; 

       const studentId = data.id; // 2. The key is data.id

       setStudents(prevStudents => {
            // 3. Check if that student exists in our *current* state
            if (prevStudents[studentId]) {
                // 4. Return the new state object
                return {
                    ...prevStudents,
                    // 5. Merge the new 'data' object with the existing student data
                    [studentId]: { ...prevStudents[studentId], ...data }
                };
            } else {
                // This student isn't in our list yet, ignore the update
                // (The 'new_student' event will handle adding them)
                return prevStudents; 
            }
       });
    });


    socketRef.current.on('new_alert', (alert) => {
        console.log("New alert:", alert);
        if (alert && alert.id) {
             let Icon = FiBell;
             if (alert.audio_filename) Icon = FiVolume2; // Prioritize audio icon
             else if (alert.color === '#dc3545') Icon = FiAlertTriangle;
             else if (alert.color === '#ffc107') Icon = FiAlertCircle;
             else if (alert.color === '#17a2b8') Icon = FiInfo;

             const alertData = { ...alert, Icon: Icon, audioFilename: alert.audio_filename || null };
             setAlerts(prev => [alertData, ...prev].slice(0, 15));

             // Auto-open modal for CRITICAL alerts
             if (alert.text && alert.color === '#dc3545' && (alert.text.includes("CRITICAL") || alert.text.includes("Multiple Faces"))) {
                 const studentIdMatch = alert.text.match(/^([^:]+):/);
                 if (studentIdMatch && studentIdMatch[1]) {
                     setSelectedStudent(prevId => prevId === studentIdMatch[1] ? prevId : studentIdMatch[1]);
                 }
             }
             // Update student snapshot state if alert includes one (used by normal modal)
            // Update student snapshot state if alert includes one (used by normal modal)
             if(alertData.snapshot && alertData.text) {
                 const studentIdMatch = alertData.text.match(/^([^:]+):/);
                 if (studentIdMatch && studentIdMatch[1]) {
                     const studentId = studentIdMatch[1];
                     
                     // Use the functional update to get the *current* state
                     setStudents(prevStudents => {
                          // Move the check INSIDE
                          if (prevStudents[studentId]) {
                              // Return the new state
                              return { ...prevStudents, [studentId]: { ...prevStudents[studentId], snapshot: alertData.snapshot } };
                          }
                          // Return state unchanged if student not found
                          return prevStudents;
                     });
                 }
             }
        }
    });
    socketRef.current.on('error', (data) => { console.error("Server error:", data.message); alert(`Server Error: ${data.message || 'Unknown'}`); });

    return () => { console.log("Disconnecting..."); socketRef.current?.disconnect(); socketRef.current = null; };
  // Removed students dependency - updates happen via socket events
  }, []); // Run only once on mount

  // --- Helper Functions ---
  const getBorderColor = (score = 100, status = "") => {
    if (status && (status.includes('CRITICAL') || status.includes('Multiple Faces'))) return '#dc3545';
    if (status === 'Away') return '#6c757d';
    if (score > 80) return '#28a745';
    if (score > 50) return '#ffc107';
    return '#dc3545';
  };
  const handleKickStudent = (studentId) => {
    if (window.confirm(`Kick student ${studentId}?`)) {
      console.log(`Kicking ${studentId}`);
      socketRef.current?.emit("adminKickStudent", { student_id: studentId });
      setSelectedStudent(null);
    }
  };
  const studentArray = Object.values(students);

  // --- Components ---
  const FocusScoreDoughnut = () => { /* ... unchanged ... */
      const onlineStudents = studentArray.filter(s => s.status !== 'Away');
      const avgScore = Math.round(onlineStudents.reduce((acc, s) => acc + (s.score ?? 0), 0) / (onlineStudents.length || 1));
      const borderColor = getBorderColor(avgScore, '');
      return ( <div style={styles.doughnutChartContainer}> <svg viewBox="0 0 120 120" style={styles.doughnutSvg}><circle cx="60" cy="60" r={50} fill="none" stroke="#eef2ff" strokeWidth="10" /><circle cx="60" cy="60" r={50} fill="none" stroke={borderColor} strokeWidth="10" strokeDasharray={2 * Math.PI * 50} strokeDashoffset={(2 * Math.PI * 50) - (avgScore / 100) * (2 * Math.PI * 50)} strokeLinecap="round" /></svg> <span style={{ ...styles.scoreText, color: borderColor }}>{onlineStudents.length > 0 ? `${avgScore}%` : '-'}</span> </div> );
  };
  const NavItem = ({ name, icon: Icon }) => ( <div style={styles.navItem(name, activeNav)} onClick={() => setActiveNav(name)}> <Icon style={styles.navIcon} /><span>{name}</span> </div> );

  // Find the latest alert for the currently selected student
  const latestAlertForModal = selectedStudent ? alerts.find(a => a.text.startsWith(selectedStudent + ":")) : null;

  // --- Render ---
  return (
    <div style={styles.appBackground}>
      <GlobalStyles /> {/* Include styles for animation */}
      <div style={styles.dashboardCard}>
        {selectedStudent && students[selectedStudent] && (
          <StudentDetailModal
            student={students[selectedStudent]}
            onClose={() => setSelectedStudent(null)}
            onKickStudent={handleKickStudent}
            styles={styles}
            latestAlert={latestAlertForModal}
          />
        )}
        <aside style={styles.sidebar}>
          <div style={styles.logo}>LockIN Admin</div>
          <NavItem name="Home" icon={FiHome} />
          <NavItem name="Students" icon={FiUsers} />
          <NavItem name="Create Exam" icon={FiSettings} />
        </aside>
        <main style={styles.mainContent}>
          <header style={styles.header}>
             <FiBell style={styles.headerIcon} title={`${alerts.length} alerts`} /> {/* Simplified title */}
             <FiUser style={styles.headerIcon} title="Admin User"/>
          </header>

          {activeNav === 'Create Exam' && <CreateExamForm styles={styles} socket={socketRef.current} />}

          {(activeNav === 'Home' || activeNav === 'Students') && (
            <div style={styles.contentArea}>
              {/* Left Column: Student Feeds */}
              <div>
                <div style={styles.panel}>
                  <h3 style={styles.panelTitle}>LIVE STUDENT FEEDS ({studentArray.length})</h3>
                  <div style={styles.feedsGrid}>
                    {studentArray.length === 0 && <p style={styles.modalStat}>Waiting for students to connect...</p>}
                    {studentArray.map((student) => {
                      const score = student.score ?? 100;
                      const status = student.status ?? "Connecting...";
                      // --- USE wallpaperB64 ---
                      const wallpaperImage = student.wallpaperB64;
                      // --- END USE ---
                      const borderColor = getBorderColor(score, status);
                      const isCritical = status.includes('CRITICAL') || status.includes('Multiple Faces');
                      return (
                        <div key={student.id}
                          style={{
                            ...styles.feedItem,
                            // --- USE wallpaperImage variable ---
                            backgroundImage: wallpaperImage ? `url(data:image/jpeg;base64,${wallpaperImage})` : 'none',
                             // --- END USE ---
                            backgroundColor: wallpaperImage ? '#e0e0e0' : '#eee', // Light gray background
                            backgroundSize: 'cover',
                            backgroundPosition: 'center',
                            border: `4px solid ${borderColor}`,
                            boxShadow: `0 0 15px ${borderColor}33`,
                            animation: isCritical ? 'pulse 1s infinite' : 'none',
                          }}
                          onClick={() => setSelectedStudent(student.id)}
                          title={`Click for details: ${student.id}`}
                        >
                          <span style={{ ...styles.feedOverlay, backgroundColor: `${borderColor}CC` }}>
                            {student.id} - {isCritical ? status.split(': ')[1] || status.split(': ')[0] || 'ALERT!' : `${score}%`}
                          </span>
                        </div> );
                    })}
                  </div>
                </div>
              </div>
              {/* Right Column: Stats & Alerts */}
              <div>
                <div style={{ ...styles.panel, ...styles.scorePanel }}>
                  <h3 style={styles.panelTitle}>OVERALL FOCUS SCORE</h3>
                  <FocusScoreDoughnut />
                  <p style={{ fontSize: '14px', color: '#555', marginTop: '10px' }}>Avg. focus of online students.</p>
                </div>
                <div style={styles.panel}>
                  <h3 style={styles.panelTitle}>RECENT ALERTS ({alerts.length})</h3>
                  <div style={{maxHeight: 'calc(100vh - 450px)', overflowY: 'auto'}}> {/* Dynamic height */}
                    {alerts.length === 0 && <p style={styles.modalStat}>No alerts yet.</p>}
                    {alerts.map((alert) => (
                      <div key={alert.id} style={styles.listItem(alert.color)} title={alert.text}>
                        {alert.Icon && <alert.Icon style={styles.alertIcon(alert.color)} />}
                        <div style={{ overflow: 'hidden'}}>
                          <span style={styles.alertText(alert.color)}>{alert.text}</span>
                          <span style={styles.alertTime}>{alert.time}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

// --- Styles Function (NO CHANGES) ---
function createStyles() {
    // ... (All the styles remain the same) ...
    return {
        appBackground: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, margin: 0, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #a8c0ff 0%, #3f63c8 100%)', fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif", boxSizing: 'border-box', overflow: 'hidden', },
        dashboardCard: { width: '1300px', height: '850px', maxWidth: '95%', maxHeight: '95vh', borderRadius: '25px', backgroundColor: 'rgba(255, 255, 255, 0.98)', boxShadow: '0 10px 40px rgba(0, 0, 0, 0.1), 0 0 50px rgba(168, 192, 255, 0.3)', backdropFilter: 'blur(5px)', display: 'grid', gridTemplateColumns: '220px 1fr', overflow: 'hidden', position: 'relative' },
        sidebar: { padding: '25px 0', borderRight: '1px solid #eee', backgroundColor: 'white', display: 'flex', flexDirection: 'column' },
        logo: { fontSize: '24px', fontWeight: '700', color: '#333366', padding: '0 25px 30px 25px', textAlign: 'center' },
        navItem: (name, activeNav) => ({ display: 'flex', alignItems: 'center', padding: '12px 25px', fontSize: '15px', fontWeight: name === activeNav ? '600' : '500', color: name === activeNav ? '#4a70f0' : '#555', backgroundColor: name === activeNav ? '#eef2ff' : 'transparent', borderLeft: name === activeNav ? '4px solid #4a70f0' : '4px solid transparent', paddingLeft: name === activeNav ? '21px' : '25px', cursor: 'pointer', transition: 'all 0.2s ease', '&:hover': { backgroundColor: '#f8f9fa'} }),
        navIcon: { marginRight: '15px', fontSize: '18px' },
        mainContent: { display: 'flex', flexDirection: 'column', overflow: 'hidden' },
        header: { display: 'flex', justifyContent: 'flex-end', alignItems: 'center', padding: '15px 30px', borderBottom: '1px solid #eee', backgroundColor: 'white', height: '70px', flexShrink: 0 },
        headerIcon: { fontSize: '20px', color: '#777', marginLeft: '20px', cursor: 'pointer', '&:hover': { color: '#4a70f0'} },
        contentArea: { padding: '30px', display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px', overflowY: 'auto', backgroundColor: '#f9faff', flexGrow: 1 },
        panel: { backgroundColor: 'white', borderRadius: '15px', padding: '20px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)', marginBottom: '30px' },
        panelTitle: { fontSize: '14px', fontWeight: '600', color: '#555', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '0.5px' },
        feedsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }, // Responsive grid
        feedItem: { position: 'relative', borderRadius: '10px', overflow: 'hidden', aspectRatio: '4 / 3', backgroundColor: '#e0e0e0', backgroundSize: 'cover', backgroundPosition: 'center', cursor: 'pointer', transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.3s ease', border: '4px solid transparent' },
        feedOverlay: { position: 'absolute', bottom: '8px', left: '8px', padding: '4px 10px', borderRadius: '15px', fontSize: '12px', fontWeight: '600', color: 'white', textShadow: '1px 1px 2px rgba(0,0,0,0.7)' },
        scorePanel: { display: 'flex', flexDirection: 'column', alignItems: 'center' },
        doughnutChartContainer: { position: 'relative', width: '120px', height: '120px', marginBottom: '10px' },
        scoreText: { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: '28px', fontWeight: '700' },
        doughnutSvg: { transform: 'rotate(-90deg)' },
        listItem: (color = '#555') => ({ display: 'flex', alignItems: 'flex-start', padding: '10px 0', borderBottom: '1px solid #f0f0f0', fontSize: '14px', color: color, cursor: 'default', '&:last-child': { borderBottom: 'none' } }),
        alertIcon: (color) => ({ fontSize: '16px', marginRight: '10px', color: color || '#555', marginTop: '3px', flexShrink: 0 }),
        alertText: (color) => ({ fontSize: '13px', fontWeight: '500', color: color || '#333', flexGrow: 1, marginRight: '10px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }),
        alertTime: { fontSize: '11px', color: '#888', display: 'block', marginTop: '2px', whiteSpace: 'nowrap' },
        modalBackdrop: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' },
        modalContent: { width: 'auto', backgroundColor: 'white', borderRadius: '15px', boxShadow: '0 10px 30px rgba(0, 0, 0, 0.2)', overflow: 'hidden', maxHeight: '90vh' },
        modalHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 25px', borderBottom: '1px solid #eee' },
        modalTitle: { fontSize: '18px', fontWeight: '600', color: '#333' },
        modalCloseButton: { background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '24px', color: '#888', '&:hover': { color: '#333'} },
        modalBody: { padding: '25px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '25px', overflowY: 'auto', maxHeight: 'calc(90vh - 70px)' },
        modalSection: { display: 'flex', flexDirection: 'column' },
        modalSectionTitle: { fontSize: '16px', fontWeight: '600', color: '#333366', borderBottom: '2px solid #eef2ff', paddingBottom: '5px', marginBottom: '15px' },
        modalStat: { fontSize: '14px', color: '#555', marginBottom: '10px', wordBreak: 'break-word' },
        criticalAlertBox: { gridColumn: '1 / -1', display: 'flex', flexDirection: 'row', alignItems: 'center', padding: '15px', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '10px', border: '1px solid #f5c6cb' },
        modalPhotoLabel: { fontSize: '14px', fontWeight: '600', color: '#555', marginBottom: '10px' },
        modalPhoto: { width: '100%', borderRadius: '10px', border: '1px solid #ddd', backgroundColor: '#eee', aspectRatio: '4 / 3', objectFit: 'cover' },
        modalActionButtons: { gridColumn: '1 / -1', display: 'flex', gap: '15px', marginTop: '20px' },
        modalButton: { flex: 1, padding: '12px', fontSize: '16px', fontWeight: '600', borderRadius: '8px', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'opacity 0.2s' },
        modalButtonConfirm: { backgroundColor: '#dc3545', color: 'white', '&:hover': { opacity: 0.9 } },
        modalButtonIgnore: { backgroundColor: '#6c757d', color: 'white', '&:hover': { opacity: 0.9 } },
        examFormContainer: { padding: '30px', overflowY: 'auto', height: 'calc(100% - 70px)', boxSizing: 'border-box', backgroundColor: '#f9faff', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' },
        formGroup: { marginBottom: '15px' },
        formLabel: { display: 'block', fontWeight: '600', color: '#555', marginBottom: '5px', fontSize: '14px' },
        formInput: { width: '100%', padding: '10px 15px', fontSize: '14px', border: '1px solid #ddd', borderRadius: '8px', boxSizing: 'border-box' },
        questionPreview: { padding: '10px', border: '1px solid #eee', borderRadius: '8px', marginBottom: '10px', backgroundColor: '#fcfcfc', fontSize: '14px' },
    };
}

// --- GlobalStyles Component ---
const GlobalStyles = () => ( <style>{`
    @keyframes pulse { /* ... pulse animation ... */ }
    /* ... scrollbar styles ... */
    @keyframes pulse {
      0% { box-shadow: 0 0 10px #dc354533, 0 0 0 0 rgba(220, 53, 69, 0.7); }
      70% { box-shadow: 0 0 15px #dc3545CC, 0 0 0 10px rgba(220, 53, 69, 0); }
      100% { box-shadow: 0 0 10px #dc354533, 0 0 0 0 rgba(220, 53, 69, 0); }
    }
    ::-webkit-scrollbar { width: 8px; height: 8px;}
    ::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px;}
    ::-webkit-scrollbar-thumb { background: #c5cddf; border-radius: 10px;}
    ::-webkit-scrollbar-thumb:hover { background: #a8b3d0; }
`}</style> );

// --- Default Export ---
export default AdminDashboard;