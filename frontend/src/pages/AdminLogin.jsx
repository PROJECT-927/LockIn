import React, { useState } from 'react';
import { FiUser, FiLock, FiKey } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';

const AdminLogin = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isHovered, setIsHovered] = useState(false);
  const navigate = useNavigate(); 

  const handleLogin = (e) => {
    e.preventDefault();

    if (username === 'admin@test.com' && password === 'password') {
      console.log('Mock Admin Login Successful');
      navigate('/admin-dashboard');
    } else {
      alert('Invalid credentials. (Use admin@test.com / password)');
    }
  };

  const styles = {
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
      overflow: 'hidden',
    },
    card: {
      width: '700px',
      maxWidth: '95%',
      padding: '30px',
      borderRadius: '30px',
      backgroundColor: 'white',
      boxShadow:
        '0 10px 30px rgba(0, 0, 0, 0.1), 0 0 50px rgba(168, 192, 255, 0.5)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      flexDirection: 'row',
      alignItems: 'flex-start',
      position: 'relative',
      overflow: 'hidden',
    },
    formContainer: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      marginRight: '20px',
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
      width: '300px',
      position: 'absolute',
      top: '60px',
      right: '0',
      height: '250px',
      backgroundImage:
        'url("data:image/jpeg;base64,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")',
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


          {/* --- THIS IS THE CHANGED LINE --- */}
          <h2 style={styles.subtitle}>ADMIN LOGIN</h2>

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

export default AdminLogin; 