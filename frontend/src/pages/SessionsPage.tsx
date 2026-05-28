import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';

// Extended session type for the new UI data requirements
interface EnhancedSession {
    session_id: string;
    candidate: string;
    job: string;
    scheduled_at: string;
    status: 'active' | 'completed';
    metrics?: { sentiment: number; talkCandidate: number; talkInterviewer: number };
    tags?: string[];
}

export default function SessionsPage() {
    const [sessions, setSessions] = useState<EnhancedSession[]>([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        // Mock data perfectly matching the screenshot
        const MOCK_SESSIONS: EnhancedSession[] = [
            {
                session_id: 'sess_1',
                candidate: 'Elena Rostova',
                job: 'Senior Machine Learning Engineer',
                scheduled_at: '10:00 AM - 11:30 AM',
                status: 'active',
                metrics: { sentiment: 75, talkCandidate: 42, talkInterviewer: 58 }
            },
            {
                session_id: 'sess_2',
                candidate: 'Priya Sharma',
                job: 'Product Manager, Platform',
                scheduled_at: '08:30 AM - 09:15 AM',
                status: 'completed',
                tags: ['Confident', 'Analytical']
            }
        ];

        setTimeout(() => {
            setSessions(MOCK_SESSIONS);
            setLoading(false);
        }, 400);
    }, []);

    const currentDate = new Date().toLocaleDateString('en-US', {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
    });

    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />

            <main style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>

                {/* Page Header */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-end',
                    borderBottom: '1px solid var(--border)',
                    paddingBottom: '1.5rem',
                    marginBottom: '2rem'
                }}>
                    <div>
                        <h1 style={{ fontSize: '28px', fontWeight: 600, margin: '0 0 0.5rem 0', letterSpacing: '-0.02em' }}>
                            Today's Interviews
                        </h1>
                        <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '14px' }}>
                            {currentDate}
                        </p>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <button style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            width: '40px', height: '40px', borderRadius: 'var(--radius-sm, 6px)',
                            border: '1px solid var(--border)', backgroundColor: 'transparent',
                            color: 'var(--text-secondary)', cursor: 'pointer'
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>refresh</span>
                        </button>

                        <button style={{
                            display: 'flex', alignItems: 'center', gap: '0.5rem',
                            backgroundColor: 'var(--accent)', color: '#ffffff',
                            border: 'none', padding: '0 1rem', height: '40px',
                            borderRadius: 'var(--radius-sm, 6px)', fontWeight: 500,
                            fontSize: '13px', cursor: 'pointer'
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>add</span>
                            New Session
                        </button>
                    </div>
                </div>

                {loading ? (
                    <p style={{ color: 'var(--text-secondary)' }}>Loading schedule...</p>
                ) : (
                    /* Grid Layout */
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
                        gap: '1.5rem'
                    }}>

                        {/* Render Active/Completed Sessions */}
                        {sessions.map((session) => (
                            <div key={session.session_id} style={{
                                backgroundColor: 'var(--bg-surface)',
                                borderRadius: '10px',
                                border: '1px solid var(--border)',
                                padding: '1.5rem',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '1.25rem',
                                opacity: session.status === 'completed' ? 0.8 : 1,
                                transition: 'opacity 0.2s'
                            }}
                                onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                                onMouseLeave={e => e.currentTarget.style.opacity = session.status === 'completed' ? '0.8' : '1'}
                            >
                                {/* Card Header */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <div>
                                        <h2 style={{ fontSize: '18px', fontWeight: 600, margin: '0 0 0.5rem 0' }}>{session.candidate}</h2>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '6px' }}>
                                            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>work</span>
                                            {session.job}
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '13px' }}>
                                            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>schedule</span>
                                            {session.scheduled_at}
                                        </div>
                                    </div>

                                    {/* Status Badge */}
                                    {session.status === 'active' ? (
                                        <div style={{
                                            display: 'flex', alignItems: 'center', gap: '6px',
                                            backgroundColor: 'rgba(255, 184, 106, 0.1)', // Warning/Tertiary tint
                                            border: '1px solid rgba(255, 184, 106, 0.3)',
                                            padding: '4px 12px', borderRadius: '999px'
                                        }}>
                                            <div style={{ width: '6px', height: '6px', backgroundColor: 'var(--warning)', borderRadius: '50%' }} />
                                            <span style={{ color: 'var(--warning)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em' }}>LIVE</span>
                                        </div>
                                    ) : (
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
                                            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>check_circle</span>
                                            <span style={{ fontSize: '12px', fontWeight: 500 }}>Completed</span>
                                        </div>
                                    )}
                                </div>

                                {/* Active Session Metrics (Bento Box) */}
                                {session.status === 'active' && session.metrics && (
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: 'auto' }}>
                                        <div style={{ backgroundColor: 'var(--bg)', borderRadius: '6px', padding: '10px' }}>
                                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '12px' }}>Sentiment Focus</div>
                                            <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                                                <div style={{ width: `${session.metrics.sentiment}%`, height: '100%', backgroundColor: 'var(--accent)' }} />
                                            </div>
                                        </div>
                                        <div style={{ backgroundColor: 'var(--bg)', borderRadius: '6px', padding: '10px', display: 'flex', flexDirection: 'column' }}>
                                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 'auto' }}>Talk Ratio</div>
                                            <div style={{ fontSize: '14px', fontWeight: 600 }}>
                                                {session.metrics.talkCandidate}% <span style={{ color: 'var(--text-secondary)', fontWeight: 400, fontSize: '12px' }}>/ {session.metrics.talkInterviewer}%</span>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Action Buttons */}
                                <div style={{ marginTop: 'auto', paddingTop: '1.25rem', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    {session.status === 'active' ? (
                                        <button
                                            onClick={() => navigate(`/sessions/${session.session_id}/live`)}
                                            style={{
                                                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
                                                backgroundColor: 'var(--accent)', color: '#fff', border: 'none', padding: '0.75rem',
                                                borderRadius: '6px', fontWeight: 500, cursor: 'pointer', fontSize: '13px'
                                            }}
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>login</span>
                                            Join Session
                                        </button>
                                    ) : (
                                        <>
                                            <div style={{ display: 'flex', gap: '6px' }}>
                                                {session.tags?.map((tag, idx) => (
                                                    <span key={idx} style={{
                                                        backgroundColor: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)',
                                                        padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 600
                                                    }}>
                                                        {tag}
                                                    </span>
                                                ))}
                                            </div>
                                            <button
                                                onClick={() => navigate(`/sessions/${session.session_id}/report`)}
                                                style={{
                                                    display: 'flex', alignItems: 'center', gap: '0.5rem',
                                                    backgroundColor: 'transparent', color: 'var(--text-secondary)',
                                                    border: '1px solid var(--border)', padding: '0.5rem 1rem',
                                                    borderRadius: '6px', fontWeight: 500, cursor: 'pointer', fontSize: '12px'
                                                }}
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>assessment</span>
                                                View Report
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}

                        {/* Dashed Schedule Clear Card */}
                        <div style={{
                            backgroundColor: 'transparent',
                            borderRadius: '10px',
                            border: '1px dashed var(--border)',
                            padding: '2rem',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            textAlign: 'center',
                            minHeight: '260px'
                        }}>
                            <div style={{
                                width: '48px', height: '48px', backgroundColor: 'var(--bg-surface)',
                                borderRadius: '8px', display: 'flex', alignItems: 'center',
                                justifyContent: 'center', marginBottom: '1rem', border: '1px solid var(--border)'
                            }}>
                                <span className="material-symbols-outlined" style={{ color: 'var(--text-secondary)', fontSize: '24px' }}>event_available</span>
                            </div>
                            <h3 style={{ fontSize: '16px', fontWeight: 500, margin: '0 0 6px 0', color: 'var(--text-primary)' }}>Schedule Clear</h3>
                            <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '13px', maxWidth: '200px', lineHeight: '1.5' }}>
                                No further interviews scheduled for this afternoon.
                            </p>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}