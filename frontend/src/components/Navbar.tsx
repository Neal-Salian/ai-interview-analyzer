import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

export default function Navbar() {
    const { logout } = useAuth()
    const { theme, toggleTheme } = useTheme()
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
            background: 'var(--bg)',
            borderBottom: '2px solid var(--border)',
            position: 'sticky',
            top: 0,
            zIndex: 100,
        }}>
            <span
                onClick={() => navigate('/sessions')}
                style={{ fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)', fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em', cursor: 'pointer' }}
            >
                Interview Analyzer
            </span>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <button
                    onClick={() => navigate('/history')}
                    style={{
                        background: 'transparent',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)',
                        padding: '6px 14px',
                        fontSize: '13px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={e => {
                        e.currentTarget.style.borderColor = 'var(--accent)';
                        e.currentTarget.style.color = 'var(--text-primary)';
                    }}
                    onMouseLeave={e => {
                        e.currentTarget.style.borderColor = 'var(--border)';
                        e.currentTarget.style.color = 'var(--text-secondary)';
                    }}
                    aria-label="Interview History"
                >
                    <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>history</span>
                    History
                </button>
                <button
                    onClick={() => navigate('/candidates/new')}
                    style={{
                        background: 'var(--accent)',
                        backgroundImage: 'var(--accent-gradient)',
                        boxShadow: 'var(--accent-glow)',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: 'var(--radius)',
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
                        color: 'var(--red)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)',
                        padding: '6px 14px',
                        fontSize: '13px',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--red)')}
                    onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                >
                    Logout
                </button>
                <button
                    onClick={toggleTheme}
                    style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '8px',
                        borderRadius: '4px'
                    }}
                    aria-label="Toggle theme"
                >
                    <span className="material-symbols-outlined">
                        {theme === 'dark' ? 'light_mode' : 'dark_mode'}
                    </span>
                </button>
            </div>
        </nav>
    )
}