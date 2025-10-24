// src/pages/AdminDashboard.jsx
import React, { useState, useEffect, useRef } from 'react'; // Added useEffect and useRef
import {
  FiHome,
  FiClipboard,
  FiUsers,
  FiBarChart2,
  FiSettings,
  FiBell,
  FiUser,
  FiSearch,
  FiAlertTriangle,
  FiAlertCircle,
} from 'react-icons/fi';

// --- NEW COMPONENT ---
// This component handles the webcam feed.
const LiveVideoFeed = () => {
  const videoRef = useRef(null);
  const styles = {
    feedItem: {
      position: 'relative',
      borderRadius: '10px',
      overflow: 'hidden',
      height: '140px',
      backgroundColor: '#000', // Black background
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    },
    video: {
      width: '100%',
      height: '100%',
      objectFit: 'cover', // Ensures video fills the box
    },
    feedOverlay: {
      position: 'absolute',
      bottom: '10px',
      left: '10px',
      padding: '3px 8px',
      borderRadius: '15px',
      fontSize: '12px',
      fontWeight: '600',
      color: 'white',
      backgroundColor: '#00cc00', // Green "ONLINE"
    },
  };

  useEffect(() => {
    // Get user's webcam
    const getVideoStream = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        // TODO: When backend is ready, start sending frames from here
      } catch (err) {
        console.error('Error accessing webcam:', err);
      }
    };

    getVideoStream();

    // Clean up
    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <div style={styles.feedItem}>
      <video ref={videoRef} autoPlay playsInline muted style={styles.video} />
      <span style={styles.feedOverlay}>LIVE</span>
    </div>
  );
};
// --- END OF NEW COMPONENT ---

const AdminDashboard = () => {
  const [activeNav, setActiveNav] = useState('Exams');

  // --- NEW DYNAMIC STATE ---
  const [focusScore, setFocusScore] = useState(85);
  const [alerts, setAlerts] = useState([
    // Pre-populate with your static alerts
    {
      id: 1,
      time: new Date().toLocaleTimeString(),
      color: '#D9534F',
      Icon: FiAlertTriangle,
      text: 'Student #12: Unauthorized Device Detected',
    },
    {
      id: 2,
      time: new Date().toLocaleTimeString(),
      color: '#F0AD4E',
      Icon: FiAlertCircle,
      text: 'Student ID 448: Low Attention - Eye Movement',
    },
  ]);

  // --- MOCK DATA SIMULATOR ---
  useEffect(() => {
    const mockDataInterval = setInterval(() => {
      // 1. Update Focus Score
      setFocusScore((prevScore) => {
        const change = Math.random() * 10 - 5; // Change between -5 and +5
        const newScore = Math.round(prevScore + change);
        return Math.min(100, Math.max(0, newScore)); // Clamp between 0 and 100
      });

      // 2. Randomly add a new alert
      if (Math.random() < 0.2) { // 20% chance to add an alert
        const newAlert = {
          id: Date.now(),
          time: new Date().toLocaleTimeString(),
          color: '#D9534F',
          Icon: FiAlertTriangle,
          text: `New Alert: Student ${Math.floor(Math.random() * 100)} is AFK`,
        };
        
        // Add new alert to the top, keep only the 5 most recent
        setAlerts((prevAlerts) => [newAlert, ...prevAlerts].slice(0, 5));
      }
    }, 2500); // Update every 2.5 seconds

    // Clean up interval on unmount
    return () => clearInterval(mockDataInterval);
  }, []); // Empty dependency array so it only runs once
  // --- END OF MOCK DATA SIMULATOR ---

  const styles = {
    appBackground: {
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #a8c0ff 0%, #3f63c8 100%)',
      fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      padding: '40px',
      boxSizing: 'border-box',
    },
    dashboardCard: {
      width: '1200px',
      height: '800px',
      maxWidth: '100%',
      maxHeight: '100%',
      borderRadius: '25px',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      boxShadow:
        '0 10px 40px rgba(0, 0, 0, 0.1), 0 0 50px rgba(168, 192, 255, 0.3)',
      backdropFilter: 'blur(10px)',
      display: 'grid',
      gridTemplateColumns: '220px 1fr',
      overflow: 'hidden',
    },
    sidebar: {
      padding: '25px 0',
      borderRight: '1px solid #eee',
      backgroundColor: 'white',
      display: 'flex',
      flexDirection: 'column',
    },
    logo: {
      fontSize: '24px',
      fontWeight: '700',
      color: '#333366',
      padding: '0 25px 30px 25px',
    },
    navItem: (name) => ({
      display: 'flex',
      alignItems: 'center',
      padding: '12px 25px',
      fontSize: '15px',
      fontWeight: name === activeNav ? '600' : '500',
      color: name === activeNav ? '#4a70f0' : '#555',
      backgroundColor: name === activeNav ? '#eef2ff' : 'transparent',
      paddingLeft: name === activeNav ? '21px' : '25px',
      borderLeft:
        name === activeNav ? '4px solid #4a70f0' : '4px solid transparent',
      cursor: 'pointer',
      transition: 'all 0.2s ease',
    }),
    navIcon: {
      marginRight: '15px',
      fontSize: '18px',
    },
    mainContent: {
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    },
    header: {
      display: 'flex',
      justifyContent: 'flex-end',
      alignItems: 'center',
      padding: '15px 30px',
      borderBottom: '1px solid #eee',
      backgroundColor: 'white',
      height: '70px',
      flexShrink: 0,
    },
    headerIcon: {
      fontSize: '20px',
      color: '#777',
      marginLeft: '15px',
      cursor: 'pointer',
    },
    contentArea: {
      padding: '30px',
      display: 'grid',
      gridTemplateColumns: '2fr 1fr',
      gap: '30px',
      overflowY: 'auto',
      backgroundColor: '#f9f9ff',
      flexGrow: 1,
    },
    panel: {
      backgroundColor: 'white',
      borderRadius: '15px',
      padding: '20px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
      marginBottom: '30px',
    },
    panelTitle: {
      fontSize: '16px',
      fontWeight: '600',
      color: '#333',
      marginBottom: '20px',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    },
    feedsGrid: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '15px',
    },
    feedItem: {
      position: 'relative',
      borderRadius: '10px',
      overflow: 'hidden',
      height: '140px',
      backgroundColor: '#e0e0e0',
      backgroundSize: 'cover',
      backgroundPosition: 'center',
    },
    feedOverlay: {
      position: 'absolute',
      bottom: '10px',
      left: '10px',
      padding: '3px 8px',
      borderRadius: '15px',
      fontSize: '12px',
      fontWeight: '600',
      color: 'white',
      backgroundColor: '#00cc00',
    },
    scorePanel: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
    },
    doughnutChartContainer: {
      position: 'relative',
      width: '120px',
      height: '120px',
      marginBottom: '10px',
    },
    scoreText: {
      position: 'absolute',
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      fontSize: '28px',
      fontWeight: '700',
      color: '#4a70f0',
    },
    doughnutSvg: {
      transform: 'rotate(-90deg)',
    },
    listItem: (color = '#555') => ({
      display: 'flex',
      alignItems: 'center',
      padding: '8px 0',
      borderBottom: '1px solid #f0f0f0',
      fontSize: '14px',
      color: color,
      cursor: 'default',
    }),
    listIcon: {
      fontSize: '16px',
      marginRight: '10px',
      color: '#999',
    },
    listDetail: {
      marginLeft: 'auto',
      fontWeight: '600',
      fontSize: '13px',
      color: '#777',
    },
    alertIcon: (color) => ({
      fontSize: '16px',
      marginRight: '10px',
      color: color,
    }),
    alertText: (color) => ({
      fontSize: '14px',
      fontWeight: '500',
      color: color,
    }),
    examItem: {
      padding: '10px 0',
      borderBottom: '1px solid #f0f0f0',
    },
    examTime: {
      fontSize: '15px',
      fontWeight: '600',
      color: '#333',
      marginBottom: '5px',
    },
    examDetails: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    examTitle: {
      fontSize: '14px',
      fontWeight: '500',
      color: '#444',
    },
    examPercentage: {
      fontSize: '14px',
      fontWeight: '600',
      color: '#4a70f0',
    },
    progressBarContainer: {
      height: '6px',
      backgroundColor: '#e0eaff',
      borderRadius: '3px',
      marginTop: '5px',
    },
    progressBar: (width) => ({
      height: '100%',
      width: `${width}%`,
      backgroundColor: '#4a70f0',
      borderRadius: '3px',
    }),
    // Style for the alert's timestamp
    alertTime: {
      fontSize: '11px',
      color: '#888',
      display: 'block',
      marginTop: '2px',
    }
  };

  const FocusScoreDoughnut = ({ score }) => {
    const radius = 50;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    const strokeColor = '#4a70f0';
    const trackColor = '#eef2ff';

    return (
      <div style={styles.doughnutChartContainer}>
        <svg viewBox="0 0 120 120" style={styles.doughnutSvg}>
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={trackColor}
            strokeWidth="10"
          />
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <span style={styles.scoreText}>{score}%</span>
      </div>
    );
  };

  const NavItem = ({ name, icon: Icon }) => (
    <div style={styles.navItem(name)} onClick={() => setActiveNav(name)}>
      <Icon style={styles.navIcon} />
      <span>{name}</span>
    </div>
  );

  // Static placeholder feeds for #2, 3, 4
  const placeholderFeeds = [
    { name: 'Student 2', img: 'https://i.imgur.com/G3t7jYJ.png', status: 'ONLINE' },
    { name: 'Student 3', img: 'https://i.imgur.com/G3t7jYJ.png', status: 'ONLINE' },
    { name: 'Student 4', img: 'https://i.imgur.com/G3t7jYJ.png', status: 'ONLINE' },
  ];

  const recentActivity = [
    { text: 'Searched student feeds', time: '4:00 AM', detail: '' },
    { text: 'Cooked #fixed', time: '4:00 AM', detail: '90%' },
    { text: 'Tepoasoild Bic', time: '3:50 AM', detail: '30%' },
  ];

  const ongoingExams = [
    {
      time: '9:00 AM',
      title: 'Calculus I',
      subtitle: 'Veasmed Imiqit',
      progress: 83,
    },
    {
      time: '11:00 AM',
      title: 'World History',
      subtitle: 'Venvic Exams',
      progress: 60,
    },
  ];

  return (
    <div style={styles.appBackground}>
      <div style={styles.dashboardCard}>
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
                <h3 style={styles.panelTitle}>LIVE STUDENT FEEDS</h3>
                <div style={styles.feedsGrid}>
                  {/* --- MODIFICATION --- */}
                  {/* The first feed is now the live webcam */}
                  <LiveVideoFeed />

                  {/* The other 3 are placeholders */}
                  {placeholderFeeds.map((feed, index) => (
                    <div
                      key={index}
                      style={{
                        ...styles.feedItem,
                        backgroundImage: `url('${feed.img}')`,
                      }}
                    >
                      <span style={styles.feedOverlay}>{feed.status}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ ...styles.panel, paddingBottom: '10px' }}>
                <h3 style={styles.panelTitle}>#REECIS</h3>
                <div>
                  {recentActivity.map((item, index) => (
                    <div
                      key={index}
                      style={{
                        ...styles.listItem(),
                        borderBottom:
                          index < recentActivity.length - 1
                            ? styles.listItem().borderBottom
                            : 'none',
                      }}
                    >
                      <FiSearch style={styles.listIcon} />
                      <span>{item.text}</span>
                      <span style={styles.listDetail}>
                        {item.time}
                        {item.detail && ` | ${item.detail}`}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ ...styles.panel, paddingBottom: '10px' }}>
                <h3 style={styles.panelTitle}>CAACUING LAMS</h3>
                <div>
                  <div
                    style={{
                      ...styles.listItem(),
                      borderBottom: styles.listItem().borderBottom,
                    }}
                  >
                    <FiClipboard style={styles.listIcon} />
                    <span>World History</span>
                    <span style={styles.listDetail}>1:00 AM</span>
                  </div>
                  <div style={{ ...styles.listItem(), borderBottom: 'none' }}>
                    <FiClipboard style={styles.listIcon} />
                    <span>Tøjñwæs ‡ž‡šī boæpe</span>
                    <span style={styles.listDetail}>3:30 AM</span>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <div style={{ ...styles.panel, ...styles.scorePanel }}>
                <h3 style={styles.panelTitle}>FOCUS/ATTENTION SCORES</h3>
                {/* --- MODIFICATION --- */}
                {/* Score is now dynamic */}
                <FocusScoreDoughnut score={focusScore} />
                <p style={{ fontSize: '14px', color: '#555', marginTop: '10px' }}>
                  {focusScore}% overall focus score.
                </p>
              </div>

              <div style={styles.panel}>
                <h3 style={styles.panelTitle}>ALERTS</h3>
                {/* --- MODIFICATION --- */}
                {/* Alerts are now mapped from dynamic state */}
                {alerts.length === 0 && (
                  <p style={{fontSize: '14px', color: '#888'}}>No alerts yet.</p>
                )}
                {alerts.map((alert) => (
                  <div key={alert.id} style={styles.listItem(alert.color)}>
                    <alert.Icon style={styles.alertIcon(alert.color)} />
                    <div>
                      <span style={styles.alertText(alert.color)}>
                        {alert.text}
                      </span>
                      <span style={styles.alertTime}>{alert.time}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div style={styles.panel}>
                <h3 style={styles.panelTitle}>ONGOING EXAMS</h3>
                {ongoingExams.map((exam, index) => (
                  <div
                    key={index}
                    style={{
                      ...styles.examItem,
                      borderBottom:
                        index < ongoingExams.length - 1
                          ? styles.examItem.borderBottom
                          : 'none',
                    }}
                  >
                    <div style={styles.examDetails}>
                      <span style={styles.examTime}>{exam.time}</span>
                      <span style={styles.examPercentage}>{exam.progress}%</span>
                    </div>
                    <div
                      style={{
                        fontSize: '13px',
                        color: '#888',
                        marginBottom: '5px',
                      }}
                    >
                      {exam.title} | {exam.subtitle}
                    </div>

                    <div style={styles.progressBarContainer}>
                      <div style={styles.progressBar(exam.progress)}></div>
                    </div>
                  </div>
                ))}

                <div
                  style={{
                    marginTop: '15px',
                    paddingTop: '10px',
                    borderTop: '1px solid #f0f0f0',
                  }}
                >
                  <div style={styles.examDetails}>
                    <span
                      style={{
                        fontSize: '14px',
                        fontWeight: '500',
                        color: '#444',
                      }}
                    >
                      Active students
                    </span>
                    <span style={styles.examPercentage}>20%</span>
                  </div>
                  <div style={styles.progressBarContainer}>
                    <div style={styles.progressBar(20)}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;