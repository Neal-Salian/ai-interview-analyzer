import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import type { ReactNode } from 'react'
import DashboardLayout from '../layouts/DashboardLayout'

interface ProtectedRouteProps {
    children: ReactNode
    allowedRoles?: string[]
}

export default function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
    const { isAuthenticated, role } = useAuth()
    
    if (!isAuthenticated) return <Navigate to="/login" replace />
    
    if (allowedRoles && role && !allowedRoles.includes(role)) {
        return <Navigate to="/" replace /> // or a 403 page
    }
    
    return <DashboardLayout>{children}</DashboardLayout>
}