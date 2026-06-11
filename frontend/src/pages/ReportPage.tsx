import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import Navbar from '../components/Navbar';
import client from '../api/client';
import type { MetricResult } from '../types';

interface Analysis {
    session_id: string
    candidate: string | null
    job: string | null
    status: string
    started_at: string | null
    ended_at: string | null
    duration_minutes: number | null
    emotion_breakdown: Record<string, number>
    avg_confidence: number
    emotion_timeline: { dominant_emotion: string; confidence: number; timestamp: string }[]
    transcript_chunks: number
    full_transcript: string
    big_five: Record<string, number>
    overall_sentiment: { label: string; score: number }
    questions_generated: number
    questions_asked: number
    questions: {
        id: string
        question_text: string
        triggered_by: string
        was_asked: boolean
        created_at: string | null
    }[]
    metrics: MetricResult[]
}

const EMOTION_COLOR: Record<string, string> = {
    happy: '#34d399',
    neutral: '#60a5fa',
    sad: '#818cf8',
    angry: '#f87171',
    fear: '#fbbf24',
    surprise: '#f472b6',
    disgust: '#a78bfa',
}

const BIG_FIVE_LABELS: Record<string, string> = {
    openness: 'Openness',
    conscientiousness: 'Conscientiousness',
    extraversion: 'Extraversion',
    agreeableness: 'Agreeableness',
    neuroticism: 'Neuroticism',
}

export default function ReportPage() {
    const { id: sessionId } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [analysis, setAnalysis] = useState<Analysis | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!sessionId) return
        client.get(`/analysis/${sessionId}`)
            .then(res => setAnalysis(res.data))
            .catch(err => {
                console.error('Failed to load analysis', err)
                setError('Could not load analysis data.')
            })
            .finally(() => setLoading(false))
    }, [sessionId])

    if (loading) {
        return (
            <div>
                <Navbar />
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', color: 'var(--text-secondary)' }}>
                    Loading report...
                </div>
            </div>
        );
    }

    if (error || !analysis) {
        return (
            <div>
                <Navbar />
                <div style={{ padding: '40px', color: 'var(--danger)' }}>
                    {error || 'No analysis data found for this session.'}
                </div>
            </div>
        );
    }

    const emotionEntries = Object.entries(analysis.emotion_breakdown).sort((a, b) => b[1] - a[1])
    const dominantEmotion = emotionEntries[0]?.[0] ?? 'neutral'
    const confidencePercent = Math.round(analysis.avg_confidence)

    const chartData = analysis.emotion_timeline.map((e, i) => ({
        t: i,
        confidence: e.confidence,
        emotion: e.dominant_emotion,
    }))

    const bigFiveEntries = Object.entries(analysis.big_five)
    const sentimentPositive = analysis.overall_sentiment?.label === 'POSITIVE'

    const circumference = 314
    const dashOffset = circumference - (circumference * (confidencePercent / 100))

    return (
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />

            {/* Page Header */}
            <header style={{ padding: '2rem', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <button onClick={() => navigate('/sessions')} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px' }}>
                            ←
                        </button>
                        <h1 style={{ fontSize: '22px', fontWeight: 600, margin: 0 }}>
                            {analysis.candidate ?? 'Unknown Candidate'} — Session Report
                        </h1>
                    </div>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '4px', padding: '4px 10px' }}>
                        PDF coming soon
                    </span>
                </div>

                <div style={{ display: 'flex', gap: '2rem', color: 'var(--text-secondary)', fontSize: '13px', marginLeft: '2.5rem', flexWrap: 'wrap' }}>
                    {analysis.job && <span>📋 {analysis.job}</span>}
                    {analysis.duration_minutes && <span>⏱ {analysis.duration_minutes} mins</span>}
                    {analysis.started_at && (
                        <span>📅 {new Date(analysis.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                    )}
                    <span style={{ color: analysis.status === 'completed' ? 'var(--success)' : 'var(--warning)' }}>
                        ● {analysis.status}
                    </span>
                </div>
            </header>

            {/* Main Grid */}
            <main style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', padding: '2rem', flex: 1 }}>

                {/* LEFT COLUMN */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

                    {/* Sentiment Summary */}
                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>
                            🤖 Overall Sentiment
                        </h2>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                            <div style={{
                                fontSize: '28px', fontWeight: 700,
                                color: sentimentPositive ? 'var(--success)' : 'var(--danger)',
                                textTransform: 'capitalize'
                            }}>
                                {analysis.overall_sentiment?.label ?? '—'}
                            </div>
                            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', background: 'var(--bg)', padding: '4px 12px', borderRadius: '20px' }}>
                                {analysis.overall_sentiment?.score
                                    ? `${Math.round(analysis.overall_sentiment.score * 100)}% confidence`
                                    : 'No transcript data'}
                            </div>
                        </div>
                        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '10px' }}>
                            Based on {analysis.transcript_chunks} transcript chunks · {analysis.questions_asked}/{analysis.questions_generated} suggested questions were asked
                        </p>
                    </div>

                    {/* Emotion Timeline Chart */}
                    {chartData.length > 0 && (
                        <div style={cardStyle}>
                            <h2 style={cardTitleStyle}>📈 Emotion Confidence Over Time</h2>
                            <ResponsiveContainer width="100%" height={200}>
                                <LineChart data={chartData}>
                                    <XAxis dataKey="t" hide />
                                    <YAxis domain={[0, 100]} hide />
                                    <Tooltip
                                        contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', fontSize: '12px' }}
                                        formatter={(val, _name, props) => [`${val}%`, props.payload.emotion]}
                                    />
                                    <Line type="monotone" dataKey="confidence" stroke="var(--accent)" strokeWidth={2} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )}

                    {/* Big Five */}
                    {bigFiveEntries.length > 0 && (
                        <div style={cardStyle}>
                            <h2 style={cardTitleStyle}>🧠 Big Five Personality Signals</h2>
                            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                                Directional estimates based on linguistic cues in the transcript.
                            </p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                {bigFiveEntries.map(([trait, score]) => (
                                    <div key={trait}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '5px' }}>
                                            <span style={{ fontWeight: 600 }}>{BIG_FIVE_LABELS[trait] ?? trait}</span>
                                            <span style={{ color: 'var(--accent)' }}>{score.toFixed(1)} / 10</span>
                                        </div>
                                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                                            <div style={{ width: `${(score / 10) * 100}%`, height: '100%', backgroundColor: 'var(--accent)' }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Questions asked */}
                    {analysis.questions.length > 0 && (
                        <div style={cardStyle}>
                            <h2 style={cardTitleStyle}>❓ Suggested Questions</h2>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                {analysis.questions.map(q => (
                                    <div key={q.id} style={{
                                        background: 'var(--bg)',
                                        border: `1px solid ${q.was_asked ? 'var(--success)' : 'var(--border)'}`,
                                        borderRadius: '6px',
                                        padding: '12px',
                                        opacity: q.was_asked ? 1 : 0.6,
                                    }}>
                                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            {q.triggered_by} · {q.was_asked ? '✓ Asked' : 'Not asked'}
                                        </div>
                                        <div style={{ fontSize: '13px', lineHeight: 1.5 }}>{q.question_text}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Behavioral Metrics — rendered dynamically (Phase 10) */}
                    {analysis.metrics?.length > 0 && (
                        <div style={cardStyle}>
                            <h2 style={cardTitleStyle}>📊 Behavioral Insights</h2>
                            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                                Metrics computed from emotion, transcript, attention, and behavioral signals.
                            </p>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                                {analysis.metrics.map(m => (
                                    <MetricCard key={m.name} metric={m} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Full transcript */}
                    {analysis.full_transcript && (
                        <div style={cardStyle}>
                            <h2 style={cardTitleStyle}>📝 Full Transcript</h2>
                            <div style={{
                                maxHeight: '300px', overflowY: 'auto',
                                fontSize: '13px', lineHeight: 1.7,
                                color: 'var(--text-secondary)',
                                background: 'var(--bg)', padding: '16px',
                                borderRadius: '6px', border: '1px solid var(--border)'
                            }}>
                                {analysis.full_transcript}
                            </div>
                        </div>
                    )}
                </div>

                {/* RIGHT COLUMN */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

                    {/* Confidence ring */}
                    <div style={{ ...cardStyle, textAlign: 'center', padding: '2rem' }}>
                        <h2 style={{ fontSize: '15px', margin: '0 0 1.5rem 0' }}>Avg. Emotion Confidence</h2>
                        <div style={{ position: 'relative', width: '120px', height: '120px', margin: '0 auto' }}>
                            <svg width="120" height="120" viewBox="0 0 120 120">
                                <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" strokeWidth="10" />
                                <circle
                                    cx="60" cy="60" r="50"
                                    fill="none"
                                    stroke={EMOTION_COLOR[dominantEmotion] ?? 'var(--accent)'}
                                    strokeWidth="10"
                                    strokeDasharray={circumference}
                                    strokeDashoffset={dashOffset}
                                    strokeLinecap="round"
                                    transform="rotate(-90 60 60)"
                                />
                            </svg>
                            <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '22px', fontWeight: 700 }}>
                                {confidencePercent}%
                            </div>
                        </div>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '1rem' }}>
                            Dominant: <strong style={{ color: EMOTION_COLOR[dominantEmotion] ?? 'var(--text-primary)', textTransform: 'capitalize' }}>{dominantEmotion}</strong>
                        </p>
                    </div>

                    {/* Emotion breakdown */}
                    {emotionEntries.length > 0 && (
                        <div style={cardStyle}>
                            <h2 style={cardTitleStyle}>😐 Emotion Breakdown</h2>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                {emotionEntries.map(([emotion, pct]) => (
                                    <div key={emotion}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '5px' }}>
                                            <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{emotion}</span>
                                            <span style={{ color: EMOTION_COLOR[emotion] ?? 'var(--text-secondary)', fontWeight: 600 }}>{pct}%</span>
                                        </div>
                                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                                            <div style={{ width: `${pct}%`, height: '100%', backgroundColor: EMOTION_COLOR[emotion] ?? 'var(--accent)' }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Stats */}
                    <div style={cardStyle}>
                        <h2 style={cardTitleStyle}>📊 Session Stats</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {[
                                ['Frames analyzed', analysis.total_frames_analyzed],
                                ['Transcript chunks', analysis.transcript_chunks],
                                ['Questions generated', analysis.questions_generated],
                                ['Questions asked', analysis.questions_asked],
                                ['Duration', analysis.duration_minutes ? `${analysis.duration_minutes} min` : '—'],
                            ].map(([label, val]) => (
                                <div key={label as string} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
                                    <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                                    <span style={{ fontWeight: 600 }}>{val}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
}

// ── Dynamic metric card — renders any MetricResult without hardcoding ────────

function getMetricColor(score: number): string {
    if (score >= 80) return 'var(--success)'
    if (score >= 60) return '#3b82f6'
    if (score >= 40) return 'var(--warning)'
    return 'var(--danger)'
}

function MetricCard({ metric }: { metric: MetricResult }) {
    const [expanded, setExpanded] = useState(false)
    const barColor = getMetricColor(metric.score)

    return (
        <div style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            padding: '14px',
        }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '13px', fontWeight: 600 }}>{metric.name}</span>
                <span style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    color: barColor,
                    background: `${barColor}15`,
                    padding: '2px 8px',
                    borderRadius: '4px',
                }}>{metric.level}</span>
            </div>

            {/* Score bar */}
            <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border)', borderRadius: '3px', marginBottom: '8px', overflow: 'hidden' }}>
                <div style={{
                    width: `${metric.score}%`,
                    height: '100%',
                    backgroundColor: barColor,
                    borderRadius: '3px',
                    transition: 'width 0.5s ease',
                }} />
            </div>

            {/* Score + confidence */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                <span>{metric.score}/100</span>
                <span>{Math.round(metric.confidence * 100)}% confidence</span>
            </div>

            {/* Explanation */}
            {metric.explanation && (
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '6px 0 0 0', lineHeight: 1.5 }}>
                    {metric.explanation}
                </p>
            )}

            {/* Expandable evidence */}
            {metric.evidence.length > 0 && (
                <>
                    <button
                        onClick={() => setExpanded(prev => !prev)}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--accent)',
                            fontSize: '11px',
                            cursor: 'pointer',
                            padding: '4px 0 0 0',
                            fontWeight: 500,
                        }}
                    >
                        {expanded ? '▾ Hide evidence' : '▸ Show evidence'} ({metric.evidence.length})
                    </button>
                    {expanded && (
                        <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            {metric.evidence.map((e, i) => (
                                <div key={i} style={{
                                    fontSize: '11px',
                                    color: 'var(--text-secondary)',
                                    background: 'var(--bg-surface)',
                                    padding: '6px 8px',
                                    borderRadius: '4px',
                                    borderLeft: '2px solid var(--accent)',
                                    lineHeight: 1.4,
                                }}>
                                    {e.quote}
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

const cardStyle: React.CSSProperties = {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    boxShadow: 'var(--shadow-card)',
    borderRadius: '8px',
    padding: '1.5rem',
}

const cardTitleStyle: React.CSSProperties = {
    fontSize: '15px',
    fontWeight: 600,
    margin: '0 0 1rem 0',
    paddingBottom: '0.75rem',
    borderBottom: '1px solid var(--border)',
}