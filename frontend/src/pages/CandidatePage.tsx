import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'

export default function CandidatePage() {
    const [name, setName] = useState('')
    const [email, setEmail] = useState('')
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle')
    const navigate = useNavigate()

    const handleSubmit = async () => {
        // Real endpoint not built yet — mock success
        // Replace with: await client.post('/candidates', { name, email })
        if (!name || !email) return
        setStatus('success')
        setTimeout(() => navigate('/sessions'), 1500)
    }

    return (
        <div>
            <Navbar />
            <div style={{ padding: '40px 24px', maxWidth: '480px', margin: '0 auto' }}>
                <h1 style={{ fontSize: '22px', fontWeight: 600, marginBottom: '8px' }}>Register Candidate</h1>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', fontSize: '13px' }}>
                    Add a candidate before their scheduled interview.
                </p>

                <div style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    padding: '32px',
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div>
                            <label style={labelStyle}>Full Name</label>
                            <input
                                value={name}
                                onChange={e => setName(e.target.value)}
                                placeholder="Priya Sharma"
                                style={inputStyle}
                            />
                        </div>
                        <div>
                            <label style={labelStyle}>Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="priya@example.com"
                                style={inputStyle}
                            />
                        </div>

                        {status === 'success' && (
                            <p style={{ color: 'var(--success)', fontSize: '13px' }}>
                                ✓ Candidate registered — redirecting...
                            </p>
                        )}
                        {status === 'error' && (
                            <p style={{ color: 'var(--danger)', fontSize: '13px' }}>
                                Failed to register. Please try again.
                            </p>
                        )}

                        <button
                            onClick={handleSubmit}
                            disabled={!name || !email}
                            style={{
                                background: 'var(--accent)',
                                color: '#fff',
                                border: 'none',
                                borderRadius: 'var(--radius-sm)',
                                padding: '12px',
                                fontSize: '14px',
                                fontWeight: 500,
                                opacity: (!name || !email) ? 0.5 : 1,
                                marginTop: '8px',
                            }}
                        >
                            Register Candidate
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: '6px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
}

const inputStyle: React.CSSProperties = {
    width: '100%',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    padding: '10px 14px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
}