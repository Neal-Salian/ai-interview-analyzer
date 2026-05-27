import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const { login } = useAuth()
    const navigate = useNavigate()

    const handleLogin = async () => {
        setError('')
        setLoading(true)
        try {
            // Auth route not built yet — mock token for development
            // Replace with: const res = await client.post('/auth/login', { email, password })
            if (email === 'admin@demo.com' && password === 'password') {
                login('mock-jwt-token-dev')
                navigate('/sessions')
            } else {
                setError('Invalid credentials. Use admin@demo.com / password')
            }
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--bg)',
        }}>
            <div style={{
                background: 'var(--bg-surface)',
                border: '2px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '40px',
                width: '380px',
                boxShadow: 'var(--shadow)',
            }}>
                <h2 style={{ marginBottom: '8px', fontSize: '22px', fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em', fontWeight: 700, }}>Welcome back</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', fontSize: '13px' }}>
                    Sign in to access the recruiter dashboard
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                            Email
                        </label>
                        <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            placeholder="admin@demo.com"
                            style={inputStyle}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                            Password
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="••••••••"
                            onKeyDown={e => e.key === 'Enter' && handleLogin()}
                            style={inputStyle}
                        />
                    </div>

                    {error && (
                        <p style={{ color: 'var(--danger)', fontSize: '13px' }}>{error}</p>
                    )}

                    <button
                        onClick={handleLogin}
                        disabled={loading}
                        style={{
                            background: 'var(--accent)',
                            color: '#000',
                            border: 'none',
                            borderRadius: 'var(--radius)',
                            fontFamily: 'var(--font-heading)',
                            fontWeight: 600,
                            padding: '12px',
                            fontSize: '14px',
                            opacity: loading ? 0.7 : 1,
                            marginTop: '8px',
                        }}
                    >
                        {loading ? 'Signing in...' : 'Sign in'}
                    </button>
                </div>
            </div>
        </div>
    )
}

const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'var(--bg-surface-high)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: '10px 14px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
    fontFamily: 'var(--font-body)',
}