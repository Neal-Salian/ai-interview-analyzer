import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Sidebar() {
    const location = useLocation()
    const navigate = useNavigate()
    const { role } = useAuth()

    const isActive = (path: string) => location.pathname.startsWith(path)

    const NavItem = ({ path, icon, label, exact = false }: { path: string, icon: string, label: string, exact?: boolean }) => {
        const active = exact ? location.pathname === path : isActive(path)
        
        return (
            <button
                onClick={() => navigate(path)}
                className={`sidebar-nav-item ${active ? 'sidebar-nav-item--active' : ''}`}
                aria-current={active ? 'page' : undefined}
            >
                <span className="material-symbols-outlined sidebar-nav-icon">{icon}</span>
                <span className="sidebar-nav-label">{label}</span>
            </button>
        )
    }

    return (
        <aside className="sidebar">
            <div className="sidebar-section">
                <div className="sidebar-section-title">MAIN</div>
                <div className="sidebar-nav-list">
                    <NavItem path="/sessions" icon="dashboard" label="Dashboard" exact />
                    {/* Live Interview and Reports are session-specific. Omitted from global sidebar unless we add state for them. */}
                </div>
            </div>

            <div className="sidebar-section">
                <div className="sidebar-section-title">WORKSPACE</div>
                <div className="sidebar-nav-list">
                    <NavItem path="/candidates" icon="people" label="Candidates" />
                    <NavItem path="/jobs" icon="work" label="Jobs" />
                    <NavItem path="/history" icon="history" label="History" />
                    <NavItem path="/settings" icon="settings" label="Settings" />
                    
                    {role === 'ADMIN' && (
                        <>
                            <NavItem path="/admin/users" icon="group" label="Users" />
                            <NavItem path="/admin/audit-logs" icon="list_alt" label="Audit Logs" />
                            <NavItem path="/admin/settings" icon="settings" label="Settings" />
                        </>
                    )}
                </div>
            </div>
        </aside>
    )
}
