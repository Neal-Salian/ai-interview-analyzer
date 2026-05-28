import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
//import { EmotionBadge } from '../components/EmotionBadge';

export default function ReportPage() {
    const { id: sessionId } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);

    // Mock data based on the screenshot
    const candidateName = "Priya Sharma";
    const role = "Senior Frontend Engineer";
    const duration = "45 mins";
    const date = "Oct 24, 2023";

    // Emotion breakdown data
    const emotions = [
        { name: "Focus", percentage: 65, color: "var(--info)" },
        { name: "Neutral", percentage: 20, color: "var(--text-secondary)" },
        { name: "Joy / Engagement", percentage: 10, color: "var(--success)" },
        { name: "Anxiety / Hesitation", percentage: 5, color: "var(--warning)" },
    ];

    // Mock timeline blocks (representing emotional shifts over 45 mins)
    const timelineBlocks = [
        { type: "info", width: "30%" },
        { type: "warning", width: "5%" },
        { type: "info", width: "45%" },
        { type: "success", width: "10%" },
        { type: "text-secondary", width: "10%" },
    ];

    useEffect(() => {
        // Simulate API fetch
        const timer = setTimeout(() => setLoading(false), 500);
        return () => clearTimeout(timer);
    }, []);

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: 'var(--bg)', color: 'var(--text-secondary)' }}>
                Loading report...
            </div>
        );
    }

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            minHeight: '100vh',
            backgroundColor: 'var(--bg)',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font)'
        }}>

            {/* Page Header */}
            <header style={{ padding: '2rem', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <button onClick={() => navigate('/sessions')} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: 0 }}>
                            <span className="material-symbols-outlined">arrow_back</span>
                        </button>
                        <h1 style={{ fontSize: '24px', fontWeight: 600, margin: 0 }}>{candidateName} - Session Report</h1>
                    </div>
                    <button
                        disabled
                        title="PDF generation coming soon"
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            background: 'var(--bg-surface)',
                            color: 'var(--danger)', /* Swapped --red to --danger to match your index.css */
                            border: '1px solid var(--danger)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '8px 16px',
                            fontSize: '13px',
                            fontWeight: 500,
                            cursor: 'not-allowed',
                            opacity: 0.8
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: '16px' }}></span>
                        ↓ Download PDF (coming soon)
                    </button>
                </div>

                <div style={{ display: 'flex', gap: '2rem', color: 'var(--text-secondary)', fontSize: '13px', marginLeft: '2.5rem' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><span className="material-symbols-outlined" style={{ fontSize: '16px' }}>calendar_today</span> {date}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><span className="material-symbols-outlined" style={{ fontSize: '16px' }}>schedule</span> {duration}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><span className="material-symbols-outlined" style={{ fontSize: '16px' }}>work</span> {role}</span>
                </div>
            </header>

            {/* Main Content Grid */}
            <main style={{
                display: 'grid',
                gridTemplateColumns: '2fr 1fr',
                gap: '1.5rem',
                padding: '2rem',
                flex: 1
            }}>

                {/* LEFT COLUMN */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

                    {/* Executive Summary */}
                    <div style={cardStyle}>
                        <h2 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 1rem 0', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                            <span className="material-symbols-outlined" style={{ color: 'var(--accent)' }}>auto_awesome</span> AI Executive Summary
                        </h2>
                        <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                            demonstrated exceptional technical proficiency, particularly in React architecture and state management optimization. The candidate maintained a consistently high level of focus during technical problem-solving exercises. Communication was clear, though slightly rushed during the system design phase, indicating mild performance anxiety which quickly subsided as they began structuring the solution. Overall cultural fit appears strong, showing alignment with our agile methodologies.
                        </p>
                    </div>

                    {/* Transcript Highlights */}
                    <div style={cardStyle}>
                        <h2 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 1rem 0', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                            <span className="material-symbols-outlined">format_quote</span> Transcript Highlights
                        </h2>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                            <div style={{ borderLeft: '3px solid var(--accent)', paddingLeft: '1rem' }}>
                                <p style={{ fontStyle: 'italic', margin: '0 0 8px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>
                                    "I prefer to tackle state management by minimizing global state and keeping it as close to the component tree where it's needed, falling back to Context or Redux only when prop-drilling becomes unmanageable."
                                </p>
                                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.05em' }}>12:45 - TECHNICAL APPROACH</span>
                            </div>

                            <div style={{ borderLeft: '3px solid var(--accent)', paddingLeft: '1rem' }}>
                                <p style={{ fontStyle: 'italic', margin: '0 0 8px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>
                                    "When dealing with legacy code, my first step is always writing comprehensive tests for the existing behavior before attempting any refactoring."
                                </p>
                                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.05em' }}>28:10 - PROBLEM SOLVING</span>
                            </div>
                        </div>
                    </div>

                    {/* Questions Addressed */}
                    <div style={cardStyle}>
                        <h2 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 1rem 0', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                            <span className="material-symbols-outlined">help_center</span> Questions Addressed
                        </h2>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <div style={{ padding: '1rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '6px' }}>
                                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Q1</span>
                                <p style={{ margin: '8px 0 0 0', fontSize: '13px', lineHeight: '1.5' }}>Explain your approach to optimizing React application performance.</p>
                            </div>
                            <div style={{ padding: '1rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '6px' }}>
                                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Q2</span>
                                <p style={{ margin: '8px 0 0 0', fontSize: '13px', lineHeight: '1.5' }}>Design a scalable architecture for a real-time collaborative editing tool.</p>
                            </div>
                            <div style={{ padding: '1rem', backgroundColor: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '6px' }}>
                                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>Q3</span>
                                <p style={{ margin: '8px 0 0 0', fontSize: '13px', lineHeight: '1.5' }}>Describe a time you had to resolve a significant conflict within an engineering team.</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* RIGHT COLUMN */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

                    {/* Confidence Scorecard */}
                    <div style={{ ...cardStyle, textAlign: 'center', padding: '2rem' }}>
                        <h2 style={{ fontSize: '16px', margin: '0 0 1.5rem 0' }}>Overall Confidence</h2>
                        {/* Task 3: Confidence Arc implemented natively with SVG */}
                        <div style={{ position: 'relative', width: '120px', height: '120px', margin: '0 auto' }}>
                            <svg width="120" height="120" viewBox="0 0 120 120">
                                {/* Background ring */}
                                <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" strokeWidth="10" />
                                {/* Foreground arc (74% filled) */}
                                <circle
                                    cx="60" cy="60" r="50"
                                    fill="none"
                                    stroke="var(--success)"
                                    strokeWidth="10"
                                    strokeDasharray="314"
                                    strokeDashoffset="81.64" /* 314 - (314 * 0.74) */
                                    strokeLinecap="round"
                                    transform="rotate(-90 60 60)"
                                />
                            </svg>
                            <div style={{ position: 'absolute', top: '0', left: '0', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px', fontWeight: 700 }}>
                                74%
                            </div>
                        </div>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '1.5rem', lineHeight: '1.5' }}>
                            Calculated based on vocal tonality, pacing, and visual stability.
                        </p>
                    </div>

                    {/* Emotion Breakdown */}
                    <div style={cardStyle}>
                        <h2 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 1rem 0', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                            <span className="material-symbols-outlined">bar_chart</span> Emotion Breakdown
                        </h2>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {emotions.map((em, idx) => (
                                <div key={idx}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                                        <span style={{ fontWeight: 600 }}>{em.name}</span>
                                        <span style={{ color: em.color, fontWeight: 600 }}>{em.percentage}%</span>
                                    </div>
                                    <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                                        <div style={{ width: `${em.percentage}%`, height: '100%', backgroundColor: em.color }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Task 2: Horizontal Session Timeline */}
                    <div style={cardStyle}>
                        <h2 style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 1rem 0', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                            <span className="material-symbols-outlined">timeline</span> Session Timeline
                        </h2>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                            Chronological emotional states throughout the interview.
                        </p>

                        <div style={{ display: 'flex', width: '100%', height: '16px', borderRadius: '4px', overflow: 'hidden', marginBottom: '8px' }}>
                            {timelineBlocks.map((block, idx) => (
                                <div key={idx} style={{
                                    width: block.width,
                                    height: '100%',
                                    backgroundColor: `var(--${block.type})`,
                                    borderRight: idx !== timelineBlocks.length - 1 ? '1px solid var(--bg-surface)' : 'none'
                                }} />
                            ))}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>
                            <span>0:00</span>
                            <span>45:00</span>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
}

const cardStyle: React.CSSProperties = {
    backgroundColor: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: '8px',
    padding: '1.5rem',
}