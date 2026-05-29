import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import SessionsPage from './pages/SessionsPage'
import LiveDashboard from './pages/LiveDashboard'
import ReportPage from './pages/ReportPage'
import CandidatePage from './pages/CandidatePage'
import { ThemeProvider } from './context/ThemeContext';

export default function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected */}
            <Route path="/sessions" element={
              <ProtectedRoute><SessionsPage /></ProtectedRoute>
            } />
            <Route path="/sessions/:id/live" element={
              <ProtectedRoute><LiveDashboard /></ProtectedRoute>
            } />
            <Route path="/sessions/:id/report" element={
              <ProtectedRoute><ReportPage /></ProtectedRoute>
            } />
            <Route path="/candidates/new" element={
              <ProtectedRoute><CandidatePage /></ProtectedRoute>
            } />

            {/* Default redirect */}
            <Route path="*" element={<Navigate to="/sessions" replace />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  )
}
