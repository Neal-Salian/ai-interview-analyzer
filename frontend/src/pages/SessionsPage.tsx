import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import client from '../api/client';
import { useTheme } from '../context/ThemeContext';
import PageTransition from '../components/PageTransition';
import { SessionCardSkeleton } from '../components/Skeleton';
import { SessionCard } from '../components/Sessions/SessionCard';
import { SessionDetailsDrawer } from '../components/Sessions/SessionDetailsDrawer';

export interface EnhancedSession {
    session_id: string;
    candidate: string | null;
    job: string | null;
    scheduled_at: string | null;
    status: 'active' | 'completed' | 'scheduled' | 'processing';
    metrics?: { sentiment: number; talkCandidate: number; talkInterviewer: number };
    tags?: string[];
}

type FilterStatus = 'all' | 'scheduled' | 'active' | 'processing' | 'completed';

export default function SessionsPage() {
    const [showNewSession, setShowNewSession] = useState(false);
    const [candidates, setCandidates] = useState<{ id: string, name: string }[]>([]);
    const [selectedCandidate, setSelectedCandidate] = useState('');
    const [creating, setCreating] = useState(false);
    const [sessions, setSessions] = useState<EnhancedSession[]>([]);
    const [scheduledAt, setScheduledAt] = useState('');
    const [loading, setLoading] = useState(true);
    
    // UI states
    const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
    const [selectedSession, setSelectedSession] = useState<EnhancedSession | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    const navigate = useNavigate();
    const { theme } = useTheme();

    const fetchSessions = async () => {
        try {
            const [res] = await Promise.all([
                client.get('/sessions/today'),
                new Promise(resolve => setTimeout(resolve, 500))
            ]);
            setSessions(res.data);
        } catch (err) {
            console.error('Failed to fetch sessions', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();
    }, []);

    const fetchCandidates = async () => {
        try {
            const res = await client.get('/candidates');
            setCandidates(res.data);
        } catch (err) {
            console.error('Failed to fetch candidates', err);
        }
    };

    const handleNewSession = async () => {
        if (!selectedCandidate) return;
        setCreating(true);
        try {
            await client.post('/sessions', {
                candidate_id: selectedCandidate,
                scheduled_at: scheduledAt || new Date().toISOString()
            });
            setShowNewSession(false);
            setSelectedCandidate('');
            setScheduledAt('');
            await fetchSessions();
        } catch (err) {
            console.error('Failed to create session', err);
        } finally {
            setCreating(false);
        }
    };

    const handleStartSession = async (sessionId: string) => {
        await client.patch(`/sessions/${sessionId}/start`);
        await fetchSessions();
        if (selectedSession?.session_id === sessionId) setIsDrawerOpen(false);
    };

    const handleEndSession = async (sessionId: string) => {
        await client.patch(`/sessions/${sessionId}/end`);
        await fetchSessions();
        if (selectedSession?.session_id === sessionId) setIsDrawerOpen(false);
    };

    const filteredSessions = sessions.filter(s => filterStatus === 'all' || s.status === filterStatus);

    const currentDate = new Date().toLocaleDateString('en-US', {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
    });

    const FilterPill = ({ label, value }: { label: string, value: FilterStatus }) => (
        <button
            onClick={() => setFilterStatus(value)}
            style={{
                background: filterStatus === value ? 'var(--accent)' : 'transparent',
                color: filterStatus === value ? '#fff' : 'var(--text-secondary)',
                border: `1px solid ${filterStatus === value ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: '999px',
                padding: '6px 16px',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
            }}
        >
            {label}
        </button>
    );

    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />

            <PageTransition>
                <main style={{ padding: '2rem', maxWidth: '1600px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>

                    {/* Page Header */}
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-end',
                        marginBottom: '1.5rem'
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
                            <button 
                                onClick={fetchSessions}
                                style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    width: '40px', height: '40px', borderRadius: 'var(--radius-sm, 6px)',
                                    border: '1px solid var(--border)', backgroundColor: 'transparent',
                                    color: 'var(--text-secondary)', cursor: 'pointer'
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>refresh</span>
                            </button>
                        </div>
                    </div>

                    {/* Filters */}
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '2rem', flexWrap: 'wrap' }}>
                        <FilterPill label="All" value="all" />
                        <FilterPill label="Scheduled" value="scheduled" />
                        <FilterPill label="Active" value="active" />
                        <FilterPill label="Processing" value="processing" />
                        <FilterPill label="Completed" value="completed" />
                    </div>

                    {loading ? (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
                            gap: '1.5rem'
                        }}>
                            {[1, 2, 3].map((i) => (
                                <SessionCardSkeleton key={i} />
                            ))}
                        </div>
                    ) : (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
                            gap: '1.5rem'
                        }}>
                            {/* Create New Session Card */}
                            <div 
                                onClick={() => { fetchCandidates(); setShowNewSession(true); }}
                                style={{
                                    backgroundColor: 'transparent',
                                    borderRadius: '12px',
                                    border: '1px dashed var(--border)',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    textAlign: 'center',
                                    minHeight: '220px',
                                    maxHeight: '280px',
                                    cursor: 'pointer',
                                    transition: 'background-color 0.2s',
                                    padding: '1.5rem'
                                }}
                                onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bg-surface)'}
                                onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                            >
                                <div style={{
                                    width: '48px', height: '48px', backgroundColor: 'var(--bg-surface-high)',
                                    borderRadius: '50%', display: 'flex', alignItems: 'center',
                                    justifyContent: 'center', marginBottom: '1rem', border: '1px solid var(--border)'
                                }}>
                                    <span className="material-symbols-outlined" style={{ color: 'var(--accent)', fontSize: '24px' }}>add</span>
                                </div>
                                <h3 style={{ fontSize: '16px', fontWeight: 500, margin: '0 0 6px 0', color: 'var(--text-primary)' }}>Create New Session</h3>
                                <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '13px', maxWidth: '200px', lineHeight: '1.5' }}>
                                    Schedule a new interview for a candidate.
                                </p>
                            </div>

                            {/* Session Cards */}
                            {filteredSessions.map((session) => (
                                <SessionCard 
                                    key={session.session_id}
                                    session={session}
                                    onClick={() => { setSelectedSession(session); setIsDrawerOpen(true); }}
                                    onStart={() => handleStartSession(session.session_id)}
                                    onEnd={() => handleEndSession(session.session_id)}
                                    onJoin={() => navigate(`/sessions/${session.session_id}/live`)}
                                    onViewReport={() => navigate(`/sessions/${session.session_id}/report`)}
                                />
                            ))}
                        </div>
                    )}
                </main>
            </PageTransition>

            <SessionDetailsDrawer 
                session={selectedSession}
                isOpen={isDrawerOpen}
                onClose={() => { setIsDrawerOpen(false); setTimeout(() => setSelectedSession(null), 300); }}
                onStart={() => { if(selectedSession) handleStartSession(selectedSession.session_id); }}
                onEnd={() => { if(selectedSession) handleEndSession(selectedSession.session_id); }}
                onJoin={() => { if(selectedSession) navigate(`/sessions/${selectedSession.session_id}/live`); }}
                onViewReport={() => { if(selectedSession) navigate(`/sessions/${selectedSession.session_id}/report`); }}
            />

            {showNewSession && (
                <div style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: 2000
                }}>
                    <div style={{
                        background: 'var(--bg-surface)', border: '1px solid var(--border)',
                        borderRadius: '10px', padding: '32px', width: '400px'
                    }}>
                        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '24px' }}>
                            New Session
                        </h2>
                        <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
                            Select Candidate
                        </label>
                        <select
                            value={selectedCandidate}
                            onChange={e => setSelectedCandidate(e.target.value)}
                            style={{
                                width: '100%', background: 'var(--bg)',
                                border: '1px solid var(--border)', borderRadius: '6px',
                                padding: '10px', color: 'var(--text-primary)',
                                fontSize: '14px', marginBottom: '24px'
                            }}
                        >
                            <option value="">Choose a candidate...</option>
                            {candidates.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                        <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
                            Schedule Date & Time
                        </label>
                        <input
                            type="datetime-local"
                            value={scheduledAt}
                            onChange={e => setScheduledAt(e.target.value)}
                            style={{
                                width: '100%',
                                background: 'var(--bg)',
                                border: '1px solid var(--border)',
                                borderRadius: '6px',
                                padding: '10px',
                                color: 'var(--text-primary)',
                                fontSize: '14px',
                                marginBottom: '24px',
                                colorScheme: theme
                            }}
                        />
                        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => {
                                    setShowNewSession(false);
                                    setSelectedCandidate('');
                                    setScheduledAt('');
                                }}
                                style={{
                                    background: 'var(--bg)', border: '1px solid var(--border)',
                                    borderRadius: '6px', padding: '8px 16px',
                                    color: 'var(--text-secondary)', cursor: 'pointer'
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleNewSession}
                                disabled={!selectedCandidate || creating}
                                style={{
                                    background: 'var(--accent)', backgroundImage: 'var(--accent-gradient)', boxShadow: 'var(--accent-glow)', border: 'none',
                                    borderRadius: '6px', padding: '8px 16px',
                                    color: '#fff', cursor: 'pointer', fontWeight: 600,
                                    opacity: !selectedCandidate || creating ? 0.5 : 1
                                }}
                            >
                                {creating ? 'Creating...' : 'Create Session'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
