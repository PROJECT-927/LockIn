// src/pages/StudentLogin.jsx
import React, { useState } from 'react';
// I've corrected the import for FiKey. It's in 'fi', not 'fa'.
import { FiUser, FiLock, FiKey } from 'react-icons/fi';

const StudentLogin = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isHovered, setIsHovered] = useState(false);

  const handleLogin = (e) => {
    e.preventDefault();
    // TODO: Add real login logic
    console.log('Attempting login with:', { username, password });
    alert(`Login attempted!\nUsername: ${username}\nPassword: ${password}`);
  };

  const styles = {
    appBackground: {
      position: 'fixed', // cover full viewport
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
    card: {
      width: '700px', // widened for side-by-side layout
      maxWidth: '95%',
      padding: '30px',
      borderRadius: '30px',
      backgroundColor: 'white',
      boxShadow:
        '0 10px 30px rgba(0, 0, 0, 0.1), 0 0 50px rgba(168, 192, 255, 0.5)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      flexDirection: 'row', // side by side
      alignItems: 'flex-start',
      position: 'relative',
      overflow: 'hidden',
    },
    formContainer: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      marginRight: '20px', // space between form and image
    },
    logoContainer: {
      display: 'flex',
      alignItems: 'center',
      marginBottom: '5px',
    },
    logoText: {
      fontSize: '40px',
      fontWeight: '700',
      color: '#333366',
      letterSpacing: '0.5px',
      lineHeight: '1',
    },
    logoIcon: {
      color: '#4a70f0',
      fontSize: '40px',
      margin: '0 2px',
      display: 'inline-block',
      transform: 'translateY(-2px)',
    },
    subtitle: {
      fontSize: '14px',
      fontWeight: '500',
      color: '#555',
      letterSpacing: '2px',
      textTransform: 'uppercase',
      marginBottom: '30px',
    },
    inputGroup: {
      width: '100%',
      marginBottom: '20px',
    },
    inputWrapper: {
      display: 'flex',
      alignItems: 'center',
      height: '55px',
      backgroundColor: 'white',
      borderRadius: '28px',
      padding: '0 20px',
      boxShadow: '0 2px 10px rgba(0, 0, 0, 0.05)',
      border: '1px solid #eee',
    },
    inputIcon: {
      color: '#888',
      fontSize: '18px',
      marginRight: '12px',
    },
    input: {
      flexGrow: '1',
      border: 'none',
      outline: 'none',
      backgroundColor: 'transparent',
      fontSize: '16px',
      color: '#333',
    },
    loginButton: {
      width: '100%',
      height: '55px',
      borderRadius: '28px',
      border: 'none',
      fontSize: '18px',
      fontWeight: '600',
      color: 'white',
      cursor: 'pointer',
      background: 'linear-gradient(90deg, #4a70f0 0%, #6f5edc 100%)',
      boxShadow: '0 8px 20px rgba(74, 112, 240, 0.4)',
      transition: 'all 0.3s ease',
      marginTop: '10px',
      marginBottom: '15px',
    },
    loginButtonHover: {
      opacity: '0.9',
      boxShadow: '0 10px 25px rgba(74, 112, 240, 0.6)',
    },
    forgotPassword: {
      fontSize: '13px',
      color: '#4a70f0',
      textDecoration: 'none',
      fontWeight: '500',
      alignSelf: 'flex-start',
      marginLeft: '5px',
      transition: 'color 0.2s',
      marginBottom: '20px',
    },
    illustrationContainer: {
      width: '300px',
      position: 'relative',
      flexShrink: 0,
    },
    illustrationImage: {
      width: '100%',
      position: 'absolute',
      top: '60px', // aligns roughly with middle/lower section of password input
      right: '0',
      height: '400px',
      backgroundImage:
        'url("https://static.vecteezy.com/system/resources/previews/017/637/810/non_2x/safer-internet-day-concept-illustration-of-safe-internet-man-with-computer-vector.jpg")',
      backgroundSize: 'contain',
      backgroundRepeat: 'no-repeat',
      backgroundPosition: 'right top',
    },
  };

  const CustomInput = ({ icon: Icon, placeholder, type, value, onChange }) => (
    <div style={styles.inputWrapper}>
      <Icon style={styles.inputIcon} />
      <input
        key={`input-${placeholder}`}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        style={styles.input}
      />
    </div>
  );

  return (
    <div style={styles.appBackground}>
      <div style={styles.card}>
        {/* Form Section */}
        <div style={styles.formContainer}>
          {/* LockIN Logo */}
<div style={styles.logoContainer}>
  <span style={styles.logoText}>L</span>
  <div
    style={{
      width: '40px',
      height: '40px',
      borderRadius: '50%',
      background: 'linear-gradient(135deg, #4a70f0 0%, #6f5edc 100%)', // gradient background
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)', // subtle shadow
      margin: '0 4px',
      transition: 'transform 0.3s ease', // smooth hover effect
      cursor: 'pointer',
    }}
    onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.1)')}
    onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
  >
    <FiLock style={{ color: 'white', fontSize: '24px' }} /> {/* slightly bigger icon */}
  </div>
  <span style={styles.logoText}>ckIN</span>
</div>


          <h2 style={styles.subtitle}>STUDENT LOGIN</h2>

          <form onSubmit={handleLogin} style={{ width: '100%' }}>
            <div style={styles.inputGroup}>
              <CustomInput
                icon={FiUser}
                placeholder="USERNAME"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div style={styles.inputGroup}>
              <CustomInput
                icon={FiLock}
                placeholder="PASSWORD"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              style={{
                ...styles.loginButton,
                ...(isHovered ? styles.loginButtonHover : {}),
              }}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
            >
              LOGIN
            </button>
          </form>

          <a
            href="#"
            style={styles.forgotPassword}
            onClick={(e) => {
              e.preventDefault();
              alert('Forgot Password clicked!');
            }}
          >
            Forgot Password?
          </a>
        </div>

        {/* Illustration Section */}
        <div style={styles.illustrationContainer}>
          <div style={styles.illustrationImage}></div>
        </div>
      </div>
    </div>
  );
};

export default StudentLogin;