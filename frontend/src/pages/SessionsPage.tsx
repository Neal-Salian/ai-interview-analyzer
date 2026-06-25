import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import client from '../api/client';
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
    status: 'active' | 'completed' | 'scheduled' | 'processing' | 'cancelled' | 'no_show' | 'draft';
    metrics?: { sentiment: number; talkCandidate: number; talkInterviewer: number };
    tags?: string[];
    zoom_meeting_id?: string | null;
    zoom_join_url?: string | null;
    zoom_start_url?: string | null;
}

type FilterStatus = 'all' | 'scheduled' | 'active' | 'processing' | 'completed' | 'cancelled' | 'no_show';

export default function SessionsPage() {
    const [sessions, setSessions] = useState<EnhancedSession[]>([]);
    const [loading, setLoading] = useState(true);

    // UI states
    const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
    const [filterJob, setFilterJob] = useState<string>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedSession, setSelectedSession] = useState<EnhancedSession | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [jobs, setJobs] = useState<{ id: string, title: string }[]>([]);

    const navigate = useNavigate();
    const { role } = useAuth();
    const [adminStats, setAdminStats] = useState<AdminStats | null>(null);

    const fetchSessions = async () => {
        try {
            const [res] = await Promise.all([
                client.get('/sessions/today'),
                new Promise(resolve => setTimeout(resolve, 500))
            ]);
            const validSessions = res.data.filter((s: any) => s.status !== 'draft');
            setSessions(validSessions);
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

    const handleScheduleSession = async (sessionId: string, payload: { scheduled_at: string, interview_type?: string, notes?: string }) => {
        await client.patch(`/sessions/${sessionId}/schedule`, payload);
        await fetchSessions();
        if (selectedSession?.session_id === sessionId) setIsDrawerOpen(false);
    };

    const handleDeleteSession = async (sessionId: string) => {
        await client.delete(`/sessions/${sessionId}`);
        await fetchSessions();
        if (selectedSession?.session_id === sessionId) setIsDrawerOpen(false);
    };

    const handleAssignJob = async (sessionId: string, jobId: string) => {
        await client.patch(`/sessions/${sessionId}/job`, { job_id: jobId });

        // update selected session in state locally without closing drawer
        const updatedSessionRes = await client.get(`/sessions/${sessionId}`);
        setSelectedSession(updatedSessionRes.data);
        await fetchSessions();
    };

    const handleStartZoomMeeting = async (sessionId: string) => {
        try {
            const res = await client.get(`/sessions/${sessionId}/zoom`);
            const startUrl = res.data.zoom_start_url;
            if (startUrl) {
                window.open(startUrl, '_blank', 'noopener,noreferrer');
            } else {
                alert('This session does not have an associated Zoom meeting.');
            }
        } catch (err: any) {
            const detail = err?.response?.data?.detail || 'Failed to load Zoom meeting information.';
            alert(detail);
        }
    };

    const handleCopyJoinLink = async (sessionId: string) => {
        const session = sessions.find(s => s.session_id === sessionId);
        const joinUrl = session?.zoom_join_url || selectedSession?.zoom_join_url;
        if (joinUrl) {
            try {
                await navigator.clipboard.writeText(joinUrl);
                // Brief visual feedback would go here in a toast system
            } catch {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = joinUrl;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
        } else {
            alert('No Zoom join link available for this session.');
        }
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
                            onCreateSession={() => navigate('/candidates')}
                        />
                    ) : filteredSessions.length === 0 && sessions.length === 0 ? (
                        <EmptyState
                            hasActiveFilter={false}
                            hasSearchQuery={false}
                            onClearFilters={handleClearFilters}
                            onCreateSession={() => navigate('/candidates')}
                        />
                    ) : (
                        <div className="session-grid">
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
                                    onStartZoom={() => handleStartZoomMeeting(session.session_id)}
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
                onStart={() => { if (selectedSession) handleStartSession(selectedSession.session_id); }}
                onEnd={() => { if (selectedSession) handleEndSession(selectedSession.session_id); }}
                onJoin={() => { if (selectedSession) navigate(`/sessions/${selectedSession.session_id}/live`); }}
                onViewReport={() => { if (selectedSession) navigate(`/sessions/${selectedSession.session_id}/report`); }}
                onCancel={() => { if (selectedSession) handleCancelSession(selectedSession.session_id); }}
                onNoShow={() => { if (selectedSession) handleNoShowSession(selectedSession.session_id); }}
                onSchedule={(payload) => { if (selectedSession) handleScheduleSession(selectedSession.session_id, payload); }}
                onDelete={() => { if (selectedSession) handleDeleteSession(selectedSession.session_id); }}
                onAssignJob={(jobId) => { if (selectedSession) handleAssignJob(selectedSession.session_id, jobId); }}
                onStartZoom={() => { if (selectedSession) handleStartZoomMeeting(selectedSession.session_id); }}
                onCopyJoinLink={() => { if (selectedSession) handleCopyJoinLink(selectedSession.session_id); }}
                jobs={jobs}
            />
        </div>
    );
}
