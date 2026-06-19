import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import client from '../api/client'

export default function RegisterPage() {
    const [fullName, setFullName] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirm, setConfirm] = useState('')
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const handleRegister = async () => {
        setError('')
        if (password !== confirm) { setError('Passwords do not match'); return }
        if (password.length < 8) { setError('Password must be at least 8 characters'); return }
        setLoading(true)
        try {
            await client.post('/auth/register', { full_name: fullName, email, password })
            setSuccess(true)
            setTimeout(() => navigate('/login'), 2000)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Registration failed. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
            <div style={{ background: 'var(--bg-surface)', border: '2px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '40px', width: '380px', boxShadow: 'var(--shadow)' }}>
                <h2 style={{ marginBottom: '8px', fontSize: '22px', fontFamily: 'var(--font-heading)', fontWeight: 700 }}>Create account</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', fontSize: '13px' }}>
                    Register as a recruiter to access the platform
                </p>

                {success ? (
                    <p style={{ color: 'var(--success)', fontSize: '14px' }}>Account created! Redirecting to login...</p>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        {[
                            { label: 'Full Name', value: fullName, setter: setFullName, type: 'text', placeholder: 'Jane Smith' },
                            { label: 'Email', value: email, setter: setEmail, type: 'email', placeholder: 'jane@company.com' },
                            { label: 'Password', value: password, setter: setPassword, type: 'password', placeholder: '••••••••' },
                            { label: 'Confirm Password', value: confirm, setter: setConfirm, type: 'password', placeholder: '••••••••' },
                        ].map(({ label, value, setter, type, placeholder }) => (
                            <div key={label}>
                                <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-secondary)' }}>{label}</label>
                                <input
                                    type={type}
                                    value={value}
                                    onChange={e => setter(e.target.value)}
                                    placeholder={placeholder}
                                    onKeyDown={e => e.key === 'Enter' && handleRegister()}
                                    style={inputStyle}
                                />
                            </div>
                        ))}

                        {error && <p style={{ color: 'var(--danger)', fontSize: '13px' }}>{error}</p>}

                        <button onClick={handleRegister} disabled={loading} style={btnStyle(loading)}>
                            {loading ? 'Creating account...' : 'Create account'}
                        </button>

                        <p style={{ textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
                            Already have an account?{' '}
                            <Link to="/login" style={{ color: 'var(--accent)' }}>Sign in</Link>
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