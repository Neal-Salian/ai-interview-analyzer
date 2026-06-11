import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'


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
            const params = new URLSearchParams()
            params.append('username', email)
            params.append('password', password)
            const res = await client.post('/auth/login', params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            })
            login(res.data.access_token)
            navigate('/sessions')
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Login failed. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            background: 'var(--bg)',
            fontFamily: 'var(--font-body)',
        }}>
            <style>{`
                .login-input:focus {
                    border-color: var(--accent) !important;
                    outline: none !important;
                    box-shadow: 0 0 0 1px var(--accent) !important;
                }
            `}</style>

            {/* Left Panel */}
            <div style={{
                flex: '0 0 55%',
                position: 'relative',
                backgroundColor: 'var(--bg)',
                backgroundImage: `
                    linear-gradient(var(--grid-color) 1px, transparent 1px),
                    linear-gradient(90deg, var(--grid-color) 1px, transparent 1px)
                `,
                backgroundSize: '48px 48px',
                overflow: 'hidden'
            }}>
                {/* Radial Glow */}
                <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '10%',
                    transform: 'translate(-50%, -50%)',
                    width: '800px',
                    height: '800px',
                    background: 'radial-gradient(circle, var(--glow-color) 0%, transparent 60%)',
                    borderRadius: '50%',
                    pointerEvents: 'none',
                }} />
            </div>

            {/* Right Panel */}
            <div style={{
                flex: '1',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-start',
                paddingLeft: '10%',
                backgroundColor: 'var(--bg-surface)'
            }}>
                <div style={{ width: '380px' }}>
                    <h2 style={{ marginBottom: '8px', fontSize: '26px', fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em', fontWeight: 700, color: 'var(--text-primary)' }}>Welcome back</h2>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '36px', fontSize: '14px' }}>
                        Sign in to continue
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Email Address
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="admin@demo.com"
                                style={inputStyle}
                                className="login-input"
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', marginBottom: '8px', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="••••••••"
                                onKeyDown={e => e.key === 'Enter' && handleLogin()}
                                style={inputStyle}
                                className="login-input"
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
                                backgroundImage: 'var(--accent-gradient)',
                                boxShadow: 'var(--accent-glow)',
                                color: '#ffffff',
                                border: 'none',
                                borderRadius: '14px',
                                fontFamily: 'var(--font-heading)',
                                fontWeight: 600,
                                padding: '14px',
                                fontSize: '15px',
                                opacity: loading ? 0.7 : 1,
                                marginTop: '12px',
                                cursor: 'pointer',
                                transition: 'opacity 0.2s',
                            }}
                        >
                            {loading ? 'Signing in...' : 'Sign in'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'var(--bg-surface-high)',
    border: '1px solid var(--border)',
    borderRadius: '14px',
    padding: '14px 16px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
    fontFamily: 'var(--font-body)',
    transition: 'border-color 0.2s, box-shadow 0.2s',
}