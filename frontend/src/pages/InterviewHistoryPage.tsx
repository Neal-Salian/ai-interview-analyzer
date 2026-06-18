import { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import client from '../api/client';
import PageTransition from '../components/PageTransition';
import { SearchBar } from '../components/Sessions/SearchBar';
import { StatusBadge } from '../components/Sessions/StatusBadge';
import { EmptyState } from '../components/Sessions/EmptyState';
import { AvatarInitials } from '../components/Sessions/AvatarInitials';
import './SessionsPage.css';
import './InterviewHistoryPage.css';

/* ── Types ────────────────────────────────────────────────────────── */

interface HistoryItem {
    session_id: string;
    candidate_name: string;
    job_title: string;
    interview_date: string | null;
    status: 'completed' | 'processing';
    overall_score: number | null;
    recommendation: string | null;
    has_transcript: boolean;
    has_evaluation: boolean;
}

interface HistoryResponse {
    total: number;
    page: number;
    page_size: number;
    items: HistoryItem[];
}

interface JobOption {
    id: string;
    title: string;
}

type FilterStatus = 'all' | 'completed' | 'processing';

/* ── Helpers ──────────────────────────────────────────────────────── */

function getScoreClass(score: number | null): string {
    if (score === null) return 'score-badge--none';
    if (score >= 70) return 'score-badge--high';
    if (score >= 45) return 'score-badge--medium';
    return 'score-badge--low';
}

function getRecClass(rec: string | null): string {
    if (!rec) return 'rec-badge--pending';
    const key = rec.toLowerCase().replace(/\s+/g, '-');
    return `rec-badge--${key}`;
}

function formatDate(iso: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
    }) + ', ' + d.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit',
    });
}

/* ── Component ────────────────────────────────────────────────────── */

export default function InterviewHistoryPage() {
    const navigate = useNavigate();

    // Data state
    const [data, setData] = useState<HistoryResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [jobs, setJobs] = useState<JobOption[]>([]);

    // Filter / search state
    const [searchQuery, setSearchQuery] = useState('');
    const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
    const [filterJobId, setFilterJobId] = useState('');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [page, setPage] = useState(1);
    const pageSize = 20;

    // Debounced search
    const [debouncedSearch, setDebouncedSearch] = useState('');
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchQuery);
            setPage(1); // reset to first page on new search
        }, 350);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Reset page when filters change
    useEffect(() => { setPage(1); }, [filterStatus, filterJobId, sortOrder]);

    // Fetch jobs for the filter dropdown (once)
    useEffect(() => {
        client.get('/jobs').then(res => {
            const jobList = res.data.map((j: any) => ({ id: String(j.id), title: j.title }));
            setJobs(jobList);
        }).catch(() => {});
    }, []);

    // Fetch history
    const fetchHistory = useCallback(async () => {
        setLoading(true);
        try {
            const params: Record<string, string | number> = {
                page,
                page_size: pageSize,
                sort_order: sortOrder,
            };
            if (debouncedSearch.trim()) params.search = debouncedSearch.trim();
            if (filterStatus !== 'all') params.status = filterStatus;
            if (filterJobId) params.job_id = filterJobId;

            const [res] = await Promise.all([
                client.get('/history', { params }),
                new Promise(resolve => setTimeout(resolve, 300)), // min skeleton time
            ]);
            setData(res.data);
        } catch (err) {
            console.error('Failed to fetch history', err);
        } finally {
            setLoading(false);
        }
    }, [page, pageSize, sortOrder, debouncedSearch, filterStatus, filterJobId]);

    useEffect(() => { fetchHistory(); }, [fetchHistory]);

    // Derived counts (from loaded data only — server handles actual filtering)
    const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

    const statusFilters: { label: string; value: FilterStatus }[] = [
        { label: 'All', value: 'all' },
        { label: 'Completed', value: 'completed' },
        { label: 'Processing', value: 'processing' },
    ];

    const handleClearFilters = () => {
        setSearchQuery('');
        setFilterStatus('all');
        setFilterJobId('');
        setSortOrder('desc');
    };

    const toggleSortOrder = () => {
        setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc');
    };

    // Stats from current response
    const stats = useMemo(() => {
        if (!data) return { total: 0, avgScore: null as number | null, withEval: 0, withTranscript: 0 };
        const items = data.items;
        const scores = items.filter(i => i.overall_score !== null).map(i => i.overall_score!);
        return {
            total: data.total,
            avgScore: scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length * 10) / 10 : null,
            withEval: items.filter(i => i.has_evaluation).length,
            withTranscript: items.filter(i => i.has_transcript).length,
        };
    }, [data]);

    return (
        <div className="sessions-page">
            <Navbar />

            <PageTransition>
                <main className="sessions-main">

                    {/* Page Header */}
                    <div className="sessions-header">
                        <div>
                            <h1 className="sessions-header__title">
                                Interview History
                            </h1>
                            <p className="sessions-header__date">
                                All past interviews · {stats.total} total
                            </p>
                        </div>

                        <div className="sessions-header__actions">
                            <button
                                className="btn-icon"
                                onClick={fetchHistory}
                                aria-label="Refresh history"
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '20px' }} aria-hidden="true">refresh</span>
                            </button>
                        </div>
                    </div>

                    {/* Stats Row */}
                    {!loading && data && (
                        <div className="history-stats-row">
                            <div className="stat-card">
                                <div className="stat-card__icon stat-card__icon--total">
                                    <span className="material-symbols-outlined" aria-hidden="true">history</span>
                                </div>
                                <div>
                                    <div className="stat-card__value">{stats.total}</div>
                                    <div className="stat-card__label">Total Interviews</div>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-card__icon stat-card__icon--completed">
                                    <span className="material-symbols-outlined" aria-hidden="true">check_circle</span>
                                </div>
                                <div>
                                    <div className="stat-card__value">
                                        {stats.avgScore !== null ? stats.avgScore : '—'}
                                    </div>
                                    <div className="stat-card__label">Avg Score (this page)</div>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-card__icon stat-card__icon--upcoming">
                                    <span className="material-symbols-outlined" aria-hidden="true">assessment</span>
                                </div>
                                <div>
                                    <div className="stat-card__value">{stats.withEval}</div>
                                    <div className="stat-card__label">With Evaluations</div>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-card__icon stat-card__icon--today">
                                    <span className="material-symbols-outlined" aria-hidden="true">description</span>
                                </div>
                                <div>
                                    <div className="stat-card__value">{stats.withTranscript}</div>
                                    <div className="stat-card__label">With Transcripts</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Search & Filters Row */}
                    <div className="search-filters-row">
                        <SearchBar value={searchQuery} onChange={setSearchQuery} />
                        <div className="filter-pills" role="tablist" aria-label="Filter by status">
                            {statusFilters.map((f) => (
                                <button
                                    key={f.value}
                                    className={`filter-pill ${filterStatus === f.value ? 'filter-pill--active' : ''}`}
                                    onClick={() => setFilterStatus(f.value)}
                                    role="tab"
                                    aria-selected={filterStatus === f.value}
                                >
                                    {f.label}
                                </button>
                            ))}
                        </div>
                        {jobs.length > 0 && (
                            <select
                                className="job-filter-select"
                                value={filterJobId}
                                onChange={e => setFilterJobId(e.target.value)}
                                aria-label="Filter by job"
                            >
                                <option value="">All Jobs</option>
                                {jobs.map(j => (
                                    <option key={j.id} value={j.id}>{j.title}</option>
                                ))}
                            </select>
                        )}
                    </div>

                    {/* Table or Loading/Empty */}
                    {loading ? (
                        <div className="history-table-wrap">
                            {[1, 2, 3, 4, 5, 6].map(i => (
                                <div className="skeleton-table-row" key={i}>
                                    {[1, 2, 3, 4, 5, 6, 7].map(j => (
                                        <div key={j} className="skeleton-shimmer skeleton-cell" />
                                    ))}
                                </div>
                            ))}
                        </div>
                    ) : data && data.items.length > 0 ? (
                        <>
                            <div className="history-table-wrap">
                                <table className="history-table">
                                    <thead>
                                        <tr>
                                            <th>Candidate</th>
                                            <th>Job Title</th>
                                            <th
                                                className="sortable"
                                                onClick={toggleSortOrder}
                                                aria-label={`Sort by date ${sortOrder === 'desc' ? 'ascending' : 'descending'}`}
                                            >
                                                Date
                                                <span className="sort-icon material-symbols-outlined" aria-hidden="true">
                                                    {sortOrder === 'desc' ? 'arrow_downward' : 'arrow_upward'}
                                                </span>
                                            </th>
                                            <th>Status</th>
                                            <th>Score</th>
                                            <th>Recommendation</th>
                                            <th>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.items.map(item => (
                                            <tr key={item.session_id}>
                                                <td>
                                                    <div className="history-candidate">
                                                        <AvatarInitials name={item.candidate_name} size={34} />
                                                        <span className="history-candidate__name">
                                                            {item.candidate_name}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td>{item.job_title}</td>
                                                <td>{formatDate(item.interview_date)}</td>
                                                <td>
                                                    <StatusBadge status={item.status as any} />
                                                </td>
                                                <td>
                                                    <span className={`score-badge ${getScoreClass(item.overall_score)}`}>
                                                        {item.overall_score !== null ? item.overall_score : '—'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <span className={`rec-badge ${getRecClass(item.recommendation)}`}>
                                                        {item.recommendation || 'Pending'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <div className="history-actions">
                                                        <button
                                                            className="history-action-btn history-action-btn--primary"
                                                            onClick={() => navigate(`/sessions/${item.session_id}/report`)}
                                                            aria-label={`View report for ${item.candidate_name}`}
                                                        >
                                                            <span className="material-symbols-outlined" aria-hidden="true">assessment</span>
                                                            Report
                                                        </button>
                                                        {item.has_transcript && (
                                                            <button
                                                                className="history-action-btn"
                                                                onClick={() => navigate(`/sessions/${item.session_id}/report`)}
                                                                aria-label={`View transcript for ${item.candidate_name}`}
                                                            >
                                                                <span className="material-symbols-outlined" aria-hidden="true">description</span>
                                                                Transcript
                                                            </button>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination */}
                            <div className="history-pagination">
                                <span className="history-pagination__info">
                                    Showing {((data.page - 1) * data.page_size) + 1}–{Math.min(data.page * data.page_size, data.total)} of {data.total} interviews
                                </span>
                                <div className="history-pagination__controls">
                                    <button
                                        className="history-pagination__btn"
                                        disabled={page <= 1}
                                        onClick={() => setPage(p => Math.max(1, p - 1))}
                                        aria-label="Previous page"
                                    >
                                        <span className="material-symbols-outlined" aria-hidden="true">chevron_left</span>
                                        Prev
                                    </button>
                                    <span className="history-pagination__page">
                                        {page}
                                    </span>
                                    <button
                                        className="history-pagination__btn"
                                        disabled={page >= totalPages}
                                        onClick={() => setPage(p => p + 1)}
                                        aria-label="Next page"
                                    >
                                        Next
                                        <span className="material-symbols-outlined" aria-hidden="true">chevron_right</span>
                                    </button>
                                </div>
                            </div>
                        </>
                    ) : (
                        <EmptyState
                            hasActiveFilter={filterStatus !== 'all' || !!filterJobId}
                            hasSearchQuery={searchQuery.trim().length > 0}
                            onClearFilters={handleClearFilters}
                            onCreateSession={() => navigate('/sessions')}
                        />
                    )}

                </main>
            </PageTransition>
        </div>
    );
}
