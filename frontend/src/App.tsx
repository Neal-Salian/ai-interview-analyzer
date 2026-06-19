import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import SessionsPage from './pages/SessionsPage'
import LiveDashboard from './pages/LiveDashboard'
import ReportPage from './pages/ReportPage'
import CandidatePage from './pages/CandidatePage'
import InterviewHistoryPage from './pages/InterviewHistoryPage'
import { ThemeProvider } from './context/ThemeContext';
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import JobsPage from './pages/JobsPage'
import JobDetailsPage from './pages/JobDetailsPage'

import UsersPage from './pages/admin/UsersPage'
import AuditLogsPage from './pages/admin/AuditLogsPage'
import SettingsPage from './pages/admin/SettingsPage'

// Inside <Routes> after /login:


export default function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
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
            <Route path="/history" element={
              <ProtectedRoute><InterviewHistoryPage /></ProtectedRoute>
            } />
            <Route path="/jobs" element={
              <ProtectedRoute><JobsPage /></ProtectedRoute>
            } />
            <Route path="/jobs/:id" element={
              <ProtectedRoute><JobDetailsPage /></ProtectedRoute>
            } />
            
            {/* Admin Only Protected */}
            <Route path="/admin/users" element={
              <ProtectedRoute allowedRoles={['ADMIN']}><UsersPage /></ProtectedRoute>
            } />
            <Route path="/admin/audit-logs" element={
              <ProtectedRoute allowedRoles={['ADMIN']}><AuditLogsPage /></ProtectedRoute>
            } />
            <Route path="/admin/settings" element={
              <ProtectedRoute allowedRoles={['ADMIN']}><SettingsPage /></ProtectedRoute>
            } />

            {/* Default redirect */}
            <Route path="*" element={<Navigate to="/sessions" replace />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </AuthProvider>
  )
}
