import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import client from '../api/client';
import PageTransition from '../components/PageTransition';
import './JobsPage.css';

export interface Job {
    id: string;
    title: string;
    raw_description: string;
    seniority_level?: string;
    interview_type?: string;
    extracted_skills?: string[];
    created_at: string;
    is_archived?: boolean;
}

export default function JobsPage() {
    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [showNewJob, setShowNewJob] = useState(false);
    const [creating, setCreating] = useState(false);
    
    // New Job Form State
    const [newTitle, setNewTitle] = useState('');
    const [newDescription, setNewDescription] = useState('');
    const [newSeniority, setNewSeniority] = useState('');
    const [newInterviewType, setNewInterviewType] = useState('');

    const navigate = useNavigate();

    const fetchJobs = async () => {
        try {
            const res = await client.get('/jobs');
            setJobs(res.data);
        } catch (err) {
            console.error('Failed to fetch jobs', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
    }, []);

    const filteredJobs = useMemo(() => {
        if (!searchQuery.trim()) return jobs;
        const q = searchQuery.toLowerCase();
        return jobs.filter(j => 
            j.title.toLowerCase().includes(q) || 
            (j.raw_description && j.raw_description.toLowerCase().includes(q))
        );
    }, [jobs, searchQuery]);

    const handleCreateJob = async () => {
        if (!newTitle.trim()) return;
        setCreating(true);
        try {
            await client.post('/jobs', {
                title: newTitle,
                raw_description: newDescription,
                seniority_level: newSeniority,
                interview_type: newInterviewType
            });
            setShowNewJob(false);
            setNewTitle('');
            setNewDescription('');
            setNewSeniority('');
            setNewInterviewType('');
            await fetchJobs();
        } catch (err) {
            console.error('Failed to create job', err);
        } finally {
            setCreating(false);
        }
    };

    return (
        <div className="jobs-page">
            <Navbar />
            <PageTransition>
                <main className="jobs-main">
                    <div className="jobs-header">
                        <div>
                            <h1 className="jobs-header__title">Job Management</h1>
                            <p className="jobs-header__desc">Create and manage your active job postings.</p>
                        </div>
                    </div>

                    <div className="search-row">
                        <input 
                            type="text" 
                            className="job-search-input" 
                            placeholder="Search jobs..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>

                    {loading ? (
                        <div style={{ color: 'var(--text-secondary)' }}>Loading jobs...</div>
                    ) : (
                        <div className="job-grid">
                            <div 
                                className="create-job-card"
                                onClick={() => setShowNewJob(true)}
                                role="button"
                                tabIndex={0}
                            >
                                <div className="create-job-card__icon-wrap">
                                    <span className="material-symbols-outlined" style={{ color: 'var(--accent)', fontSize: '26px' }}>add</span>
                                </div>
                                <h3 className="create-job-card__title">Create New Job</h3>
                                <p className="create-job-card__desc">Set up a new job profile for interviews.</p>
                            </div>

                            {filteredJobs.map(job => (
                                <div 
                                    key={job.id} 
                                    className="job-card"
                                    onClick={() => navigate(`/jobs/${job.id}`)}
                                >
                                    <h3 className="job-card__title">{job.title}</h3>
                                    <div className="job-card__meta">
                                        {job.seniority_level && <span className="job-card__tag">{job.seniority_level}</span>}
                                        {job.interview_type && <span className="job-card__tag">{job.interview_type}</span>}
                                    </div>
                                    <p className="job-card__desc">
                                        {job.raw_description || 'No description provided.'}
                                    </p>
                                    <div className="job-card__footer">
                                        <span className="job-card__date">
                                            Created {new Date(job.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </main>
            </PageTransition>

            {showNewJob && (
                <div className="modal-backdrop" onClick={() => setShowNewJob(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2 className="modal-title">Create New Job</h2>
                        
                        <label className="modal-label">Job Title</label>
                        <input 
                            className="modal-input"
                            value={newTitle}
                            onChange={e => setNewTitle(e.target.value)}
                            placeholder="e.g. Senior Frontend Developer"
                        />

                        <label className="modal-label">Description</label>
                        <textarea 
                            className="modal-input"
                            value={newDescription}
                            onChange={e => setNewDescription(e.target.value)}
                            placeholder="Job description..."
                            style={{ minHeight: '100px', resize: 'vertical' }}
                        />

                        <label className="modal-label">Experience Level</label>
                        <input 
                            className="modal-input"
                            value={newSeniority}
                            onChange={e => setNewSeniority(e.target.value)}
                            placeholder="e.g. Mid-Level, Senior"
                        />

                        <label className="modal-label">Interview Type</label>
                        <input 
                            className="modal-input"
                            value={newInterviewType}
                            onChange={e => setNewInterviewType(e.target.value)}
                            placeholder="e.g. Technical, Behavioral"
                        />

                        <div className="modal-actions">
                            <button className="modal-btn--cancel" onClick={() => setShowNewJob(false)}>
                                Cancel
                            </button>
                            <button 
                                className="modal-btn--create"
                                onClick={handleCreateJob}
                                disabled={!newTitle.trim() || creating}
                            >
                                {creating ? 'Creating...' : 'Create Job'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
