// src/components/StudentVideoTile.jsx
import React, { useEffect, useRef, useState } from 'react';
import Peer from 'simple-peer';

const StudentVideoTile = ({ student, socket, onStudentClick }) => {
  const videoRef = useRef();
  const peerRef = useRef();
  const [focusScore, setFocusScore] = useState(100);
  const [status, setStatus] = useState('ONLINE');

  const styles = {
    feedItem: {
      position: 'relative',
      borderRadius: '10px',
      overflow: 'hidden',
      height: '140px',
      backgroundColor: '#000', // Black background
      cursor: 'pointer',
      transition: 'transform 0.2s ease, box-shadow 0.2s ease',
    },
    video: {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
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
      backgroundColor: 'rgba(0, 204, 0, 0.8)',
    },
    feedOverlayAlert: {
      backgroundColor: 'rgba(217, 83, 79, 0.8)',
    },
  };

  useEffect(() => {
    // 1. Create a NEW peer (as the receiver)
    const peer = new Peer({
      initiator: false, // Not the initiator
      trickle: false,
    });

    // 2. This event fires when the peer has the "answer" ready
    peer.on('signal', (answer) => {
      // Send this "answer" back to the specific student
      socket.emit('adminAnswer', {
        answer: answer,
        studentSocketId: student.socketId,
      });
    });

    // 4. This event fires when the student's video stream arrives
    peer.on('stream', (stream) => {
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    });

    // 5. This event fires when the ML backend sends analysis data
    // (This assumes the backend links analysis to a socketId)
    const analysisListener = (data) => {
      if (data.studentSocketId === student.socketId) {
        setFocusScore(data.focus_score);
        setStatus(data.status);
      }
    };
    socket.on('analysis_result', analysisListener);

    // 3. Signal the peer with the student's "offer"
    peer.signal(student.offer);
    peerRef.current = peer;

    return () => {
      peer.destroy();
      socket.off('analysis_result', analysisListener);
    };
  }, [student.socketId, student.offer, socket]);

  const getStatusStyle = () =>
    status === 'ALERT' || status === 'Away' || status === 'Phone Detected'
      ? styles.feedOverlayAlert
      : {};

  return (
    <div
      style={styles.feedItem}
      onClick={() =>
        onStudentClick({ ...student, focusScore, status, img: null })
      }
      onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.03)')}
      onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
    >
      <video ref={videoRef} autoPlay playsInline style={styles.video} />
      <span style={{ ...styles.feedOverlay, ...getStatusStyle() }}>
        {student.name} - {focusScore}%
      </span>
    </div>
  );
};

export default StudentVideoTile;