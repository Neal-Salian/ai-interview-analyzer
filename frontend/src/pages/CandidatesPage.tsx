import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import client from '../api/client'
import PageTransition from '../components/PageTransition'
import { StatusBadge } from '../components/Sessions/StatusBadge'
import ImportCandidatesModal from '../components/ImportCandidatesModal'

export default function CandidatesPage() {
    const [candidates, setCandidates] = useState<any[]>([])
    const [jobs, setJobs] = useState<any[]>([])
    const [searchQuery, setSearchQuery] = useState('')
    const [statusFilter, setStatusFilter] = useState('Draft')
    const [jobFilter, setJobFilter] = useState('All')
    const [loading, setLoading] = useState(true)
    const [showImportModal, setShowImportModal] = useState(false)
    const navigate = useNavigate()

    const fetchData = useCallback(async () => {
        try {
            setLoading(true)
            const [candRes, jobsRes] = await Promise.all([
                client.get('/candidates'),
                client.get('/jobs')
            ])
            setCandidates(candRes.data)
            setJobs(jobsRes.data)
        } catch (err) {
            console.error('Failed to load data:', err)
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchData()
    }, [fetchData])

    const filteredCandidates = candidates.filter(c => {
        const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                              c.email.toLowerCase().includes(searchQuery.toLowerCase())
        const cStatus = c.status || 'Draft';
        const matchesStatus = statusFilter === 'All' || cStatus === statusFilter;
        
        let matchesJob = true
        if (jobFilter !== 'All') {
            const jobObj = jobs.find(j => j.id === jobFilter)
            const jobTitle = jobObj ? jobObj.title : null
            matchesJob = c.applied_jobs.includes(jobTitle)
        }

        return matchesSearch && matchesStatus && matchesJob
    })

    const tabs = ['All', 'Draft', 'Scheduled', 'Completed']

    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />
            <PageTransition>
                <div style={{ padding: '2rem 4rem', maxWidth: '1400px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                        <div>
                            <h1 style={{ fontSize: '28px', fontWeight: 700, fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em', marginBottom: '4px' }}>Candidates</h1>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Manage all your candidates and track their progress.</p>
                        </div>
                        <div style={{ display: 'flex', gap: '10px' }}>
                            <button
                                onClick={() => setShowImportModal(true)}
                                style={{
                                    background: 'var(--bg-surface)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius)',
                                    padding: '10px 16px',
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s',
                                }}
                                id="import-candidates-btn"
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>upload_file</span>
                                Import Candidates
                            </button>
                            <button
                                onClick={() => navigate('/candidates/new')}
                                style={{
                                    background: 'var(--accent)',
                                    backgroundImage: 'var(--accent-gradient)',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: 'var(--radius)',
                                    padding: '10px 16px',
                                    fontSize: '14px',
                                    fontWeight: 600,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    cursor: 'pointer',
                                    boxShadow: 'var(--accent-glow)'
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>add</span>
                                Add Candidate
                            </button>
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', alignItems: 'center', flexWrap: 'wrap' }}>
                        <div style={{ position: 'relative', flex: '1 1 300px' }}>
                            <span className="material-symbols-outlined" style={{ position: 'absolute', left: '12px', top: '10px', fontSize: '18px', color: 'var(--text-secondary)' }}>search</span>
                            <input
                                type="text"
                                placeholder="Search by name or email..."
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '10px 10px 10px 38px',
                                    borderRadius: 'var(--radius)',
                                    border: '1px solid var(--border)',
                                    background: 'var(--bg-surface)',
                                    color: 'var(--text-primary)',
                                    fontSize: '14px',
                                    boxSizing: 'border-box'
                                }}
                            />
                        </div>
                        
                        <div style={{ display: 'flex', gap: '8px', background: 'var(--bg-surface)', padding: '4px', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                            {tabs.map(tab => (
                                <button
                                    key={tab}
                                    onClick={() => setStatusFilter(tab)}
                                    style={{
                                        padding: '6px 16px',
                                        border: 'none',
                                        background: statusFilter === tab ? 'var(--bg-surface-high)' : 'transparent',
                                        color: statusFilter === tab ? 'var(--text-primary)' : 'var(--text-secondary)',
                                        borderRadius: 'var(--radius)',
                                        fontSize: '14px',
                                        fontWeight: statusFilter === tab ? 600 : 500,
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {tab}
                                </button>
                            ))}
                        </div>

                        <select
                            value={jobFilter}
                            onChange={e => setJobFilter(e.target.value)}
                            style={{
                                padding: '10px 14px',
                                borderRadius: 'var(--radius)',
                                border: '1px solid var(--border)',
                                background: 'var(--bg-surface)',
                                color: 'var(--text-primary)',
                                fontSize: '14px'
                            }}
                        >
                            <option value="All">All Jobs</option>
                            {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
                        </select>
                    </div>

                    {loading ? (
                        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>Loading candidates...</div>
                    ) : filteredCandidates.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '60px 20px', background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)', border: '1px dashed var(--border)' }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '48px', color: 'var(--text-secondary)', marginBottom: '16px', display: 'block' }}>group_off</span>
                            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px' }}>No candidates found</h3>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Try adjusting your filters or add a new candidate.</p>
                        </div>
                    ) : (
                        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-surface-high)' }}>
                                        <th style={thStyle}>Candidate</th>
                                        <th style={thStyle}>Status</th>
                                        <th style={thStyle}>Applied Jobs</th>
                                        <th style={thStyle}>Added</th>
                                        <th style={thStyle}></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredCandidates.map(c => (
                                        <tr key={c.id} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.2s' }} 
                                            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-surface-high)'}
                                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                            onClick={() => navigate(`/candidates/${c.id}`)}
                                        >
                                            <td style={tdStyle}>
                                                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px' }}>{c.name}</div>
                                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{c.email}</div>
                                                {c.phone && <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>{c.phone}</div>}
                                            </td>
                                            <td style={tdStyle}>
                                                <StatusBadge status={(c.status || 'Draft').toLowerCase() as any} />
                                            </td>
                                            <td style={tdStyle}>
                                                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                                    {c.applied_jobs && c.applied_jobs.length > 0 ? c.applied_jobs.map((job: string, i: number) => (
                                                        <span key={i} style={{ padding: '2px 8px', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                                            {job}
                                                        </span>
                                                    )) : <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>-</span>}
                                                </div>
                                            </td>
                                            <td style={tdStyle}>
                                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                                    {new Date(c.created_at).toLocaleDateString()}
                                                </div>
                                            </td>
                                            <td style={{ ...tdStyle, textAlign: 'right' }}>
                                                <span className="material-symbols-outlined" style={{ color: 'var(--text-secondary)', fontSize: '20px' }}>chevron_right</span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </PageTransition>

            {showImportModal && (
                <ImportCandidatesModal
                    onClose={() => setShowImportModal(false)}
                    onImportComplete={() => fetchData()}
                    jobs={jobs.map((j: any) => ({ id: j.id, title: j.title }))}
                />
            )}
        </div>
    )
}

const thStyle: React.CSSProperties = {
    padding: '16px',
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
}

const tdStyle: React.CSSProperties = {
    padding: '16px',
    verticalAlign: 'middle'
}
