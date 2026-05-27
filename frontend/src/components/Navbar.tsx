import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
    const { logout } = useAuth()
    const navigate = useNavigate()

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    return (
        <nav style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            height: '56px',
            background: 'var(--bg-surface)',
            borderBottom: '1px solid var(--border)',
            position: 'sticky',
            top: 0,
            zIndex: 100,
        }}>
            <span
                onClick={() => navigate('/sessions')}
                style={{ fontWeight: 600, fontSize: '15px', color: 'var(--accent)', cursor: 'pointer' }}
            >
                ⚡ Interview Analyzer
            </span>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <button
                    onClick={() => navigate('/candidates/new')}
                    style={{
                        background: 'var(--accent-bg)',
                        color: 'var(--accent)',
                        border: '1px solid var(--accent)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '6px 14px',
                        fontSize: '13px',
                    }}
                >
                    + New Candidate
                </button>
                <button
                    onClick={handleLogout}
                    style={{
                        background: 'transparent',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '6px 14px',
                        fontSize: '13px',
                    }}
                >
                    Logout
                </button>
            </div>
        </nav>
    )
}