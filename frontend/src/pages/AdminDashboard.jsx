// src/pages/AdminDashboard.jsx
import React, { useState, useEffect } from 'react';
import {
  FiHome, FiClipboard, FiUsers, FiBarChart2, FiSettings,
  FiBell, FiUser, FiSearch, FiAlertTriangle, FiAlertCircle, FiX,
  FiCheckCircle, FiUserX // --- NEW ICONS ---
} from 'react-icons/fi';

// --- 1. Updated Mock Data ---
// I've added new photo URLs for Student #55
const MOCK_STUDENT_DATA = [
  {
    id: 1,
    name: 'Student #12 (Thilak K)',
    staticPhotoUrl: 'https://i.imgur.com/G3t7jYJ.png', // Baseline photo
    swappedPhotoUrl: 'https://i.imgur.com/G3t7jYJ.png', // (not used for this student)
    status: 'Focused',
    focusScore: 95,
  },
  {
    id: 2,
    name: 'Student #448',
    staticPhotoUrl: 'https://i.imgur.com/G3t7jYJ.png',
    swappedPhotoUrl: 'https://i.imgur.com/G3t7jYJ.png',
    status: 'Focused',
    focusScore: 88,
  },
  {
    id: 3,
    name: 'Student #301',
    staticPhotoUrl: 'https://i.imgur.com/G3t7jYJ.png',
    swappedPhotoUrl: 'https://i.imgur.com/G3t7jYJ.png',
    status: 'Focused',
    focusScore: 72,
  },
  {
    id: 4,
    name: 'Student #55',
    staticPhotoUrl: 'https://i.imgur.com/G3t7jYJ.png', // Baseline photo
    // --- THIS IS THE "SWAPPED" PERSON'S PHOTO ---
    swappedPhotoUrl: 'https://i.imgur.com/8mBma2t.png', // A different placeholder image
    status: 'Distracted',
    focusScore: 45,
  },
];

// --- 2. Upgraded Modal Component ---
// This modal now has a "critical" state
const StudentDetailModal = ({ student, onClose, onKickStudent, styles }) => {
  const isCritical = student.status.includes('CRITICAL');

  return (
    <div style={styles.modalBackdrop} onClick={onClose}>
      <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <h2 style={styles.modalTitle}>Student Details: {student.name}</h2>
          <button style={styles.modalCloseButton} onClick={onClose}>
            <FiX />
          </button>
        </div>
        
        {/* --- NEW CONDITIONAL RENDERING --- */}
        {isCritical ? (
          // --- CRITICAL ALERT VIEW ---
          <div style={styles.modalBody}>
            <div style={{ ...styles.modalSection, ...styles.criticalAlertBox }}>
              <FiAlertTriangle style={{ fontSize: '24px', marginRight: '10px' }} />
              <h3 style={styles.modalSectionTitle}>IMPERSONATION ALERT</h3>
            </div>
            <p style={{ ...styles.modalStat, gridColumn: '1 / -1' }}>
              System detected a potential face swap. Please review the images below and confirm.
            </p>
            <div style={styles.modalSection}>
              <h4 style={styles.modalPhotoLabel}>Baseline Photo (Start of Exam)</h4>
              <img src={student.staticPhotoUrl} alt="Baseline" style={styles.modalPhoto} />
            </div>
            <div style={styles.modalSection}>
              <h4 style={styles.modalPhotoLabel}>New Snapshot (From Alert)</h4>
              <img src={student.swappedPhotoUrl} alt="Swapped" style={styles.modalPhoto} />
            </div>
            <div style={styles.modalActionButtons}>
              <button 
                style={{ ...styles.modalButton, ...styles.modalButtonConfirm }}
                onClick={() => onKickStudent(student.id, student.name)}
              >
                <FiUserX style={{ marginRight: '5px' }} /> Confirm & Kick Student
              </button>
              <button 
                style={{ ...styles.modalButton, ...styles.modalButtonIgnore }}
                onClick={onClose}
              >
                <FiCheckCircle style={{ marginRight: '5px' }} /> False Alarm (Ignore)
              </button>
            </div>
          </div>
        ) : (
          // --- NORMAL DETAIL VIEW ---
          <div style={styles.modalBody}>
            <div style={styles.modalSection}>
              <h3 style={styles.modalSectionTitle}>Candidate Photo</h3>
              <img
                src={student.staticPhotoUrl}
                alt={student.name}
                style={{...styles.feedItem, height: 'auto', width: '100%', backgroundColor: '#f0f0f0'}}
              />
            </div>
            <div style={styles.modalSection}>
              <h3 style={styles.modalSectionTitle}>Focus Statistics</h3>
              <p style={styles.modalStat}>
                <strong>Current Score:</strong> {student.focusScore}%
              </p>
              <p style={styles.modalStat}>
                <strong>Status:</strong> {student.status}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// --- 3. Main Dashboard Component ---
const AdminDashboard = () => {
  const [activeNav, setActiveNav] = useState('Exams');
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [students, setStudents] = useState(MOCK_STUDENT_DATA);
  const [styles, setStyles] = useState(createStyles());

  // --- 4. Upgraded Data Simulator ---
  useEffect(() => {
    // This interval updates scores
    const scoreInterval = setInterval(() => {
      setStudents((prevStudents) =>
        prevStudents.map((student) => {
          // Don't update the 'critical' student
          if (student.status.includes('CRITICAL')) return student;

          let newScore = student.focusScore;
          let newStatus = student.status;
          const scoreChange = Math.random() * 10 - 4; // -4 to +6
          newScore = Math.max(0, Math.min(100, newScore + scoreChange));

          if (newScore > 80) newStatus = 'Focused';
          else if (newScore > 50) newStatus = 'Distracted';
          else newStatus = 'Low Attention';
          
          return { ...student, focusScore: Math.round(newScore), status: newStatus };
        })
      );
    }, 2000);

    // --- NEW: This timer triggers the impersonation alert ---
    const impersonationTimer = setTimeout(() => {
      // Flag Student #55 (id: 4) as 'CRITICAL'
      setStudents(prevStudents => 
        prevStudents.map(s => 
          s.id === 4 
            ? { ...s, status: 'CRITICAL: Impersonation Suspected', focusScore: 0 } 
            : s
        )
      );
      
      // Add a matching alert to the log
      setAlerts(prev => [{
        id: `critical-${Date.now()}`,
        time: new Date().toLocaleTimeString(),
        color: '#dc3545', // Red
        Icon: FiAlertTriangle,
        text: 'CRITICAL: Impersonation Alert for Student #55. Admin review required.'
      }, ...prev].slice(0, 5));

    }, 10000); // Triggers 10 seconds after the page loads

    return () => {
      clearInterval(scoreInterval);
      clearTimeout(impersonationTimer);
    };
  }, []); // Empty array ensures this runs only once on mount

  // --- 5. Helper Function for Border Color ---
  const getBorderColor = (score, status) => {
    if (status.includes('CRITICAL')) return '#dc3545'; // Red
    if (score > 80) return '#28a745'; // Green
    if (score > 50) return '#ffc107'; // Yellow
    return '#dc3545'; // Red
  };

  // --- 6. New Kick Student Function ---
  const handleKickStudent = (studentId, studentName) => {
    setStudents(prev => prev.filter(s => s.id !== studentId));
    setSelectedStudent(null); // Close the modal

    // Add a final "kicked" alert
    setAlerts(prev => [{
      id: `kicked-${studentId}`,
      time: new Date().toLocaleTimeString(),
      color: '#17a2b8', // Info color
      Icon: FiUserX,
      text: `${studentName} has been removed from the exam by admin.`
    }, ...prev].slice(0, 5));
  };

  // --- (No changes to Doughnut, NavItem, or static data) ---
  const FocusScoreDoughnut = ({ score }) => {
    const avgScore = Math.round(
      students.reduce((acc, s) => acc + s.focusScore, 0) / (students.length || 1)
    );
    const borderColor = getBorderColor(avgScore, '');
    return (
      <div style={styles.doughnutChartContainer}>
        <svg viewBox="0 0 120 120" style={styles.doughnutSvg}>
          <circle cx="60" cy="60" r={50} fill="none" stroke="#eef2ff" strokeWidth="10" />
          <circle
            cx="60" cy="60" r={50} fill="none"
            stroke={borderColor} strokeWidth="10"
            strokeDasharray={2 * Math.PI * 50}
            strokeDashoffset={(2 * Math.PI * 50) - (avgScore / 100) * (2 * Math.PI * 50)}
            strokeLinecap="round"
          />
        </svg>
        <span style={{ ...styles.scoreText, color: borderColor }}>{avgScore}%</span>
      </div>
    );
  };
  const NavItem = ({ name, icon: Icon }) => {
    return (
      <div style={styles.navItem(name)} onClick={() => setActiveNav(name)}>
        <Icon style={styles.navIcon} />
        <span>{name}</span>
      </div>
    );
  };
  const ongoingExams = [
    { time: '9:00 AM', title: 'Calculus I', progress: 83 },
    { time: '11:00 AM', title: 'World History', progress: 60 },
  ];
  // --- End of unchanged components ---

  return (
    <div style={styles.appBackground}>
      <div style={styles.dashboardCard}>
        {selectedStudent && (
          <StudentDetailModal
            student={selectedStudent}
            onClose={() => setSelectedStudent(null)}
            onKickStudent={handleKickStudent} // --- Pass the kick function
            styles={styles}
          />
        )}

        <aside style={styles.sidebar}>
          <div style={styles.logo}>LockIN</div>
          <NavItem name="Home" icon={FiHome} />
          <NavItem name="Exams" icon={FiClipboard} />
          <NavItem name="Students" icon={FiUsers} />
          <NavItem name="Reports" icon={FiBarChart2} />
          <NavItem name="Settings" icon={FiSettings} />
        </aside>

        <main style={styles.mainContent}>
          <header style={styles.header}>
            <FiSearch style={styles.headerIcon} />
            <FiBell style={styles.headerIcon} />
            <FiUser style={styles.headerIcon} />
          </header>

          <div style={styles.contentArea}>
            <div>
              <div style={styles.panel}>
                <h3 style={styles.panelTitle}>LIVE STUDENT FEEDS ({students.length})</h3>
                <div style={styles.feedsGrid}>
                  {/* --- 7. Main Render Logic (Updated) --- */}
                  {students.map((student) => {
                    const borderColor = getBorderColor(student.focusScore, student.status);
                    const isCritical = student.status.includes('CRITICAL');
                    return (
                      <div
                        key={student.id}
                        style={{
                          ...styles.feedItem,
                          backgroundImage: `url(${student.staticPhotoUrl})`,
                          border: `4px solid ${borderColor}`,
                          boxShadow: `0 0 15px ${borderColor}33`,
                          // --- NEW: Add pulsing animation for critical alerts ---
                          animation: isCritical ? 'pulse 1s infinite' : 'none',
                        }}
                        onClick={() => setSelectedStudent(student)}
                      >
                        <span
                          style={{
                            ...styles.feedOverlay,
                            backgroundColor: `${borderColor}CC`,
                          }}
                        >
                          {student.name} - {isCritical ? 'ALERT!' : `${student.focusScore}%`}
                        </span>
                      </div>
                    );
})}
                </div>
              </div>
              {/* ... other panels ... */}
            </div>

            <div>
              <div style={{ ...styles.panel, ...styles.scorePanel }}>
                <h3 style={styles.panelTitle}>OVERALL FOCUS SCORE</h3>
                <FocusScoreDoughnut />
                <p style={{ fontSize: '14px', color: '#555', marginTop: '10px' }}>
                  Average focus score.
                </p>
              </div>

              <div style={styles.panel}>
                <h3 style={styles.panelTitle}>ALERTS</h3>
                {alerts.length === 0 && (
                  <p style={{ fontSize: '14px', color: '#888' }}>No alerts yet.</p>
                )}
                {alerts.map((alert) => (
                  <div key={alert.id} style={styles.listItem(alert.color)}>
                    <alert.Icon style={styles.alertIcon(alert.color)} />
                    <div>
                      <span style={styles.alertText(alert.color)}>{alert.text}</span>
                      <span style={styles.alertTime}>{alert.time}</span>
                    </div>
                  </div>
                ))}
              </div>
              
              <div style={styles.panel}>
                <h3 style={styles.panelTitle}>ONGOING EXAMS</h3>
                {ongoingExams.map((exam, index) => (
                  <div key={index} style={{ ...styles.examItem, borderBottom: 'none' }}>
                     <div style={styles.examDetails}>
                      <span style={styles.examTime}>{exam.time}</span>
                      <span style={styles.examPercentage}>{exam.progress}%</span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#888', marginBottom: '5px' }}>
                      {exam.title}
                    </div>
                    <div style={styles.progressBarContainer}>
                      <div style={styles.progressBar(exam.progress)}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

// --- STYLES FUNCTION ---
// (This contains all your styles, with new additions for the modal)
function createStyles() {
  return {
    // ... (all previous styles) ...
    appBackground: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #a8c0ff 0%, #3f63c8 100%)', fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif", padding: '40px', boxSizing: 'border-box' },
    dashboardCard: { width: '1200px', height: '800px', maxWidth: '100%', maxHeight: '100%', borderRadius: '25px', backgroundColor: 'rgba(255, 255, 255, 0.95)', boxShadow: '0 10px 40px rgba(0, 0, 0, 0.1), 0 0 50px rgba(168, 192, 255, 0.3)', backdropFilter: 'blur(10px)', display: 'grid', gridTemplateColumns: '220px 1fr', overflow: 'hidden', position: 'relative' },
    sidebar: { padding: '25px 0', borderRight: '1px solid #eee', backgroundColor: 'white', display: 'flex', flexDirection: 'column' },
    logo: { fontSize: '24px', fontWeight: '700', color: '#333366', padding: '0 25px 30px 25px' },
    navItem: (name) => ({ display: 'flex', alignItems: 'center', padding: '12px 25px', fontSize: '15px', fontWeight: '500', color: '#555', backgroundColor: 'transparent', paddingLeft: '25px', borderLeft: '4px solid transparent', cursor: 'pointer', transition: 'all 0.2s ease' }),
    navIcon: { marginRight: '15px', fontSize: '18px' },
    mainContent: { display: 'flex', flexDirection: 'column', overflow: 'hidden' },
    header: { display: 'flex', justifyContent: 'flex-end', alignItems: 'center', padding: '15px 30px', borderBottom: '1px solid #eee', backgroundColor: 'white', height: '70px', flexShrink: 0 },
    headerIcon: { fontSize: '20px', color: '#777', marginLeft: '15px', cursor: 'pointer' },
    contentArea: { padding: '30px', display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px', overflowY: 'auto', backgroundColor: '#f9f9ff', flexGrow: 1 },
    panel: { backgroundColor: 'white', borderRadius: '15px', padding: '20px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)', marginBottom: '30px' },
    panelTitle: { fontSize: '16px', fontWeight: '600', color: '#333', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '0.5px' },
    feedsGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' },
    feedItem: { position: 'relative', borderRadius: '10px', overflow: 'hidden', height: '140px', backgroundColor: '#e0e0e0', backgroundSize: 'cover', backgroundPosition: 'center', cursor: 'pointer', transition: 'transform 0.2s ease, box-shadow 0.2s ease', border: '4px solid transparent' },
    feedItemHover: { transform: 'scale(1.03)', boxShadow: '0 8px 20px rgba(0, 0, 0, 0.1)' },
    feedOverlay: { position: 'absolute', bottom: '10px', left: '10px', padding: '3px 8px', borderRadius: '15px', fontSize: '12px', fontWeight: '600', color: 'white' },
    scorePanel: { display: 'flex', flexDirection: 'column', alignItems: 'center' },
    doughnutChartContainer: { position: 'relative', width: '120px', height: '120px', marginBottom: '10px' },
    scoreText: { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: '28px', fontWeight: '700' },
    doughnutSvg: { transform: 'rotate(-90deg)' },
    listItem: (color = '#555') => ({ display: 'flex', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0', fontSize: '14px', color: color, cursor: 'default' }),
    listIcon: { fontSize: '16px', marginRight: '10px', color: '#999' },
    listDetail: { marginLeft: 'auto', fontWeight: '600', fontSize: '13px', color: '#777' },
    alertIcon: (color) => ({ fontSize: '16px', marginRight: '10px', color: color }),
    alertText: (color) => ({ fontSize: '14px', fontWeight: '500', color: color }),
    examItem: { padding: '10px 0', borderBottom: '1px solid #f0f0f0' },
    examTime: { fontSize: '15px', fontWeight: '600', color: '#333', marginBottom: '5px' },
    examDetails: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
    examTitle: { fontSize: '14px', fontWeight: '500', color: '#444' },
    examPercentage: { fontSize: '14px', fontWeight: '600', color: '#4a70f0' },
    progressBarContainer: { height: '6px', backgroundColor: '#e0eaff', borderRadius: '3px', marginTop: '5px' },
    progressBar: (width) => ({ height: '100%', width: `${width}%`, backgroundColor: '#4a70f0', borderRadius: '3px' }),
    alertTime: { fontSize: '11px', color: '#888', display: 'block', marginTop: '2px' },
    modalBackdrop: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.5)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
    modalContent: { width: '700px', maxWidth: '90%', backgroundColor: 'white', borderRadius: '15px', boxShadow: '0 10px 30px rgba(0, 0, 0, 0.2)', overflow: 'hidden' },
    modalHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 25px', borderBottom: '1px solid #eee' },
    modalTitle: { fontSize: '18px', fontWeight: '600', color: '#333' },
    modalCloseButton: { background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '24px', color: '#888' },
    modalBody: { padding: '25px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '25px' },
    modalSection: { display: 'flex', flexDirection: 'column' },
    modalSectionTitle: { fontSize: '16px', fontWeight: '600', color: '#333366', borderBottom: '2px solid #eef2ff', paddingBottom: '5px', marginBottom: '15px' },
    modalStat: { fontSize: '14px', color: '#555', marginBottom: '10px' },
    
    // --- NEW STYLES FOR IMPERSONATION MODAL ---
    criticalAlertBox: {
      gridColumn: '1 / -1', // Span full width
      display: 'flex',
      flexDirection: 'row',
      alignItems: 'center',
      padding: '15px',
      backgroundColor: '#f8d7da',
      color: '#721c24',
      borderRadius: '10px',
      border: '1px solid #f5c6cb',
    },
    modalPhotoLabel: {
      fontSize: '14px',
      fontWeight: '600',
      color: '#555',
      marginBottom: '10px',
    },
    modalPhoto: {
      width: '100%',
      borderRadius: '10px',
      border: '1px solid #ddd',
    },
    modalActionButtons: {
      gridColumn: '1 / -1',
      display: 'flex',
      gap: '15px',
      marginTop: '20px',
    },
    modalButton: {
      flex: 1,
      padding: '12px',
      fontSize: '16px',
      fontWeight: '600',
      borderRadius: '8px',
      border: 'none',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'opacity 0.2s',
    },
    modalButtonConfirm: {
      backgroundColor: '#dc3545',
      color: 'white',
    },
    modalButtonIgnore: {
      backgroundColor: '#6c757d',
      color: 'white',
    }
  };
}

// --- NEW: CSS KEYFRAMES FOR PULSING BORDER ---
// We need to inject this into the page.
const pulseAnimation = `
@keyframes pulse {
  0% { box-shadow: 0 0 15px #dc354533; }
  50% { box-shadow: 0 0 25px #dc3545CC; }
  100% { box-shadow: 0 0 15px #dc354533; }
}
`;

// A small component to inject the keyframes
const GlobalStyles = () => {
  return (
    <style>
      {pulseAnimation}
    </style>
  );
};

// --- FINAL EXPORT ---
// We wrap the dashboard in a Fragment to include the global styles
export default function DashboardWrapper() {
  return (
    <>
      <GlobalStyles />
      <AdminDashboard />
    </>
  );
}