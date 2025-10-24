// src/App.jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import StudentLogin from './pages/StudentLogin'
import AdminLogin from './pages/AdminLogin'
import AdminDashboard from './pages/AdminDashboard'

function App() {
  return (
    // We REMOVED the wrapper <div className="min-h-screen..."> from here
    <Routes>
      <Route path="/" element={<Navigate to="/student-login" />} />
      <Route path="/student-login" element={<StudentLogin />} />
      <Route path="/admin-login" element={<AdminLogin />} />
      <Route path="/admin-dashboard" element={<AdminDashboard />} />
    </Routes>
    // We REMOVED the wrapper </div> from here
  )
}

export default App