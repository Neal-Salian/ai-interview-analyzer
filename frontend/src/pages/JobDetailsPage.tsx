import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import client from '../api/client';
import PageTransition from '../components/PageTransition';
import type { Job } from './JobsPage';
import './JobDetailsPage.css';

export default function JobDetailsPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    
    const [job, setJob] = useState<Job | null>(null);
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
