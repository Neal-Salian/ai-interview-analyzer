import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import client from '../api/client'
import PageTransition from '../components/PageTransition'
import { StatusBadge } from '../components/Sessions/StatusBadge'

export default function CandidateDetailsPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const [candidate, setCandidate] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [isEditing, setIsEditing] = useState(false)
    const [editForm, setEditForm] = useState({ name: '', email: '', phone: '', notes: '' })
    const [saving, setSaving] = useState(false)
    const [uploading, setUploading] = useState(false)
    const [jobs, setJobs] = useState<any[]>([])
    const [scheduleModalOpen, setScheduleModalOpen] = useState(false)
    const [selectedDraftSessionId, setSelectedDraftSessionId] = useState<string | null>(null)
    const [scheduleForm, setScheduleForm] = useState({ scheduled_at: '', interview_type: '', notes: '' })
    const fileInputRef = useRef<HTMLInputElement>(null)



    useEffect(() => {
        fetchCandidate()
        fetchJobs()
    }, [id])

    const fetchJobs = async () => {
        try {
            const res = await client.get('/jobs')
            setJobs(res.data)
        } catch (err) {
            console.error('Failed to load jobs', err)
        }
    }

    const fetchCandidate = async () => {
        try {
            const res = await client.get(`/candidates/${id}`)
            setCandidate(res.data)
            setEditForm({
                name: res.data.name || '',
                email: res.data.email || '',
                phone: res.data.phone || '',
                notes: res.data.notes || ''
            })
        } catch (err) {
            console.error('Failed to load candidate', err)
        } finally {
            setLoading(false)
        }
    }

    const handleSave = async () => {
        setSaving(true)
        try {
            await client.patch(`/candidates/${id}`, editForm)
            await fetchCandidate()
            setIsEditing(false)
        } catch (err) {
            console.error('Failed to save', err)
            alert('Failed to save changes. Email might be in use.')
        } finally {
            setSaving(false)
        }
    }

    const handleAssignJob = async (sessionId: string, jobId: string) => {
        try {
            await client.patch(`/sessions/${sessionId}/job`, { job_id: jobId })
            await fetchCandidate()
        } catch (err) {
            console.error('Failed to assign job', err)
            alert('Failed to assign job')
        }
    }

    const handleScheduleSubmit = async () => {
        if (!selectedDraftSessionId) return
        try {
            await client.patch(`/sessions/${selectedDraftSessionId}/schedule`, scheduleForm)
            setScheduleModalOpen(false)
            setScheduleForm({ scheduled_at: '', interview_type: '', notes: '' })
            await fetchCandidate()
        } catch (err) {
            console.error('Failed to schedule session', err)
            alert('Failed to schedule session')
        }
    }

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        if (!file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
            alert('Only PDF and DOCX files are allowed.')
            return
        }

        setUploading(true)
        const formData = new FormData()
        formData.append('file', file)

        try {
            await client.post(`/candidates/${id}/resume`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            await fetchCandidate()
        } catch (err) {
            console.error('Upload failed', err)
            alert('Failed to upload resume.')
        } finally {
            setUploading(false)
            if (fileInputRef.current) fileInputRef.current.value = ''
        }
    }

    if (loading) {
        return (
            <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg)' }}>
                <Navbar />
                <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading candidate...</div>
            </div>
        )
    }

    if (!candidate) {
        return (
            <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg)' }}>
                <Navbar />
                <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>Candidate not found</div>
            </div>
        )
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />
            <PageTransition>
                <div style={{ padding: '2rem 4rem', maxWidth: '1000px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
                    <button onClick={() => navigate('/candidates')} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 500, padding: '0 0 16px 0' }}>
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>arrow_back</span>
                        Back to Candidates
                    </button>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                        <div>
                            <h1 style={{ fontSize: '28px', fontWeight: 700, fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                                {candidate.name}
                                {!isEditing && <StatusBadge status={candidate.status.toLowerCase() as any} />}
                            </h1>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Added on {new Date(candidate.created_at).toLocaleDateString()}</p>
                        </div>
                        {!isEditing ? (
                            <button
                                onClick={() => setIsEditing(true)}
                                style={{
                                    background: 'var(--bg-surface-high)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius)',
                                    padding: '8px 16px',
                                    fontSize: '13px',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px'
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>edit</span>
                                Edit Profile
                            </button>
                        ) : (
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <button
                                    onClick={() => {
                                        setIsEditing(false)
                                        setEditForm({
                                            name: candidate.name || '',
                                            email: candidate.email || '',
                                            phone: candidate.phone || '',
                                            notes: candidate.notes || ''
                                        })
                                    }}
                                    style={{
                                        background: 'transparent',
                                        color: 'var(--text-secondary)',
                                        border: '1px solid var(--border)',
                                        borderRadius: 'var(--radius)',
                                        padding: '8px 16px',
                                        fontSize: '13px',
                                        cursor: 'pointer'
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSave}
                                    disabled={saving}
                                    style={{
                                        background: 'var(--accent)',
                                        color: '#fff',
                                        border: 'none',
                                        borderRadius: 'var(--radius)',
                                        padding: '8px 16px',
                                        fontSize: '13px',
                                        fontWeight: 600,
                                        cursor: 'pointer',
                                        opacity: saving ? 0.7 : 1
                                    }}
                                >
                                    {saving ? 'Saving...' : 'Save Changes'}
                                </button>
                            </div>
                        )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '24px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                            {/* Profile Info */}
                            <div style={cardStyle}>
                                <h3 style={cardTitleStyle}>Contact Information</h3>
                                {isEditing ? (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                        <div>
                                            <label style={labelStyle}>Full Name</label>
                                            <input value={editForm.name} onChange={e => setEditForm({...editForm, name: e.target.value})} style={inputStyle} />
                                        </div>
                                        <div>
                                            <label style={labelStyle}>Email</label>
                                            <input type="email" value={editForm.email} onChange={e => setEditForm({...editForm, email: e.target.value})} style={inputStyle} />
                                        </div>
                                        <div>
                                            <label style={labelStyle}>Phone (Optional)</label>
                                            <input value={editForm.phone} onChange={e => setEditForm({...editForm, phone: e.target.value})} style={inputStyle} />
                                        </div>
                                    </div>
                                ) : (
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                                        <div>
                                            <div style={labelStyle}>Email</div>
                                            <div style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{candidate.email}</div>
                                        </div>
                                        <div>
                                            <div style={labelStyle}>Phone</div>
                                            <div style={{ fontSize: '14px', color: 'var(--text-primary)' }}>{candidate.phone || '-'}</div>
                                        </div>
                                        <div style={{ gridColumn: 'span 2' }}>
                                            <div style={labelStyle}>Applied Jobs</div>
                                            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '4px' }}>
                                                {candidate.applied_jobs && candidate.applied_jobs.length > 0 ? candidate.applied_jobs.map((job: any, i: number) => (
                                                    <span key={i} style={{ padding: '4px 10px', background: 'var(--bg-surface-high)', border: '1px solid var(--border)', borderRadius: '16px', fontSize: '13px' }}>
                                                        {job.title}
                                                    </span>
                                                )) : <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>No jobs applied</span>}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Notes */}
                            <div style={cardStyle}>
                                <h3 style={cardTitleStyle}>Recruiter Notes</h3>
                                {isEditing ? (
                                    <textarea 
                                        value={editForm.notes} 
                                        onChange={e => setEditForm({...editForm, notes: e.target.value})} 
                                        style={{ ...inputStyle, minHeight: '120px', resize: 'vertical' }} 
                                        placeholder="Add notes about this candidate..."
                                    />
                                ) : (
                                    <div style={{ fontSize: '14px', color: candidate.notes ? 'var(--text-primary)' : 'var(--text-secondary)', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
                                        {candidate.notes || 'No notes added yet.'}
                                    </div>
                                )}
                            </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                            {/* Resume */}
                            <div style={cardStyle}>
                                <h3 style={cardTitleStyle}>Resume</h3>
                                {candidate.resume_url ? (
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', background: 'var(--bg-surface-high)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                                        <span className="material-symbols-outlined" style={{ color: 'var(--accent)', fontSize: '24px' }}>description</span>
                                        <div style={{ flex: 1, overflow: 'hidden' }}>
                                            <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                                                Resume
                                            </div>
                                            <button
                                                onClick={async () => {
                                                    try {
                                                        const res = await client.get(`/candidates/${id}/resume`, { responseType: 'blob' })
                                                        const contentType = (res.headers['content-type'] as string) || 'application/octet-stream'
                                                        const blob = new Blob([res.data], { type: contentType })
                                                        const url = URL.createObjectURL(blob)
                                                        window.open(url, '_blank')
                                                        // Revoke after a delay to allow the tab to load
                                                        setTimeout(() => URL.revokeObjectURL(url), 60000)
                                                    } catch {
                                                        alert('Failed to download resume.')
                                                    }
                                                }}
                                                style={{ background: 'none', border: 'none', padding: 0, fontSize: '12px', color: 'var(--accent)', textDecoration: 'none', cursor: 'pointer' }}
                                            >View File</button>
                                        </div>
                                    </div>
                                ) : (
                                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>No resume uploaded.</div>
                                )}
                                
                                <input 
                                    type="file" 
                                    ref={fileInputRef} 
                                    style={{ display: 'none' }} 
                                    accept=".pdf,.docx" 
                                    onChange={handleFileUpload} 
                                />
                                <button
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={uploading}
                                    style={{
                                        width: '100%',
                                        background: 'transparent',
                                        border: '1px dashed var(--border)',
                                        color: 'var(--text-primary)',
                                        padding: '10px',
                                        borderRadius: 'var(--radius)',
                                        fontSize: '13px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '6px',
                                        marginTop: candidate.resume_url ? '12px' : '0'
                                    }}
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>upload</span>
                                    {uploading ? 'Uploading...' : (candidate.resume_url ? 'Update Resume' : 'Upload Resume')}
                                </button>
                            </div>

                            {/* Session History */}
                            <div style={cardStyle}>
                                <h3 style={cardTitleStyle}>Interview History</h3>
                                {candidate.session_history && candidate.session_history.length > 0 ? (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                        {candidate.session_history.map((s: any, i: number) => (
                                            <div key={i} style={{ padding: '12px', background: 'var(--bg-surface-high)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                                    <span style={{ fontSize: '13px', fontWeight: 600 }}>{s.job || 'No Job Assigned'}</span>
                                                    <StatusBadge status={s.status.toLowerCase() as any} />
                                                </div>
                                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                                                    {s.scheduled_at ? new Date(s.scheduled_at).toLocaleString() : 'Unscheduled'}
                                                </div>
                                                
                                                {s.status === 'draft' && (
                                                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap' }}>
                                                        <select 
                                                            value={s.job_id || ''}
                                                            onChange={(e) => handleAssignJob(s.session_id, e.target.value)}
                                                            style={{ ...inputStyle, width: 'auto', padding: '6px 10px', fontSize: '12px' }}
                                                        >
                                                            <option value="">Assign Job...</option>
                                                            {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
                                                        </select>
                                                        
                                                        <button 
                                                            onClick={() => {
                                                                setSelectedDraftSessionId(s.session_id)
                                                                setScheduleModalOpen(true)
                                                            }}
                                                            style={{
                                                                background: 'var(--accent)',
                                                                color: '#fff',
                                                                border: 'none',
                                                                borderRadius: 'var(--radius)',
                                                                padding: '6px 12px',
                                                                fontSize: '12px',
                                                                fontWeight: 600,
                                                                cursor: 'pointer'
                                                            }}
                                                        >
                                                            Schedule Interview
                                                        </button>
                                                    </div>
                                                )}
                                                {s.status !== 'draft' && (
                                                    <button 
                                                        onClick={() => navigate(`/sessions/${s.session_id}/live`)}
                                                        style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-primary)', borderRadius: 'var(--radius)', padding: '6px 12px', fontSize: '12px', cursor: 'pointer', marginTop: '8px' }}
                                                    >
                                                        View Session
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No interview sessions found.</div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </PageTransition>

            {scheduleModalOpen && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }} onClick={() => setScheduleModalOpen(false)}>
                    <div onClick={(e) => e.stopPropagation()} style={{ background: 'var(--bg-surface)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '400px', border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)' }}>
                        <h2 style={{ marginBottom: '16px', fontSize: '18px', fontFamily: 'var(--font-heading)', fontWeight: 600 }}>Schedule Interview</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div>
                                <label style={labelStyle}>Date & Time</label>
                                <input type="datetime-local" value={scheduleForm.scheduled_at} onChange={e => setScheduleForm({...scheduleForm, scheduled_at: e.target.value})} style={inputStyle} />
                            </div>
                            <div>
                                <label style={labelStyle}>Interview Type</label>
                                <input placeholder="e.g. Technical, Behavioral" value={scheduleForm.interview_type} onChange={e => setScheduleForm({...scheduleForm, interview_type: e.target.value})} style={inputStyle} />
                            </div>
                            <div>
                                <label style={labelStyle}>Notes</label>
                                <textarea placeholder="Preparation notes..." value={scheduleForm.notes} onChange={e => setScheduleForm({...scheduleForm, notes: e.target.value})} style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }} />
                            </div>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '24px' }}>
                            <button onClick={() => setScheduleModalOpen(false)} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-primary)', padding: '8px 16px', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}>Cancel</button>
                            <button onClick={handleScheduleSubmit} disabled={!scheduleForm.scheduled_at} style={{ background: 'var(--accent)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 'var(--radius)', cursor: 'pointer', opacity: scheduleForm.scheduled_at ? 1 : 0.5, fontSize: '13px', fontWeight: 600 }}>Schedule</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

const cardStyle: React.CSSProperties = {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '24px',
    boxShadow: 'var(--shadow-card)'
}

const cardTitleStyle: React.CSSProperties = {
    fontSize: '16px',
    fontWeight: 600,
    fontFamily: 'var(--font-heading)',
    marginBottom: '16px',
    color: 'var(--text-primary)'
}

const labelStyle: React.CSSProperties = {
    display: 'block',
    marginBottom: '6px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    fontFamily: 'var(--font-heading)',
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
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
    boxSizing: 'border-box'
}
