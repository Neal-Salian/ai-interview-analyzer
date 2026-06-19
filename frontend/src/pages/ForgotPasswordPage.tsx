import { useState } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('')
    const [submitted, setSubmitted] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async () => {
        setError('')
        setLoading(true)
        try {
            await client.post('/auth/forgot-password', { email })
            setSubmitted(true)
        } catch {
            setError('Something went wrong. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
            <div style={{ background: 'var(--bg-surface)', border: '2px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '40px', width: '380px', boxShadow: 'var(--shadow)' }}>
                <h2 style={{ marginBottom: '8px', fontSize: '22px', fontFamily: 'var(--font-heading)', fontWeight: 700 }}>Forgot password</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', fontSize: '13px' }}>
                    Enter your email and we'll send a reset link if it's registered.
                </p>

                {submitted ? (
                    <div>
                        <p style={{ color: 'var(--success)', fontSize: '14px', marginBottom: '16px' }}>
                            If that email is registered, a reset link has been sent.
                        </p>
                        <Link to="/login" style={{ color: 'var(--accent)', fontSize: '13px' }}>Back to sign in</Link>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="jane@company.com"
                                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                                style={inputStyle}
                            />
                        </div>

                        {error && <p style={{ color: 'var(--danger)', fontSize: '13px' }}>{error}</p>}

                        <button onClick={handleSubmit} disabled={loading} style={btnStyle(loading)}>
                            {loading ? 'Sending...' : 'Send reset link'}
                        </button>

                        <p style={{ textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
                            <Link to="/login" style={{ color: 'var(--accent)' }}>Back to sign in</Link>
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}

const inputStyle: React.CSSProperties = {
    width: '100%', background: 'var(--bg-surface-high)', border: '1px solid var(--border)',
    borderRadius: 'var(--radius)', padding: '10px 14px', color: 'var(--text-primary)',
    fontSize: '14px', outline: 'none', fontFamily: 'var(--font-body)',
}

const btnStyle = (loading: boolean): React.CSSProperties => ({
    background: 'var(--accent)', color: '#000', border: 'none',
    borderRadius: 'var(--radius)', fontFamily: 'var(--font-heading)', fontWeight: 600,
    padding: '12px', fontSize: '14px', opacity: loading ? 0.7 : 1, marginTop: '8px',
    cursor: loading ? 'not-allowed' : 'pointer',
})