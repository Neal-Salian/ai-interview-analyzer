import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import client from '../api/client'

export default function ResetPasswordPage() {
    const [searchParams] = useSearchParams()
    const token = searchParams.get('token') || ''
    const [password, setPassword] = useState('')
    const [confirm, setConfirm] = useState('')
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const handleReset = async () => {
        setError('')
        if (!token) { setError('Invalid or missing reset token.'); return }
        if (password !== confirm) { setError('Passwords do not match'); return }
        if (password.length < 8) { setError('Password must be at least 8 characters'); return }
        setLoading(true)
        try {
            await client.post('/auth/reset-password', { token, new_password: password })
            setSuccess(true)
            setTimeout(() => navigate('/login'), 2000)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Reset failed. The link may have expired.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
            <div style={{ background: 'var(--bg-surface)', border: '2px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '40px', width: '380px', boxShadow: 'var(--shadow)' }}>
                <h2 style={{ marginBottom: '8px', fontSize: '22px', fontFamily: 'var(--font-heading)', fontWeight: 700 }}>Reset password</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', fontSize: '13px' }}>Choose a new password for your account.</p>

                {success ? (
                    <p style={{ color: 'var(--success)', fontSize: '14px' }}>Password updated. Redirecting to login...</p>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        {[
                            { label: 'New Password', value: password, setter: setPassword },
                            { label: 'Confirm Password', value: confirm, setter: setConfirm },
                        ].map(({ label, value, setter }) => (
                            <div key={label}>
                                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>{label}</label>
                                <input
                                    type="password"
                                    value={value}
                                    onChange={e => setter(e.target.value)}
                                    placeholder="••••••••"
                                    onKeyDown={e => e.key === 'Enter' && handleReset()}
                                    style={inputStyle}
                                />
                            </div>
                        ))}

                        {error && <p style={{ color: 'var(--danger)', fontSize: '13px' }}>{error}</p>}

                        <button onClick={handleReset} disabled={loading} style={btnStyle(loading)}>
                            {loading ? 'Updating...' : 'Update password'}
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