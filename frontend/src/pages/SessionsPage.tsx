import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import client from '../api/client'
import type { Session } from '../types'

const STATUS_COLOR: Record<string, string> = {
    active: 'var(--success)',
    completed: 'var(--text-secondary)',
}

export default function SessionsPage() {
    const [sessions, setSessions] = useState<Session[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const navigate = useNavigate()

    useEffect(() => {
        client.get('/sessions/today')
            .then(res => setSessions(res.data))
            .catch(() => setError('Failed to load sessions'))
            .finally(() => setLoading(false))
    }, [])

    return (
        <div>
            <Navbar />
            <div style={{ padding: '32px 24px', maxWidth: '900px', margin: '0 auto' }}>
                <div style={{ marginBottom: '24px' }}>
                    <h1 style={{ fontSize: '24px', fontWeight: 600 }}>Today's Interviews</h1>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </p>
                </div>

                {loading && <p style={{ color: 'var(--text-secondary)' }}>Loading sessions...</p>}
                {error && <p style={{ color: 'var(--danger)' }}>{error}</p>}

                {!loading && !error && sessions.length === 0 && (
                    <div style={{
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)',
                        padding: '48px',
                        textAlign: 'center',
                        color: 'var(--text-secondary)',
                    }}>
                        No interviews scheduled for today.
                    </div>
                )}

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {sessions.map(session => (
                        <div
                            key={session.session_id}
                            onClick={() => navigate(`/sessions/${session.session_id}/live`)}
                            style={{
                                background: 'var(--bg-surface)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--radius)',
                                padding: '20px 24px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                transition: 'border-color 0.2s',
                            }}
                            onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                            onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                        >
                            <div>
                                <div style={{ fontWeight: 500, fontSize: '15px' }}>
                                    {session.candidate ?? 'Unknown Candidate'}
                                </div>
                                <div style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '4px' }}>
                                    {session.job ?? 'No job assigned'}
                                    {session.scheduled_at && (
                                        <> · {new Date(session.scheduled_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</>
                                    )}
                                </div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{
                                    width: '8px', height: '8px', borderRadius: '50%',
                                    background: STATUS_COLOR[session.status] ?? 'var(--text-secondary)',
                                    display: 'inline-block',
                                }} />
                                <span style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                                    {session.status}
                                </span>
                                {session.status === 'completed' && (
                                    <button
                                        onClick={e => { e.stopPropagation(); navigate(`/sessions/${session.session_id}/report`) }}
                                        style={{
                                            marginLeft: '8px',
                                            background: 'var(--accent-bg)',
                                            color: 'var(--accent)',
                                            border: '1px solid var(--accent)',
                                            borderRadius: 'var(--radius-sm)',
                                            padding: '4px 12px',
                                            fontSize: '12px',
                                        }}
                                    >
                                        View Report
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}