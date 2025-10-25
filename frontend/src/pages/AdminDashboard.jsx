// src/pages/AdminDashboard.jsx
import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import {
  FiHome, FiClipboard, FiUsers, FiBarChart2, FiSettings,
  FiBell, FiUser, FiSearch, FiAlertTriangle, FiAlertCircle, FiX,
  FiCheckCircle, FiUserX, FiPlus, FiInfo // Added FiInfo
} from 'react-icons/fi';

// --- Central Backend Server URL ---
const SOCKET_SERVER_URL = 'http://localhost:8000';

// --- Modal Component (Updated for new kick logic) ---
const StudentDetailModal = ({ student, onClose, onKickStudent, styles }) => {
  // student = { id, score, status, snapshot, sid }
  const isCritical = student.status && student.status.includes('CRITICAL');

  // Function to handle the kick confirmation
  const handleConfirmKick = () => {
    onKickStudent(student.id); // Pass only the ID to the kick function
  };

  return (
    <div style={styles.modalBackdrop} onClick={onClose}>
      <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>Student Details: {student.id}</h2>
          <button style={styles.modalCloseButton} onClick={onClose}><FiX /></button>
        </div>
        
        {isCritical ? (
          <div style={styles.modalBody}>
             <div style={{ ...styles.modalSection, ...styles.criticalAlertBox }}>
               <FiAlertTriangle style={{ fontSize: '24px', marginRight: '10px' }} />
               <h3 style={styles.modalSectionTitle}>IMPERSONATION / CRITICAL ALERT</h3>
             </div>
             <p style={{ ...styles.modalStat, gridColumn: '1 / -1' }}>{student.status}. Review snapshot and confirm action.</p>
             <div style={styles.modalSection}>
               <h4 style={styles.modalPhotoLabel}>Snapshot (From Alert)</h4>
               <img src={`data:image/jpeg;base64,${student.snapshot}`} alt="Alert Snapshot" style={styles.modalPhoto} />
             </div>
             <div style={styles.modalSection}>
               <h4 style={styles.modalPhotoLabel}>Student Details</h4>
                <p style={styles.modalStat}><strong>Status:</strong> {student.status}</p>
                <p style={styles.modalStat}><strong>Score:</strong> {student.score}%</p>
             </div>
             <div style={styles.modalActionButtons}>
               <button style={{ ...styles.modalButton, ...styles.modalButtonConfirm }} onClick={handleConfirmKick}>
                 <FiUserX style={{ marginRight: '5px' }} /> Confirm & Kick
               </button>
               <button style={{ ...styles.modalButton, ...styles.modalButtonIgnore }} onClick={onClose}>
                 <FiCheckCircle style={{ marginRight: '5px' }} /> False Alarm
               </button>
             </div>
          </div>
        ) : (
          <div style={styles.modalBody}>
            <div style={styles.modalSection}>
              <h3 style={styles.modalSectionTitle}>Latest Snapshot</h3>
              {student.snapshot ? (
                <img src={`data:image/jpeg;base64,${student.snapshot}`} alt={student.id} style={{...styles.feedItem, height: 'auto', width: '100%', backgroundColor: '#f0f0f0'}} />
              ) : (
                <div style={{...styles.feedItem, height: 'auto', width: '100%', backgroundColor: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888'}}>Waiting for snapshot...</div>
              )}
            </div>
            <div style={styles.modalSection}>
              <h3 style={styles.modalSectionTitle}>Focus Statistics</h3>
              <p style={styles.modalStat}><strong>Current Score:</strong> {student.score}%</p>
              <p style={styles.modalStat}><strong>Status:</strong> {student.status}</p>
              {/* Display warnings if available */}
              {student.warnings !== undefined && <p style={styles.modalStat}><strong>Warnings:</strong> {student.warnings}/{MAX_WARNINGS}</p>}
            </div>
             {/* Add a manual kick button for non-critical cases */}
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


// --- Create Exam Form (No changes) ---
const CreateExamForm = ({ styles }) => { /* ... same form code ... */ 
  const [questions, setQuestions] = useState([]); const [currentQ, setCurrentQ] = useState(''); const [options, setOptions] = useState(['', '', '', '']); const [correctAnswer, setCorrectAnswer] = useState(0);
  const handleOptionChange = (index, value) => { const newOptions = [...options]; newOptions[index] = value; setOptions(newOptions); };
  const handleAddQuestion = () => { if (!currentQ || options.some(opt => opt === '')) return; const newQuestion = { id: questions.length + 1, text: currentQ, options: options, correct: correctAnswer }; setQuestions([...questions, newQuestion]); setCurrentQ(''); setOptions(['', '', '', '']); setCorrectAnswer(0); };
  const handleSaveExam = () => { localStorage.setItem('hackathonExam', JSON.stringify(questions)); alert(`Exam Saved! ${questions.length} questions published.`); setQuestions([]); };
  return ( <div style={styles.examFormContainer}> <div style={styles.panel}> <h3 style={styles.panelTitle}>Create New Exam</h3> <div style={styles.formGroup}> <label style={styles.formLabel}>Question Text</label> <input type="text" style={styles.formInput} value={currentQ} onChange={(e) => setCurrentQ(e.target.value)} placeholder="e.g., What is 2 + 2?" /> </div> {options.map((opt, index) => ( <div style={styles.formGroup} key={index}> <label style={styles.formLabel}>Option {index + 1} (Mark correct)</label> <div style={{ display: 'flex', alignItems: 'center' }}> <input type="radio" name="correctAnswer" checked={correctAnswer === index} onChange={() => setCorrectAnswer(index)} style={{ marginRight: '10px' }} /> <input type="text" style={styles.formInput} value={opt} onChange={(e) => handleOptionChange(index, e.target.value)} placeholder={`Option ${index + 1}`} /> </div> </div> ))} <button style={{ ...styles.modalButton, ...styles.modalButtonIgnore, width: 'auto', marginTop: '10px' }} onClick={handleAddQuestion}> <FiPlus style={{ marginRight: '5px' }} /> Add </button> </div> <div style={styles.panel}> <h3 style={styles.panelTitle}>Current Exam ({questions.length})</h3> <div style={{ maxHeight: '300px', overflowY: 'auto' }}> {questions.map((q, index) => ( <div key={q.id} style={styles.questionPreview}><strong>{index + 1}. {q.text}</strong><small> (Ans: {q.options[q.correct]})</small></div> ))} {questions.length === 0 && <p style={styles.modalStat}>No questions yet.</p>} </div> <button style={{ ...styles.modalButton, ...styles.modalButtonConfirm, marginTop: '20px', backgroundColor: '#28a745' }} onClick={handleSaveExam} disabled={questions.length === 0}> Save & Publish </button> </div> </div> );
};

// --- Main Dashboard Component (Connects to Backend) ---
const AdminDashboard = () => {
  const [activeNav, setActiveNav] = useState('Exams');
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [students, setStudents] = useState({}); // Stores student state: { student_id: { id, score, status, snapshot, sid } }
  const [styles, setStyles] = useState(createStyles());
  const socketRef = useRef();

  // --- Connect to Backend and Listen for Events ---
  useEffect(() => {
    socketRef.current = io(SOCKET_SERVER_URL);

    socketRef.current.emit('adminJoin');

    socketRef.current.on('student_list', (studentList) => {
      console.log("Received student list:", studentList);
      setStudents(prev => {
        const newStudents = {...prev};
        // studentList is expected to be array of student objects from backend state
        studentList.forEach(student => {
            if (student && student.id) { // Ensure student object is valid
                 newStudents[student.id] = student;
            }
        });
        return newStudents;
      });
    });

    socketRef.current.on('new_student', (student) => {
       console.log("New student joined:", student);
       if (student && student.id) { // Ensure student object is valid
           setStudents(prev => ({ ...prev, [student.id]: student }));
       }
    });

    socketRef.current.on('student_left', (data) => {
      console.log("Student left:", data);
      if (data && data.student_id) {
          setStudents(prev => {
            const newStudents = { ...prev };
            delete newStudents[data.student_id];
            return newStudents;
          });
          // Close modal if the leaving student was selected
          setSelectedStudent(prev => (prev && prev.id === data.student_id ? null : prev));
      }
    });

    socketRef.current.on('student_update', (data) => {
      // console.log("Student update:", data); // Can be noisy
       if (data && data.student_id) {
           setStudents(prev => ({
             ...prev,
             [data.student_id]: { ...prev[data.student_id], ...data }
           }));
           // Update selected student modal if it's open for this student
           setSelectedStudent(prev => (prev && prev.id === data.student_id ? { ...prev, ...data } : prev));
       }
    });

    socketRef.current.on('new_alert', (alert) => {
        console.log("New alert:", alert);
        if (alert && alert.id) {
             // Assign icon based on color or type
             if (alert.color === '#dc3545') alert.Icon = FiAlertTriangle; // Red
             else if (alert.color === '#ffc107') alert.Icon = FiAlertCircle; // Yellow
             else if (alert.color === '#17a2b8') alert.Icon = FiInfo; // Info blue
             else if (alert.color === '#6c757d') alert.Icon = FiUserX; // Gray kick
             else alert.Icon = FiBell; // Default

             setAlerts(prev => [alert, ...prev].slice(0, 10)); // Keep last 10 alerts
             
             // Update student snapshot if included with alert
             if(alert.snapshot && alert.text) {
                 const studentIdMatch = alert.text.match(/^([^:]+):/); // Extract student ID from text "student_id: message"
                 if (studentIdMatch && studentIdMatch[1]) {
                      const studentId = studentIdMatch[1];
                      setStudents(prev => ({
                          ...prev,
                          [studentId]: { ...prev[studentId], snapshot: alert.snapshot }
                      }));
                      // Update modal snapshot if open
                      setSelectedStudent(prev => (prev && prev.id === studentId ? { ...prev, snapshot: alert.snapshot } : prev));
                 }
             }
        }
    });

    socketRef.current.on('error', (data) => {
        console.error("Received error from server:", data.message);
        alert(`Server Error: ${data.message}`);
    });

    return () => {
      socketRef.current.disconnect();
    };
  }, []); // Runs once

  const getBorderColor = (score = 100, status = "") => { // Default score to 100 if undefined
    if (status && status.includes('CRITICAL')) return '#dc3545';
    if (score > 80) return '#28a745';
    if (score > 50) return '#ffc107';
    return '#dc3545';
  };

  // --- Send Kick Request to Backend ---
  const handleKickStudent = (studentId) => {
    if (window.confirm(`Are you sure you want to kick student ${studentId}?`)) {
      console.log(`Requesting kick for ${studentId}`);
      socketRef.current.emit("adminKickStudent", { student_id: studentId });
      // The student will be removed from the list when the backend confirms via 'student_left' event
      setSelectedStudent(null); // Close modal immediately
    }
  };
  
  const studentArray = Object.values(students); // Convert student object to array for mapping

  // --- (Doughnut, NavItem, ongoingExams - No major changes) ---
  const FocusScoreDoughnut = () => { /* ... calculates average ... */ 
      const avgScore = Math.round(studentArray.reduce((acc, s) => acc + (s.score ?? 100), 0) / (studentArray.length || 1));
      const borderColor = getBorderColor(avgScore, '');
      return ( <div style={styles.doughnutChartContainer}> <svg viewBox="0 0 120 120" style={styles.doughnutSvg}><circle cx="60" cy="60" r={50} fill="none" stroke="#eef2ff" strokeWidth="10" /><circle cx="60" cy="60" r={50} fill="none" stroke={borderColor} strokeWidth="10" strokeDasharray={2 * Math.PI * 50} strokeDashoffset={(2 * Math.PI * 50) - (avgScore / 100) * (2 * Math.PI * 50)} strokeLinecap="round" /></svg> <span style={{ ...styles.scoreText, color: borderColor }}>{avgScore}%</span> </div> );
  };
  const NavItem = ({ name, icon: Icon }) => { /* ... */ return ( <div style={styles.navItem(name, activeNav)} onClick={() => setActiveNav(name)}> <Icon style={styles.navIcon} /><span>{name}</span> </div> ); };
  const ongoingExams = [ { time: '9:00 AM', title: 'Calculus I', progress: 83 } ];

  return (
    <div style={styles.appBackground}>
      <div style={styles.dashboardCard}>
        {selectedStudent && students[selectedStudent.id] && ( // Ensure student still exists before showing modal
          <StudentDetailModal
            student={students[selectedStudent.id]} // Pass the latest student data
            onClose={() => setSelectedStudent(null)}
            onKickStudent={handleKickStudent} // Pass kick handler
            styles={styles}
          />
        )}

        <aside style={styles.sidebar}> {/* ... Nav items ... */ }
          <div style={styles.logo}>LockIN</div>
          <NavItem name="Home" icon={FiHome} />
          <NavItem name="Exams" icon={FiClipboard} />
          <NavItem name="Students" icon={FiUsers} />
          <NavItem name="Reports" icon={FiBarChart2} />
          <NavItem name="Create Exam" icon={FiSettings} />
        </aside>

        <main style={styles.mainContent}>
          <header style={styles.header}> {/* ... Header icons ... */ }
             <FiSearch style={styles.headerIcon} /><FiBell style={styles.headerIcon} /><FiUser style={styles.headerIcon} />
          </header>

          {activeNav === 'Create Exam' ? (
            <CreateExamForm styles={styles} />
          ) : (
            <div style={styles.contentArea}>
              <div> {/* Left Column */}
                <div style={styles.panel}>
                  <h3 style={styles.panelTitle}>LIVE STUDENT FEEDS ({studentArray.length})</h3>
                  <div style={styles.feedsGrid}>
                    {studentArray.length === 0 && <p style={styles.modalStat}>Waiting for students to connect...</p>}
                    {studentArray.map((student) => {
                      // Use default values if student data is incomplete
                      const score = student.score ?? 100; 
                      const status = student.status ?? "Connecting...";
                      const snapshot = student.last_snapshot ?? student.snapshot; // Use last_snapshot if available
                      
                      const borderColor = getBorderColor(score, status);
                      const isCritical = status.includes('CRITICAL');
                      return (
                        <div
                          key={student.id}
                          style={{
                            ...styles.feedItem,
                            backgroundImage: snapshot ? `url(data:image/jpeg;base64,${snapshot})` : 'none',
                            backgroundColor: snapshot ? '#000' : '#eee', // Show gray if no snapshot yet
                            border: `4px solid ${borderColor}`,
                            boxShadow: `0 0 15px ${borderColor}33`,
                            animation: isCritical ? 'pulse 1s infinite' : 'none',
                          }}
                          onClick={() => setSelectedStudent(student)} // Selects student for modal
                        >
                          <span style={{ ...styles.feedOverlay, backgroundColor: `${borderColor}CC` }}>
                            {student.id} - {isCritical ? 'ALERT!' : `${score}%`}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
              <div> {/* Right Column */}
                <div style={{ ...styles.panel, ...styles.scorePanel }}>
                  <h3 style={styles.panelTitle}>OVERALL FOCUS SCORE</h3>
                  <FocusScoreDoughnut />
                  <p style={{ fontSize: '14px', color: '#555', marginTop: '10px' }}>Average focus score.</p>
                </div>
                <div style={styles.panel}>
                  <h3 style={styles.panelTitle}>ALERTS ({alerts.length})</h3>
                  <div style={{maxHeight: '250px', overflowY: 'auto'}}> {/* Make alerts scrollable */}
                    {alerts.length === 0 && <p style={styles.modalStat}>No alerts yet.</p>}
                    {alerts.map((alert) => (
                      <div key={alert.id} style={styles.listItem(alert.color)}>
                        {alert.Icon && <alert.Icon style={styles.alertIcon(alert.color)} />}
                        <div>
                          <span style={styles.alertText(alert.color)}>{alert.text}</span>
                          <span style={styles.alertTime}>{alert.time}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div style={styles.panel}>
                  <h3 style={styles.panelTitle}>ONGOING EXAMS</h3>
                  {/* ... Exam progress ... */}
                  {ongoingExams.map((exam, index) => ( <div key={index} style={{ ...styles.examItem, borderBottom: 'none' }}> <div style={styles.examDetails}><span style={styles.examTime}>{exam.time}</span><span style={styles.examPercentage}>{exam.progress}%</span></div> <div style={{ fontSize: '13px', color: '#888', marginBottom: '5px' }}>{exam.title}</div> <div style={styles.progressBarContainer}><div style={styles.progressBar(exam.progress)}></div></div> </div> ))}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

// --- Styles & GlobalStyles (Keep the createStyles function and GlobalStyles component) ---
function createStyles() { /* ... Paste ALL styles from previous step ... */ 
  return {
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
    dashboardCard: { width: '1200px', height: '800px', maxWidth: '100%', maxHeight: '100%', borderRadius: '25px', backgroundColor: 'rgba(255, 255, 255, 0.95)', boxShadow: '0 10px 40px rgba(0, 0, 0, 0.1), 0 0 50px rgba(168, 192, 255, 0.3)', backdropFilter: 'blur(10px)', display: 'grid', gridTemplateColumns: '220px 1fr', overflow: 'hidden', position: 'relative' },
    sidebar: { padding: '25px 0', borderRight: '1px solid #eee', backgroundColor: 'white', display: 'flex', flexDirection: 'column' },
    logo: { fontSize: '24px', fontWeight: '700', color: '#333366', padding: '0 25px 30px 25px' },
    navItem: (name, activeNav) => ({ display: 'flex', alignItems: 'center', padding: '12px 25px', fontSize: '15px', fontWeight: name === activeNav ? '600' : '500', color: name === activeNav ? '#4a70f0' : '#555', backgroundColor: name === activeNav ? '#eef2ff' : 'transparent', borderLeft: name === activeNav ? '4px solid #4a70f0' : '4px solid transparent', paddingLeft: name === activeNav ? '21px' : '25px', cursor: 'pointer', transition: 'all 0.2s ease' }),
    navIcon: { marginRight: '15px', fontSize: '18px' },
    mainContent: { display: 'flex', flexDirection: 'column', overflow: 'hidden' },
    header: { display: 'flex', justifyContent: 'flex-end', alignItems: 'center', padding: '15px 30px', borderBottom: '1px solid #eee', backgroundColor: 'white', height: '70px', flexShrink: 0 },
    headerIcon: { fontSize: '20px', color: '#777', marginLeft: '15px', cursor: 'pointer' },
    contentArea: { padding: '30px', display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px', overflowY: 'auto', backgroundColor: '#f9f9ff', flexGrow: 1 },
    panel: { backgroundColor: 'white', borderRadius: '15px', padding: '20px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)', marginBottom: '30px' },
    panelTitle: { fontSize: '16px', fontWeight: '600', color: '#333', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '0.5px' },
    feedsGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' },
    feedItem: { position: 'relative', borderRadius: '10px', overflow: 'hidden', height: '140px', backgroundColor: '#e0e0e0', backgroundSize: 'cover', backgroundPosition: 'center', cursor: 'pointer', transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.3s ease', border: '4px solid transparent' },
    feedItemHover: { transform: 'scale(1.03)', boxShadow: '0 8px 20px rgba(0, 0, 0, 0.1)' },
    feedOverlay: { position: 'absolute', bottom: '10px', left: '10px', padding: '3px 8px', borderRadius: '15px', fontSize: '12px', fontWeight: '600', color: 'white', textShadow: '1px 1px 2px rgba(0,0,0,0.5)' },
    scorePanel: { display: 'flex', flexDirection: 'column', alignItems: 'center' },
    doughnutChartContainer: { position: 'relative', width: '120px', height: '120px', marginBottom: '10px' },
    scoreText: { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: '28px', fontWeight: '700' },
    doughnutSvg: { transform: 'rotate(-90deg)' },
    listItem: (color = '#555') => ({ display: 'flex', alignItems: 'flex-start', padding: '10px 0', borderBottom: '1px solid #f0f0f0', fontSize: '14px', color: color, cursor: 'default', '&:last-child': { borderBottom: 'none' } }), // Align items top for multi-line text
    listIcon: { fontSize: '16px', marginRight: '10px', color: '#999', marginTop: '2px' }, // Add margin top
    listDetail: { marginLeft: 'auto', fontWeight: '600', fontSize: '13px', color: '#777' },
    alertIcon: (color) => ({ fontSize: '16px', marginRight: '10px', color: color, marginTop: '2px' }),
    alertText: (color) => ({ fontSize: '14px', fontWeight: '500', color: color, flex: 1, marginRight: '10px' }), // Allow text to wrap
    examItem: { padding: '10px 0', borderBottom: '1px solid #f0f0f0' },
    examTime: { fontSize: '15px', fontWeight: '600', color: '#333', marginBottom: '5px' },
    examDetails: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
    examTitle: { fontSize: '14px', fontWeight: '500', color: '#444' },
    examPercentage: { fontSize: '14px', fontWeight: '600', color: '#4a70f0' },
    progressBarContainer: { height: '6px', backgroundColor: '#e0eaff', borderRadius: '3px', marginTop: '5px' },
    progressBar: (width) => ({ height: '100%', width: `${width}%`, backgroundColor: '#4a70f0', borderRadius: '3px' }),
    alertTime: { fontSize: '11px', color: '#888', display: 'block', marginTop: '2px' },
    modalBackdrop: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
    modalContent: { width: '700px', maxWidth: '95%', backgroundColor: 'white', borderRadius: '15px', boxShadow: '0 10px 30px rgba(0, 0, 0, 0.2)', overflow: 'hidden' },
    modalHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 25px', borderBottom: '1px solid #eee' },
    modalTitle: { fontSize: '18px', fontWeight: '600', color: '#333' },
    modalCloseButton: { background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '24px', color: '#888' },
    modalBody: { padding: '25px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '25px' },
    modalSection: { display: 'flex', flexDirection: 'column' },
    modalSectionTitle: { fontSize: '16px', fontWeight: '600', color: '#333366', borderBottom: '2px solid #eef2ff', paddingBottom: '5px', marginBottom: '15px' },
    modalStat: { fontSize: '14px', color: '#555', marginBottom: '10px' },
    criticalAlertBox: { gridColumn: '1 / -1', display: 'flex', flexDirection: 'row', alignItems: 'center', padding: '15px', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '10px', border: '1px solid #f5c6cb' },
    modalPhotoLabel: { fontSize: '14px', fontWeight: '600', color: '#555', marginBottom: '10px' },
    modalPhoto: { width: '100%', borderRadius: '10px', border: '1px solid #ddd' },
    modalActionButtons: { gridColumn: '1 / -1', display: 'flex', gap: '15px', marginTop: '20px' },
    modalButton: { flex: 1, padding: '12px', fontSize: '16px', fontWeight: '600', borderRadius: '8px', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justify: 'center', transition: 'opacity 0.2s' },
    modalButtonConfirm: { backgroundColor: '#dc3545', color: 'white', '&:hover': { opacity: 0.9 } },
    modalButtonIgnore: { backgroundColor: '#6c757d', color: 'white', '&:hover': { opacity: 0.9 } },
    examFormContainer: { padding: '30px', overflowY: 'auto', height: 'calc(100% - 70px)', boxSizing: 'border-box', backgroundColor: '#f9f9ff' }, // Adjust height
    formGroup: { marginBottom: '15px' },
    formLabel: { display: 'block', fontWeight: '600', color: '#555', marginBottom: '5px', fontSize: '14px' },
    formInput: { width: '100%', padding: '10px 15px', fontSize: '14px', border: '1px solid #ddd', borderRadius: '8px', boxSizing: 'border-box' },
    questionPreview: { padding: '10px', border: '1px solid #eee', borderRadius: '8px', marginBottom: '10px', backgroundColor: '#fcfcfc', fontSize: '14px' },
  };
}

const GlobalStyles = () => { /* ... Keyframes ... */ return ( <style>{`@keyframes pulse { 0% { box-shadow: 0 0 15px #dc354533; } 50% { box-shadow: 0 0 25px #dc3545CC; } 100% { box-shadow: 0 0 15px #dc354533; } }`}</style> ); };

export default function DashboardWrapper() { return ( <> <GlobalStyles /> <AdminDashboard /> </> ); }