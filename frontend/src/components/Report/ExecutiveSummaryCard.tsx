import type { ReportExecutiveSummary, ReportEvaluation } from '../../types/report';

interface Props {
    summary: ReportExecutiveSummary;
    evaluation: ReportEvaluation | null;
}

export default function ExecutiveSummaryCard({ summary, evaluation }: Props) {
    const recommendation = evaluation?.overall_assessment || 'Pending Review';

    // Extract just the recommendation label if it's structured like "Recommended. The candidate showed..."
    const recLabel = recommendation.split('.')[0] || recommendation;

    let recColor = 'var(--text-secondary)';
    if (recLabel.toLowerCase().includes('strongly recommend')) recColor = '#10b981'; // green-500
    else if (recLabel.toLowerCase().includes('recommend')) recColor = '#34d399'; // green-400
    else if (recLabel.toLowerCase().includes('consider')) recColor = '#fbbf24'; // amber-400
    else if (recLabel.toLowerCase().includes('not')) recColor = '#f87171'; // red-400

    return (
        <div style={{
            background: 'var(--bg-surface)',
            borderRadius: '12px',
            border: '1px solid var(--border)',
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
            boxShadow: 'var(--shadow-card)'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h2 style={{ fontSize: '24px', fontWeight: 700, margin: '0 0 0.5rem 0', color: 'var(--text-primary)' }}>
                        {summary.candidate}
                    </h2>
                    <div style={{ display: 'flex', gap: '1.5rem', color: 'var(--text-secondary)', fontSize: '14px', alignItems: 'center', flexWrap: 'wrap' }}>
                        {summary.job && <span>📋 {summary.job}</span>}
                        {summary.duration_minutes !== null && <span>⏱ {summary.duration_minutes} mins</span>}
                        <span style={{ 
                            background: summary.status === 'completed' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(251, 191, 36, 0.15)',
                            color: summary.status === 'completed' ? 'var(--success)' : 'var(--warning)',
                            padding: '4px 10px',
                            borderRadius: '20px',
                            fontWeight: 600,
                            textTransform: 'capitalize',
                            fontSize: '12px'
                        }}>
                            {summary.status}
                        </span>
                    </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontWeight: 600 }}>
                        System Recommendation
                    </div>
                    <div style={{ 
                        fontSize: '20px', 
                        fontWeight: 800, 
                        color: recColor,
                        background: `${recColor}15`,
                        padding: '8px 16px',
                        borderRadius: '8px',
                        display: 'inline-block'
                    }}>
                        {recLabel}
                    </div>
                </div>
            </div>
        </div>
    );
}
