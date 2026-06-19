import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import client from '../api/client';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import PageTransition from '../components/PageTransition';
import { SessionCardSkeleton, StatCardSkeleton } from '../components/Skeleton';
import { SessionCard } from '../components/Sessions/SessionCard';
import { SessionDetailsDrawer } from '../components/Sessions/SessionDetailsDrawer';
import { DashboardStats, type AdminStats } from '../components/Sessions/DashboardStats';
import { SearchBar } from '../components/Sessions/SearchBar';
import { EmptyState } from '../components/Sessions/EmptyState';
import './SessionsPage.css';

export interface EnhancedSession {
    session_id: string;
    candidate: string | null;
    job: string | null;
    job_id?: string | null;
    scheduled_at: string | null;
    status: 'active' | 'completed' | 'scheduled' | 'processing' | 'cancelled' | 'no_show';
    metrics?: { sentiment: number; talkCandidate: number; talkInterviewer: number };
    tags?: string[];
}

type FilterStatus = 'all' | 'scheduled' | 'active' | 'processing' | 'completed' | 'cancelled' | 'no_show';

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
    const [filterJob, setFilterJob] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedSession, setSelectedSession] = useState<EnhancedSession | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [jobs, setJobs] = useState<{ id: string, title: string }[]>([]);

    const navigate = useNavigate();
    const { theme } = useTheme();
    const { role } = useAuth();
    const [adminStats, setAdminStats] = useState<AdminStats | null>(null);

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

    const fetchAdminStats = async () => {
        try {
            const [usersRes, logsRes] = await Promise.all([
                client.get('/admin/users'),
                client.get('/admin/audit-logs').catch(() => ({ data: [] }))
            ]);
            const users = usersRes.data;
            setAdminStats({
                totalRecruiters: users.filter((u: any) => u.role === 'RECRUITER').length,
                activeUsers: users.filter((u: any) => u.is_active).length,
                disabledUsers: users.filter((u: any) => !u.is_active).length,
                auditLogs: logsRes.data.length
            });
        } catch (err) {
            console.error('Failed to fetch admin stats', err);
        }
    };

    const fetchJobs = async () => {
        try {
            const res = await client.get('/jobs');
            setJobs(res.data);
        } catch (err) {
            console.error('Failed to fetch jobs', err);
        }
    };

    useEffect(() => {
        fetchSessions();
        fetchJobs();
        if (role === 'ADMIN') {
            fetchAdminStats();
        }
    }, [role]);

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

    const handleCancelSession = async (sessionId: string) => {
        await client.patch(`/sessions/${sessionId}/cancel`);
        await fetchSessions();
        if (selectedSession?.session_id === sessionId) setIsDrawerOpen(false);
    };

    const handleNoShowSession = async (sessionId: string) => {
        await client.patch(`/sessions/${sessionId}/no_show`);
        await fetchSessions();
        if (selectedSession?.session_id === sessionId) setIsDrawerOpen(false);
    };

    // Combined filter + search logic
    const filteredSessions = useMemo(() => {
        let result = sessions;

        // Apply job filter
        if (filterJob !== 'all') {
            result = result.filter(s => s.job_id === filterJob);
        }

        // Apply status filter
        if (filterStatus !== 'all') {
            result = result.filter(s => s.status === filterStatus);
        }

        // Apply search filter
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase().trim();
            result = result.filter(s =>
                (s.candidate && s.candidate.toLowerCase().includes(query)) ||
                (s.job && s.job.toLowerCase().includes(query)) ||
                s.status.toLowerCase().includes(query)
            );
        }

        return result;
    }, [sessions, filterStatus, filterJob, searchQuery]);

    // Filter counts
    const filterCounts = useMemo(() => {
        let baseSessions = sessions;
        if (filterJob !== 'all') {
            baseSessions = baseSessions.filter(s => s.job_id === filterJob);
        }

        const searchFiltered = searchQuery.trim()
            ? baseSessions.filter(s => {
                const query = searchQuery.toLowerCase().trim();
                return (
                    (s.candidate && s.candidate.toLowerCase().includes(query)) ||
                    (s.job && s.job.toLowerCase().includes(query)) ||
                    s.status.toLowerCase().includes(query)
                );
            })
            : baseSessions;

        return {
            all: searchFiltered.length,
            scheduled: searchFiltered.filter(s => s.status === 'scheduled').length,
            active: searchFiltered.filter(s => s.status === 'active').length,
            processing: searchFiltered.filter(s => s.status === 'processing').length,
            completed: searchFiltered.filter(s => s.status === 'completed').length,
            cancelled: searchFiltered.filter(s => s.status === 'cancelled').length,
            no_show: searchFiltered.filter(s => s.status === 'no_show').length,
        };
    }, [sessions, filterJob, searchQuery]);

    const currentDate = new Date().toLocaleDateString('en-US', {
        weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
    });

    const handleClearFilters = () => {
        setFilterStatus('all');
        setFilterJob('all');
        setSearchQuery('');
    };

    const handleOpenCreateSession = () => {
        fetchCandidates();
        setShowNewSession(true);
    };

    const filters: { label: string; value: FilterStatus }[] = [
        { label: 'All', value: 'all' },
        { label: 'Scheduled', value: 'scheduled' },
        { label: 'Active', value: 'active' },
        { label: 'Processing', value: 'processing' },
        { label: 'Completed', value: 'completed' },
        { label: 'Cancelled', value: 'cancelled' },
        { label: 'No-Shows', value: 'no_show' },
    ];

    return (
        <div className="sessions-page">
            <Navbar />

            <PageTransition>
                <main className="sessions-main">

                    {/* Page Header */}
                    <div className="sessions-header">
                        <div>
                            <h1 className="sessions-header__title">
                                Today's Interviews
                            </h1>
                            <p className="sessions-header__date">
                                {currentDate}
                            </p>
                        </div>

                        <div className="sessions-header__actions">
                            <button
                                className="btn-icon"
                                onClick={fetchSessions}
                                aria-label="Refresh sessions"
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">refresh</span>
                            </button>
                        </div>
                    </div>

                    {/* Dashboard Statistics */}
                    {loading ? (
                        <div className="stats-row" aria-label="Loading statistics">
                            {[1, 2, 3, 4, 5].map((i) => (
                                <StatCardSkeleton key={i} />
                            ))}
                        </div>
                    ) : (
                        <DashboardStats sessions={sessions} role={role} adminStats={adminStats} />
                    )}

                    {/* Search & Filters Row */}
                    <div className="search-filters-row">
                        <SearchBar value={searchQuery} onChange={setSearchQuery} />
                        
                        <div className="job-filter">
                            <select 
                                className="job-filter-select"
                                value={filterJob}
                                onChange={e => setFilterJob(e.target.value)}
                                aria-label="Filter sessions by job"
                            >
                                <option value="all">All Jobs</option>
                                {jobs.length === 0 ? (
                                    <option disabled>No jobs available</option>
                                ) : (
                                    jobs.map(job => (
                                        <option key={job.id} value={job.id}>{job.title}</option>
                                    ))
                                )}
                            </select>
                        </div>

                        <div className="filter-pills" role="tablist" aria-label="Filter sessions by status">
                            {filters.map((f) => (
                                <button
                                    key={f.value}
                                    className={`filter-pill ${filterStatus === f.value ? 'filter-pill--active' : ''}`}
                                    onClick={() => setFilterStatus(f.value)}
                                    role="tab"
                                    aria-selected={filterStatus === f.value}
                                    aria-label={`${f.label}: ${filterCounts[f.value]} sessions`}
                                >
                                    {f.label}
                                    <span className="filter-pill__count">
                                        {filterCounts[f.value]}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Session Grid or Empty State */}
                    {loading ? (
                        <div className="session-grid">
                            {[1, 2, 3].map((i) => (
                                <SessionCardSkeleton key={i} />
                            ))}
                        </div>
                    ) : filteredSessions.length === 0 && sessions.length > 0 ? (
                        <EmptyState
                            hasActiveFilter={filterStatus !== 'all'}
                            hasSearchQuery={searchQuery.trim().length > 0}
                            onClearFilters={handleClearFilters}
                            onCreateSession={handleOpenCreateSession}
                        />
                    ) : filteredSessions.length === 0 && sessions.length === 0 ? (
                        <EmptyState
                            hasActiveFilter={false}
                            hasSearchQuery={false}
                            onClearFilters={handleClearFilters}
                            onCreateSession={handleOpenCreateSession}
                        />
                    ) : (
                        <div className="session-grid">
                            {/* Create New Session Card */}
                            <div
                                className="create-session-card"
                                onClick={handleOpenCreateSession}
                                role="button"
                                tabIndex={0}
                                aria-label="Create a new interview session"
                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleOpenCreateSession(); } }}
                            >
                                <div className="create-session-card__icon-wrap">
                                    <span className="material-symbols-outlined" style={{ color: 'var(--accent)', fontSize: '26px' }} aria-hidden="true">add</span>
                                </div>
                                <h3 className="create-session-card__title">Create New Session</h3>
                                <p className="create-session-card__desc">
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

                    {/* Future Extensions Slot */}
                    <section
                        id="dashboard-extensions"
                        className="dashboard-extensions"
                        aria-label="Future dashboard modules"
                    />

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
                onCancel={() => { if(selectedSession) handleCancelSession(selectedSession.session_id); }}
                onNoShow={() => { if(selectedSession) handleNoShowSession(selectedSession.session_id); }}
            />

            {showNewSession && (
                <div className="modal-backdrop" onClick={() => { setShowNewSession(false); setSelectedCandidate(''); setScheduledAt(''); }}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <h2 className="modal-title">
                            New Session
                        </h2>
                        <label className="modal-label" htmlFor="session-candidate-select">
                            Select Candidate
                        </label>
                        <select
                            id="session-candidate-select"
                            value={selectedCandidate}
                            onChange={e => setSelectedCandidate(e.target.value)}
                            className="modal-input"
                            aria-label="Select a candidate for the session"
                        >
                            <option value="">Choose a candidate...</option>
                            {candidates.map(c => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                        <label className="modal-label" htmlFor="session-schedule-input">
                            Schedule Date & Time
                        </label>
                        <input
                            id="session-schedule-input"
                            type="datetime-local"
                            value={scheduledAt}
                            onChange={e => setScheduledAt(e.target.value)}
                            className="modal-input"
                            style={{ colorScheme: theme }}
                            aria-label="Schedule date and time"
                        />
                        <div className="modal-actions">
                            <button
                                className="modal-btn--cancel"
                                onClick={() => {
                                    setShowNewSession(false);
                                    setSelectedCandidate('');
                                    setScheduledAt('');
                                }}
                            >
                                Cancel
                            </button>
                            <button
                                className="modal-btn--create"
                                onClick={handleNewSession}
                                disabled={!selectedCandidate || creating}
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
