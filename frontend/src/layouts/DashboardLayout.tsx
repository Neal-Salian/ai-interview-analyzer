import type { ReactNode } from 'react'
import Sidebar from '../components/Sidebar'

interface DashboardLayoutProps {
    children: ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
    return (
        <div className="dashboard-layout">
            <Sidebar />
            <div className="dashboard-content">
                {children}
            </div>
        </div>
    )
}
