import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import client from '../api/client';
import PageTransition from '../components/PageTransition';
import type { Job } from './JobsPage';
import './JobDetailsPage.css';

interface JobMetrics {
    total_candidates: number;
    draft_candidates: number;
    scheduled_interviews: number;
    active_interviews: number;
    completed_interviews: number;
    cancelled_interviews: number;
    no_shows: number;
}

interface JobCandidate {
    id: string;
    name: string;
    email: string;
    status: string;
    created_at: string;
}

interface JobSession {
    id: string;
    candidate_name: string | null;
    candidate_id: string | null;
    status: string;
    scheduled_at: string | null;
    interview_type: string | null;
}

interface JobDetails extends Job {
    metrics: JobMetrics;
    candidates: JobCandidate[];
    sessions: JobSession[];
}

export default function JobDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    
    const [job, setJob] = useState<JobDetails | null>(null);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState(false);
    
    const [editTitle, setEditTitle] = useState('');
    const [editDescription, setEditDescription] = useState('');
    const [editSeniority, setEditSeniority] = useState('');
    const [editInterviewType, setEditInterviewType] = useState('');
    const [editSkills, setEditSkills] = useState<string[]>([]);
    const [newSkill, setNewSkill] = useState('');
    const [saving, setSaving] = useState(false);

    const fetchJob = async () => {
        try {
            const res = await client.get(`/jobs/${id}`);
            const data = res.data;
            setJob(data);
            setEditTitle(data.title || '');
            setEditDescription(data.raw_description || '');
            setEditSeniority(data.seniority_level || '');
            setEditInterviewType(data.interview_type || '');
            setEditSkills(data.extracted_skills || []);
        } catch (err) {
            console.error('Failed to fetch job', err);
            // Optionally redirect on 404
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (id) {
            fetchJob();
        }
    }, [id]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await client.patch(`/jobs/${id}`, {
                title: editTitle,
                raw_description: editDescription,
                seniority_level: editSeniority,
                interview_type: editInterviewType,
                extracted_skills: editSkills
            });
            await fetchJob();
            setEditing(false);
        } catch (err) {
            console.error('Failed to update job', err);
        } finally {
            setSaving(false);
        }
    };

    const handleArchive = async () => {
        if (!window.confirm('Are you sure you want to archive this job?')) return;
        try {
            await client.patch(`/jobs/${id}/archive`);
            navigate('/jobs');
        } catch (err) {
            console.error('Failed to archive job', err);
        }
    };

    const handleAddSkill = () => {
        if (newSkill.trim() && !editSkills.includes(newSkill.trim())) {
            setEditSkills([...editSkills, newSkill.trim()]);
            setNewSkill('');
        }
    };

    const handleRemoveSkill = (skillToRemove: string) => {
        setEditSkills(editSkills.filter(s => s !== skillToRemove));
    };

    if (loading) {
        return (
            <div className="job-details-page">
                <Navbar />
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    Loading job details...
                </div>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="job-details-page">
                <Navbar />
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--red)' }}>
                    Job not found.
                </div>
            </div>
        );
    }

    return (
        <div className="job-details-page">
            <Navbar />
            <PageTransition>
                <main className="job-details-main">
                    <div className="job-details-header">
                        <div className="job-details-header__left">
                            <button className="job-details-header__back" onClick={() => navigate('/jobs')}>
                                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>arrow_back</span>
                                Back to Jobs
                            </button>
                            <h1 className="job-details-header__title">{job.title}</h1>
                            {job.is_archived && <span style={{ color: 'var(--red)', fontWeight: 600 }}>Archived</span>}
                        </div>
                        <div className="job-details-header__actions">
                            <button className="btn-secondary" onClick={() => setEditing(true)}>
                                Edit Job
                            </button>
                            {!job.is_archived && (
                                <button className="btn-danger" onClick={handleArchive}>
                                    Archive
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="job-details-content">
                        <div className="job-details-section">
                            <h2 className="job-details-section__title">Job Information</h2>
                            <div className="job-meta-grid">
                                <div className="job-meta-item">
                                    <span className="job-meta-item__label">Created At</span>
                                    <span className="job-meta-item__value">
                                        {new Date(job.created_at).toLocaleString()}
                                    </span>
                                </div>
                                <div className="job-meta-item">
                                    <span className="job-meta-item__label">Experience Level</span>
                                    <span className="job-meta-item__value">
                                        {job.seniority_level || 'Not specified'}
                                    </span>
                                </div>
                                <div className="job-meta-item">
                                    <span className="job-meta-item__label">Interview Type</span>
                                    <span className="job-meta-item__value">
                                        {job.interview_type || 'Not specified'}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="job-details-section">
                            <h2 className="job-details-section__title">Description</h2>
                            <p className="job-details-section__text">
                                {job.raw_description || 'No description provided.'}
                            </p>
                        </div>

                        <div className="job-details-section">
                            <h2 className="job-details-section__title">Skills</h2>
                            {job.extracted_skills && job.extracted_skills.length > 0 ? (
                                <div className="skills-list">
                                    {job.extracted_skills.map((skill, idx) => (
                                        <span key={idx} className="skill-tag">{skill}</span>
                                    ))}
                                </div>
                            ) : (
                                <p className="job-details-section__text">No skills extracted/provided.</p>
                            )}
                        </div>

                        <div className="job-details-section">
                            <h2 className="job-details-section__title">Job Metrics</h2>
                            <div className="metrics-grid">
                                <div className="metric-card">
                                    <span className="metric-card__label">Total Candidates</span>
                                    <span className="metric-card__value">{job.metrics.total_candidates}</span>
                                </div>
                                <div className="metric-card">
                                    <span className="metric-card__label">Drafts</span>
                                    <span className="metric-card__value">{job.metrics.draft_candidates}</span>
                                </div>
                                <div className="metric-card">
                                    <span className="metric-card__label">Scheduled</span>
                                    <span className="metric-card__value">{job.metrics.scheduled_interviews}</span>
                                </div>
                                <div className="metric-card">
                                    <span className="metric-card__label">Active</span>
                                    <span className="metric-card__value">{job.metrics.active_interviews}</span>
                                </div>
                                <div className="metric-card">
                                    <span className="metric-card__label">Completed</span>
                                    <span className="metric-card__value">{job.metrics.completed_interviews}</span>
                                </div>
                                <div className="metric-card metric-card--danger">
                                    <span className="metric-card__label">No Shows / Cancel</span>
                                    <span className="metric-card__value">{job.metrics.no_shows + job.metrics.cancelled_interviews}</span>
                                </div>
                            </div>
                            
                            <h3 className="job-details-section__subtitle">Candidate Funnel</h3>
                            <div className="funnel-container">
                                <div className="funnel-step">
                                    <div className="funnel-step__count">{job.metrics.total_candidates}</div>
                                    <div className="funnel-step__label">Sourced</div>
                                </div>
                                <div className="funnel-divider">
                                    <span className="material-symbols-outlined">chevron_right</span>
                                </div>
                                <div className="funnel-step">
                                    <div className="funnel-step__count">{job.metrics.scheduled_interviews}</div>
                                    <div className="funnel-step__label">Scheduled</div>
                                </div>
                                <div className="funnel-divider">
                                    <span className="material-symbols-outlined">chevron_right</span>
                                </div>
                                <div className="funnel-step">
                                    <div className="funnel-step__count">{job.metrics.completed_interviews}</div>
                                    <div className="funnel-step__label">Completed</div>
                                </div>
                            </div>
                        </div>

                        <div className="job-details-section">
                            <div className="job-section-header">
                                <h2 className="job-details-section__title" style={{ margin: 0 }}>Candidates</h2>
                                <button className="btn-secondary" title="Import functionality pending" disabled>
                                    <span className="material-symbols-outlined" style={{ fontSize: '18px', marginRight: '6px' }}>upload</span>
                                    Import Candidates
                                </button>
                            </div>
                            {job.candidates && job.candidates.length > 0 ? (
                                <div className="job-table-wrapper">
                                    <table className="job-table">
                                        <thead>
                                            <tr>
                                                <th>Name</th>
                                                <th>Email</th>
                                                <th>Status</th>
                                                <th>Created</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {job.candidates.map(c => (
                                                <tr key={c.id}>
                                                    <td>{c.name}</td>
                                                    <td>{c.email}</td>
                                                    <td><span className={`status-badge status-${c.status.toLowerCase()}`}>{c.status}</span></td>
                                                    <td>{new Date(c.created_at).toLocaleDateString()}</td>
                                                    <td>
                                                        <Link to={`/candidates/${c.id}`} className="table-action-link">View</Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <p className="job-details-section__text">No candidates associated with this job yet.</p>
                            )}
                        </div>

                        <div className="job-details-section">
                            <div className="job-section-header">
                                <h2 className="job-details-section__title" style={{ margin: 0 }}>Sessions</h2>
                            </div>
                            {job.sessions && job.sessions.length > 0 ? (
                                <div className="job-table-wrapper">
                                    <table className="job-table">
                                        <thead>
                                            <tr>
                                                <th>Candidate</th>
                                                <th>Status</th>
                                                <th>Scheduled For</th>
                                                <th>Type</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {job.sessions.map(s => (
                                                <tr key={s.id}>
                                                    <td>{s.candidate_name || 'Unknown'}</td>
                                                    <td><span className={`status-badge status-${s.status.toLowerCase()}`}>{s.status}</span></td>
                                                    <td>{s.scheduled_at ? new Date(s.scheduled_at).toLocaleString() : 'TBD'}</td>
                                                    <td>{s.interview_type || '-'}</td>
                                                    <td>
                                                        <Link to={`/sessions`} className="table-action-link">Manage</Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <p className="job-details-section__text">No sessions scheduled for this job yet.</p>
                            )}
                        </div>
                    </div>
                </main>
            </PageTransition>

            {editing && (
                <div className="modal-backdrop" onClick={() => setEditing(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h2 className="modal-title">Edit Job</h2>
                        
                        <label className="modal-label">Job Title</label>
                        <input 
                            className="modal-input"
                            value={editTitle}
                            onChange={e => setEditTitle(e.target.value)}
                        />

                        <label className="modal-label">Description</label>
                        <textarea 
                            className="modal-input"
                            value={editDescription}
                            onChange={e => setEditDescription(e.target.value)}
                            style={{ minHeight: '120px', resize: 'vertical' }}
                        />

                        <label className="modal-label">Experience Level</label>
                        <input 
                            className="modal-input"
                            value={editSeniority}
                            onChange={e => setEditSeniority(e.target.value)}
                        />

                        <label className="modal-label">Interview Type</label>
                        <input 
                            className="modal-input"
                            value={editInterviewType}
                            onChange={e => setEditInterviewType(e.target.value)}
                        />

                        <label className="modal-label">Skills</label>
                        <div className="skills-list" style={{ marginBottom: '12px' }}>
                            {editSkills.map((skill, idx) => (
                                <span key={idx} className="skill-tag skill-tag-edit">
                                    {skill}
                                    <span 
                                        className="material-symbols-outlined skill-tag-remove"
                                        onClick={() => handleRemoveSkill(skill)}
                                    >
                                        close
                                    </span>
                                </span>
                            ))}
                        </div>
                        <div className="add-skill-form">
                            <input 
                                className="add-skill-input"
                                value={newSkill}
                                onChange={e => setNewSkill(e.target.value)}
                                placeholder="Add a skill..."
                                onKeyDown={e => {
                                    if (e.key === 'Enter') {
                                        e.preventDefault();
                                        handleAddSkill();
                                    }
                                }}
                            />
                            <button className="add-skill-btn" onClick={handleAddSkill}>
                                Add
                            </button>
                        </div>

                        <div className="modal-actions">
                            <button className="modal-btn--cancel" onClick={() => setEditing(false)}>
                                Cancel
                            </button>
                            <button 
                                className="modal-btn--create"
                                onClick={handleSave}
                                disabled={saving}
                            >
                                {saving ? 'Saving...' : 'Save Changes'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
