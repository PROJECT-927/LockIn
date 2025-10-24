// src/pages/StudentExam.jsx
import React, { useRef, useEffect } from 'react';

// This is the webcam component. It *only* lives on the student's page.
const StudentVideoFeed = () => {
  const videoRef = useRef(null);

  const styles = {
    videoContainer: {
      width: '100%',
      maxWidth: '600px',
      borderRadius: '15px',
      overflow: 'hidden',
      backgroundColor: '#000',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
    },
    video: {
      width: '100%',
      height: 'auto',
      display: 'block',
    },
  };

  useEffect(() => {
    // Get the student's webcam
    const getVideoStream = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("Error accessing student's webcam:", err);
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
    <div style={styles.videoContainer}>
      <video ref={videoRef} autoPlay playsInline muted style={styles.video} />
    </div>
  );
};

// This is the main page component
export default function StudentExam() {
  // We'll re-use the same background style from your login page
  const styles = {
    appBackground: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #a8c0ff 0%, #3f63c8 100%)',
      fontFamily: "'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    card: {
      width: '800px',
      maxWidth: '90%',
      padding: '40px',
      borderRadius: '30px',
      backgroundColor: 'white',
      boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '20px',
    },
    title: {
      fontSize: '24px',
      fontWeight: '600',
      color: '#333366',
    },
    subtitle: {
      fontSize: '16px',
      color: '#555',
    },
  };

  return (
    <div style={styles.appBackground}>
      <div style={styles.card}>
        <h1 style={styles.title}>Exam in Progress</h1>
        <p style={styles.subtitle}>
          Your camera is now active for proctoring.
        </p>
        <StudentVideoFeed />
        {/* The actual exam questions/content would go here */}
      </div>
    </div>
  );
}