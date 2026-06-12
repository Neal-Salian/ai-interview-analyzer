import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import PageTransition from '../components/PageTransition'

export default function LoginPage() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [mousePos, setMousePos] = useState({ x: 30, y: 50 })

    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
        const rect = e.currentTarget.getBoundingClientRect()
        const x = ((e.clientX - rect.left) / rect.width) * 100
        const y = ((e.clientY - rect.top) / rect.height) * 100
        setMousePos({ x, y })
    }
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
        <PageTransition>
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
                    box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px var(--accent) !important;
                }
                .login-input:hover:not(:focus) {
                    border-color: var(--text-secondary);
                }
                .login-btn:active {
                    transform: scale(0.98);
                }
                @keyframes fadeUp {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .animate-fade-up {
                    animation: fadeUp 0.6s ease-out forwards;
                }
                @keyframes spin {
                    100% { transform: rotate(360deg); }
                }
                .spinner {
                    animation: spin 1s linear infinite;
                }
                @keyframes float1 {
                    0% { transform: translate(0, 0) scale(1); }
                    33% { transform: translate(5%, -5%) scale(1.1); }
                    66% { transform: translate(-2%, 4%) scale(0.9); }
                    100% { transform: translate(0, 0) scale(1); }
                }
                @keyframes float2 {
                    0% { transform: translate(0, 0) scale(1); }
                    33% { transform: translate(-5%, 2%) scale(1.2); }
                    66% { transform: translate(4%, -4%) scale(0.8); }
                    100% { transform: translate(0, 0) scale(1); }
                }
                @keyframes float3 {
                    0% { transform: translate(0, 0) scale(1); }
                    33% { transform: translate(3%, 5%) scale(1.1); }
                    66% { transform: translate(-4%, -3%) scale(1.05); }
                    100% { transform: translate(0, 0) scale(1); }
                }
            `}</style>

            {/* Left Panel */}
            <div
                onMouseMove={handleMouseMove}
                style={{
                    flex: '0 0 55%',
                    position: 'relative',
                    backgroundColor: 'var(--bg)',
                    backgroundImage: `
                        linear-gradient(var(--grid-color) 1px, transparent 1px),
                        linear-gradient(90deg, var(--grid-color) 1px, transparent 1px)
                    `,
                    backgroundSize: '48px 48px',
                    overflow: 'hidden'
                }}
            >
                {/* Radial Glow */}
                <div style={{
                    position: 'absolute',
                    top: `${mousePos.y}%`,
                    left: `${mousePos.x}%`,
                    transform: 'translate(-50%, -50%)',
                    width: '800px',
                    height: '800px',
                    background: 'radial-gradient(circle, var(--glow-color) 0%, transparent 60%)',
                    borderRadius: '50%',
                    pointerEvents: 'none',
                    transition: 'top 0.4s ease-out, left 0.4s ease-out, var(--theme-transition)',
                }} />

                {/* Brand Logo */}
                <div style={{
                    position: 'absolute',
                    top: '40px',
                    left: '40px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    zIndex: 10
                }}>
                    <div style={{
                        width: '28px',
                        height: '28px',
                        background: 'var(--accent)',
                        backgroundImage: 'var(--accent-gradient)',
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: 'var(--accent-glow)'
                    }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
                        </svg>
                    </div>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '15px', fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em' }}>
                        AI Interview Analyser
                    </span>
                    <span style={{
                        border: '1px solid var(--border)',
                        background: 'var(--bg-surface-high)',
                        color: 'var(--text-secondary)',
                        fontSize: '10px',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: '12px',
                        letterSpacing: '0.02em'
                    }}>
                        Enterprise
                    </span>
                </div>

                {/* Slow Moving Gradient Mesh */}
                <div style={{
                    position: 'absolute',
                    top: '10%',
                    left: '10%',
                    width: '60vw',
                    height: '60vw',
                    background: 'radial-gradient(circle, rgba(91,140,255,0.06) 0%, transparent 60%)',
                    borderRadius: '50%',
                    animation: 'float1 20s ease-in-out infinite',
                    pointerEvents: 'none',
                    zIndex: 1
                }} />
                <div style={{
                    position: 'absolute',
                    top: '30%',
                    right: '-10%',
                    width: '50vw',
                    height: '50vw',
                    background: 'radial-gradient(circle, rgba(168,85,247,0.05) 0%, transparent 60%)',
                    borderRadius: '50%',
                    animation: 'float2 25s ease-in-out infinite',
                    pointerEvents: 'none',
                    zIndex: 1
                }} />
                <div style={{
                    position: 'absolute',
                    bottom: '-10%',
                    left: '10%',
                    width: '55vw',
                    height: '55vw',
                    background: 'radial-gradient(circle, rgba(56,189,248,0.05) 0%, transparent 60%)',
                    borderRadius: '50%',
                    animation: 'float3 22s ease-in-out infinite',
                    pointerEvents: 'none',
                    zIndex: 1
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
                <div className="animate-fade-up" style={{ width: '380px' }}>
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
                            <div style={{
                                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                borderRadius: '8px',
                                padding: '12px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="12" cy="12" r="10"></circle>
                                    <line x1="12" y1="8" x2="12" y2="12"></line>
                                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                </svg>
                                <span style={{ color: 'var(--danger)', fontSize: '13px', fontWeight: 500 }}>{error}</span>
                            </div>
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
                                transition: 'transform 0.1s, opacity 0.2s, var(--theme-transition)',
                            }}
                            className="login-btn"
                        >
                            {loading ? (
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                                    <svg className="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
                                    </svg>
                                    Signing in...
                                </div>
                            ) : 'Sign in'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
        </PageTransition>
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
    transition: 'border-color 0.2s, box-shadow 0.2s, background-color var(--theme-transition-duration) var(--theme-transition-easing), color var(--theme-transition-duration) var(--theme-transition-easing)',
}