import { useParams } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import Navbar from '../components/Navbar'

// Mock data — replace with GET /api/analysis/{session_id} when built
const MOCK_REPORT = {
    candidate: 'Priya Sharma',
    date: new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' }),
    duration: '42 minutes',
    emotion_breakdown: [
        { emotion: 'Neutral', count: 28 },
        { emotion: 'Happy', count: 18 },
        { emotion: 'Anxious', count: 9 },
        { emotion: 'Surprise', count: 5 },
    ],
    summary: 'Candidate demonstrated strong technical knowledge in Python and system design. Communication was clear and structured. Showed some anxiety when discussing team conflicts but recovered well. STAR framework was used consistently for behavioral questions. Confidence score averaged 7.4/10 over the session.',
    transcript_preview: [
        'I have been working with Python for over five years, primarily in backend development...',
        'In my last role, I led a team of three engineers to migrate our monolith to microservices...',
        'The biggest challenge was maintaining uptime during the migration — we used a strangler fig pattern...',
    ],
    questions_asked: [
        'Can you walk me through a specific example of a challenging project you led?',
        'What metrics did you use to measure success in that role?',
    ],
}

const EMOTION_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f472b6']

export default function ReportPage() {
    const { id: sessionId } = useParams<{ id: string }>()
    const r = MOCK_REPORT

    return (
        <div>
            <Navbar />
            <div style={{ padding: '32px 24px', maxWidth: '900px', margin: '0 auto' }}>

                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
                    <div>
                        <h1 style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-heading)', letterSpacing: '-0.02em' }}>{r.candidate}</h1>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '4px' }}>
                            {r.date} · {r.duration} · Session {sessionId?.slice(0, 8)}...
                        </p>
                    </div>
                    <button
                        disabled
                        title="PDF generation coming soon"
                        style={{
                            background: 'var(--bg-surface)',
                            color: 'var(--red)',
                            border: '1px solid var(--red)',
                            borderRadius: 'var(--radius)',
                            padding: '8px 16px',
                            fontSize: '13px',
                            cursor: 'not-allowed',
                        }}
                    >
                        ↓ Download PDF (coming soon)
                    </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

                    {/* AI Summary */}
                    <div style={cardStyle}>
                        <div style={sectionLabel}>AI Summary</div>
                        <p style={{ fontSize: '14px', lineHeight: 1.7, color: 'var(--text-primary)' }}>
                            {r.summary}
                        </p>
                    </div>

                    {/* Emotion breakdown */}
                    <div style={cardStyle}>
                        <div style={sectionLabel}>Emotion Breakdown</div>
                        <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={r.emotion_breakdown} barSize={32}>
                                <XAxis dataKey="emotion" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} axisLine={false} tickLine={false} />
                                <YAxis hide />
                                <Tooltip
                                    contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '12px' }}
                                />
                                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                    {r.emotion_breakdown.map((_, i) => (
                                        <Cell key={i} fill={EMOTION_COLORS[i % EMOTION_COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Questions asked */}
                    <div style={cardStyle}>
                        <div style={sectionLabel}>Questions Asked</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', color: 'var(--accent)', fontFamily: 'var(--font-heading)', fontWeight: 600 }}>
                            {r.questions_asked.map((q, i) => (
                                <div key={i} style={{
                                    background: 'var(--bg)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    padding: '12px',
                                    fontSize: '13px',
                                    display: 'flex',
                                    gap: '10px',
                                    alignItems: 'flex-start',
                                }}>
                                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>Q{i + 1}</span>
                                    {q}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Transcript */}
                    <div style={cardStyle}>
                        <div style={sectionLabel}>Transcript Highlights</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {r.transcript_preview.map((chunk, i) => (
                                <div key={i} style={{
                                    background: 'var(--bg)',
                                    border: '1px solid var(--border)',
                                    borderRadius: 'var(--radius-sm)',
                                    borderLeft: '2px solid var(--accent)',
                                    padding: '12px',
                                    fontSize: '13px',
                                    lineHeight: 1.6,
                                    fontStyle: 'italic',
                                    color: 'var(--text-secondary)',
                                }}>
                                    "{chunk}"
                                </div>
                            ))}
                        </div>
                    </div>

                </div>
            </div>
        </div>
    )
}

const cardStyle: React.CSSProperties = {
    background: 'var(--bg-surface)',
    border: '2px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '24px',
}

const sectionLabel: React.CSSProperties = {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '16px',
    fontFamily: 'var(--font-heading)',
    fontWeight: 500,
}