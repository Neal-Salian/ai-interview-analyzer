import { useState } from 'react';
import type { MetricResult } from '../../types';

interface Props {
    metrics: MetricResult[];
}

function getMetricColor(score: number): string {
    if (score >= 80) return 'var(--success)';
    if (score >= 60) return '#3b82f6';
    if (score >= 40) return 'var(--warning)';
    return 'var(--danger)';
}

function MetricCard({ metric }: { metric: MetricResult }) {
    const [expanded, setExpanded] = useState(false);
    const barColor = getMetricColor(metric.score);

    return (
        <div style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            padding: '14px',
        }}>
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

            <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--border)', borderRadius: '3px', marginBottom: '8px', overflow: 'hidden' }}>
                <div style={{
                    width: `${metric.score}%`,
                    height: '100%',
                    backgroundColor: barColor,
                    borderRadius: '3px',
                    transition: 'width 0.5s ease, var(--theme-transition)',
                }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                <span>{metric.score}/100</span>
                <span>{Math.round(metric.confidence * 100)}% confidence</span>
            </div>

            {metric.explanation && (
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '6px 0 0 0', lineHeight: 1.5 }}>
                    {metric.explanation}
                </p>
            )}

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
    );
}

export default function AIInsightsCard({ metrics }: Props) {
    if (!metrics || metrics.length === 0) return null;

    return (
        <div style={{
            background: 'var(--bg-surface)',
            borderRadius: '12px',
            border: '1px solid var(--border)',
            padding: '1.5rem',
            boxShadow: 'var(--shadow-card)',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
        }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, margin: 0, paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
                💡 AI Analysis Insights
            </h3>
            
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                Metrics computed from emotion, transcript, attention, and behavioral signals.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px', marginTop: '0.5rem' }}>
                {metrics.map(m => (
                    <MetricCard key={m.name} metric={m} />
                ))}
            </div>
        </div>
    );
}
