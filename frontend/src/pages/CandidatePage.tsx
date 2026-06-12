import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import client from '../api/client'
import PageTransition from '../components/PageTransition'

export default function CandidatePage() {
    const [name, setName] = useState('')
    const [email, setEmail] = useState('')
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle')
    const navigate = useNavigate()

    const handleSubmit = async () => {
        if (!name || !email) return
        try {
            await client.post('/candidates', { name, email })
            setStatus('success')
            setTimeout(() => navigate('/sessions'), 1500)
        } catch (err: any) {
            setStatus('error')
        }
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />
            <PageTransition>
            <div style={{ padding: '2rem', maxWidth: '480px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
                <button onClick={() => navigate('/sessions')} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500, padding: '0 0 16px 0' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>arrow_back</span>
                    Back to Sessions
                </button>
                <h1 style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em', marginBottom: '8px' }}>Register Candidate</h1>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '32px', fontSize: '13px' }}>
                    Add a candidate before their scheduled interview.
                </p>

                <div style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    boxShadow: 'var(--shadow-card)',
                    borderRadius: 'var(--radius-lg)',
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
                                backgroundImage: 'var(--accent-gradient)',
                                boxShadow: 'var(--accent-glow)',
                                color: '#fff',
                                border: 'none',
                                borderRadius: 'var(--radius)',
                                fontFamily: 'var(--font-heading)',
                                fontWeight: 600,
                                padding: '12px',
                                fontSize: '14px',
                                opacity: (!name || !email) ? 0.5 : 1,
                                marginTop: '8px',
                            }}
                        >
                            Register Candidate
                        </button>
                    </div>
                </div>
            </div>
            </PageTransition>
        </div>
    )
}

const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: '6px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    fontFamily: 'var(--font-heading)',
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
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